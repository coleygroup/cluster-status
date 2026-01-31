
import json
import queue
from concurrent import futures
import datetime


import requests
import abc
import pprint
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient import errors

from . import settings_loader
from . import general_machine_data
from . import logging_utils
from . import thread_safe_utils

request_fails = thread_safe_utils.Counter()
sheets_fails = thread_safe_utils.Counter()
kill_msgs = queue.Queue()
_thread_pool = futures.ThreadPoolExecutor(5)


class Sender(metaclass=abc.ABCMeta):
    """
    When given a data dict creates a work job and submits this to a thread pool to get executed.
    Before doing work it will check if thread pool has reported any errors (i.e., as a result of previous jobs, and if
    so will fall over).
    """
    def __init__(self, min_interval_in_secs=1):
        self.min_interval_in_secs = min_interval_in_secs
        self.last_updated = None

    def work(self, dict_in):
        try:
            msg = kill_msgs.get(block=False)
            raise RuntimeError("Failure in at least one thread: " + str(msg))
        except queue.Empty:
            pass

        time_now = datetime.datetime.now()
        if self.last_updated is None or \
                ((time_now - self.last_updated).total_seconds() > self.min_interval_in_secs):
            job = self._create_job(dict_in)
            if job is not None:
                future = _thread_pool.submit(job)
                future.add_done_callback(raise_exception_from_future)
            self.last_updated = time_now

    @abc.abstractmethod
    def _create_job(self, dict_in):
        raise NotImplementedError


class GoogleSheetSender(Sender):
    """
    Adds data as a row to a sheet in Google sheets
    """
    def __init__(self):
        google_sheets_config = settings_loader.get_config_parser()["Google_Sheets_Logger"]
        super().__init__(google_sheets_config['min_interval_in_secs'])

        self.service_account_file_path = google_sheets_config['service_account_file_path']
        self.spreadsheets_id = google_sheets_config['spreadsheets_id']
        worksheetname = google_sheets_config['worksheet_name']
        if worksheetname == "!hostname":
            worksheetname = general_machine_data.MachineData.get_hostname()
            log = logging_utils.get_log()
            log.info(f"Setting worksheet name to match hostname ({worksheetname}).")
        self.worksheet_name = worksheetname


    def _create_job(self, dict_in):
        time_in_iso = datetime.datetime.fromtimestamp(dict_in["general"]["system_time"]).isoformat()

        gpu_data = []
        for gpu_name, gpu_values in sorted(dict_in["gpu"].items()):
            gpu_data.append(gpu_values["gpu_util"])
            gpu_data.append(gpu_values["memory_util"])

        row = [
            time_in_iso,
            dict_in["memory"]["used_gb"],
            dict_in["memory"]["total_gb"],
            dict_in["cpu"]["cpu_percent"],
            dict_in["cpu"]["load_avgs"][2],
            *gpu_data
        ]

        sheet_dump = create_sheet_dump(self.service_account_file_path, row, self.spreadsheets_id, self.worksheet_name)
        return sheet_dump


class JsonSender(Sender):
    """
    Sends the data as a JSON to a server.
    """
    def __init__(self):
        json_sender_config = settings_loader.get_config_parser()["Json_Sender_Logger"]
        super().__init__(json_sender_config['min_interval_in_secs'])

        self.send_address = json_sender_config["address_in"]
        self.auth_code = json_sender_config["auth_code"]

    def _add_supp(self, dict_in):
        dict_in["auth_code"] = self.auth_code
        dict_in["hostname"] = general_machine_data.MachineData.get_hostname()
        dict_in["timestamp"] = general_machine_data.MachineData.get_time()

    def _create_job(self, dict_in):
        self._add_supp(dict_in)
        json_to_send = json.dumps(dict_in)
        req = create_request(self.send_address, json_to_send)
        return req


class StdOutSender(Sender):
    """
    Pretty prints the output to std out.
    """
    def __init__(self):
        std_out_config = settings_loader.get_config_parser()["StdOut_Logger"]
        super().__init__(std_out_config["min_interval_in_secs"])

    def _create_job(self, dict_in):
        pprint.pprint(dict_in)
        return None


def raise_exception_from_future(future):
    ex = future.exception()
    if ex is not None:
        kill_msgs.put(ex.message)


def create_request(address, json_in):
    def req():
        log = logging_utils.get_log()
        global request_fails
        headers = {"Content-Type": "application/json"}
        try:
            r = requests.post(address, headers=headers, data=json_in, timeout=5)
            r.raise_for_status()
            request_fails.reset()

            jsonBack = r.json()

            log.info("The request was a success?: {}, {}".format(jsonBack["success"], jsonBack["msg"]))

        except (requests.Timeout, requests.HTTPError) as ex:
            log.info("Request failed.")
            if isinstance(ex, requests.Timeout):
                log.info("Request timed out {}".format(ex))
            elif isinstance(ex, requests.HTTPError):
                log.info("HTTP error for post {}".format(ex))

            request_fails.increment()
            if request_fails.value > 20:
                raise RuntimeError("Over 20 fails in a row. Quitting.")
        else:
            request_fails.reset()
            log.debug("*** sent to server!")
            return r
    return req


def create_sheet_dump(service_account_file, row_values, spreadsheet_id, sheet_range):
    def req():
        log = logging_utils.get_log()
        try:
            scopes = ('https://www.googleapis.com/auth/spreadsheets',)
            creds = service_account.Credentials.from_service_account_file(service_account_file,
                                                                          scopes=scopes)
            service = build('sheets', 'v4', credentials=creds)

            # Call the Sheets API
            body = {
                'values': [row_values,]
            }
            request = service.spreadsheets().values().append(spreadsheetId=spreadsheet_id, range=sheet_range,
                                                             valueInputOption="RAW",
                                                             insertDataOption="INSERT_ROWS", body=body
                                                             )
            response = request.execute()
        except errors.Error as ex:
            log.info("Google Sheets failed.")
            if isinstance(ex, errors.HttpError):
                log.info("due to HTTP error")
            log.info(ex)
            sheets_fails.increment()
            if sheets_fails.value > 20:
                raise RuntimeError("Over 20 fails in a row for sheets. Quitting.")
        else:
            sheets_fails.reset()
            log.debug("*** sent to google sheets!")
            return response
    return req
