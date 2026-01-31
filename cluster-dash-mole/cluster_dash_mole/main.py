
import time


from . import settings_loader
from . import logging_utils
from . import gpu_data
from . import comms
from . import general_machine_data
from . import cpu_data


class MainRunner(object):

    def __init__(self):
        self.cpu_data = cpu_data.CPUData()
        self.gpu_data = gpu_data.GPUData()
        self.machine_data = general_machine_data.MachineData()

        comm_senders = []
        if settings_loader.get_config_parser()["StdOut_Logger"]["use"]:
            comm_senders.append(comms.StdOutSender())

        if settings_loader.get_config_parser()["Json_Sender_Logger"]["use"]:
            comm_senders.append(comms.JsonSender())

        if settings_loader.get_config_parser()["Google_Sheets_Logger"]["use"]:
            comm_senders.append(comms.GoogleSheetSender())

        self.comm_senders = comm_senders

    def main(self):
        log = logging_utils.get_log()
        settings = settings_loader.get_config_parser()
        log.info("Starting up!")
        while True:
            data = self.get_data()
            log.debug("Sending data: {}".format(str(data)))
            for c_ in self.comm_senders:
                c_.work(data)
            time.sleep(settings["Poll_Settings"]["poll_interval_in_secs"])

    def get_data(self):

        # Machine data
        results = self.machine_data.get_all_data_as_dict()

        # add CPU data
        results["cpu"] = self.cpu_data.get_all_data_as_dict()

        # add GPU data
        results["gpu"] = self.gpu_data.get_all_data_as_dict()

        return results


