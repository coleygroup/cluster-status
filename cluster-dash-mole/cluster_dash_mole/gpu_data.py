import contextlib
import collections
import functools

import psutil
import pynvml

from . import logging_utils
from . import utils


def try_nvml_func(func):
    try:
        func()
    except pynvml.NVMLError as ex:
        logging_utils.get_log().debug("Ignoring NVML error of {}".format(ex))
        pass


def init_nvml_if_required(fn):
    """
     decorator that wraps classmethods/regular methods and
     will ensure NVML is initialized if required (i.e., class's init flag is not set)
     and deinitialized after calling the function.
    """

    @functools.wraps(fn)
    def wrapped_func(cls, *args, **kwargs):
        # if the class does not have NVML down as being initialized then will inialize it here. we will also set a flag
        # so that we know when to deinitialize it after.
        if not cls.nvml_inited:
            initing_nvml = True
            pynvml.nvmlInit()
            cls.nvml_inited = True
        else:
            initing_nvml = False

        # can now call the function!
        result = fn(cls, *args, **kwargs)

        # if we initialized it earlier then we will shut it down now and mark it as so.
        if initing_nvml:
            pynvml.nvmlShutdown()
            cls.nvml_inited = False

        return result
    return wrapped_func


class GPUData:

    nvml_inited = False

    @classmethod
    @init_nvml_if_required
    def get_devices(cls):
        deviceCount = pynvml.nvmlDeviceGetCount()
        devs = [pynvml.nvmlDeviceGetHandleByIndex(i) for i in range(deviceCount)]
        return devs

    @classmethod
    @init_nvml_if_required
    def get_device_memory(cls, handle):
        info = pynvml.nvmlDeviceGetMemoryInfo(handle)
        total_mem_in_mb = utils.convert_bytes_to_mega_bytes(float(info.total))
        used_mem_in_mb = utils.convert_bytes_to_mega_bytes(float(info.used))
        return total_mem_in_mb, used_mem_in_mb

    @classmethod
    @init_nvml_if_required
    def get_device_utilization(cls, handle):
        util_rates = pynvml.nvmlDeviceGetUtilizationRates(handle)

        gpu_util = util_rates.gpu
        # ^ Percent of time over the past sample period during which one or more kernels was executing on the GPU.

        memory_util = util_rates.memory
        # ^ Percent of time over the past sample period during which global (device) memory was being read or written.
        return gpu_util, memory_util

    @classmethod
    @init_nvml_if_required
    def get_device_identifiers(cls, handle):
        name = pynvml.nvmlDeviceGetName(handle)
        uuid = pynvml.nvmlDeviceGetUUID(handle)
        index = pynvml.nvmlDeviceGetIndex(handle)
        return name, uuid, index

    @classmethod
    @init_nvml_if_required
    def get_all_data_as_dict(cls):

        results = {}

        try:
            for i, handle in enumerate(cls.get_devices()):
                name, uuid, index = cls.get_device_identifiers(handle)
                # in older versions of nvidia-ml-py name and uuids are byte type objects
                try:
                    name = name.decode()
                    uuid = uuid.decode()
                except (UnicodeDecodeError, AttributeError):
                    pass
                name_to_use = f"{index}_{utils.replace_spaces_with_char(name, '-')}_{uuid[4:10]}"

                total_mem, used_mem = cls.get_device_memory(handle)
                gpu_util, memory_util = cls.get_device_utilization(handle)
                user_data = cls._get_user_results(handle)

                results[name_to_use] = {
                    "name": name,
                    "uuid": uuid,
                    "index": index,
                    "total_mem": total_mem,
                    "used_mem": used_mem,
                    "users": user_data,
                    "gpu_util": gpu_util,
                    "memory_util": memory_util,
                }
        except pynvml.NVMLError_LibraryNotFound:
            results["gpu_data"] = {
                    "name": "none",
                    "uuid": "none",
                    "index": 0,
                    "total_mem": 0,
                    "used_mem": 0,
                    "users": {},
                    "gpu_util": 0,
                    "memory_util": 0,
                }
        return results

    @classmethod
    @init_nvml_if_required
    def _get_user_results(cls, handle):
        # note this likely will not currently work if someone is running inside Docker -- have not tested!
        user_data = collections.defaultdict(dict)
        process_data = pynvml.nvmlDeviceGetComputeRunningProcesses(handle)

        for p in process_data:
            pid = p.pid

            try:
                name = pynvml.nvmlSystemGetProcessName(pid)
                mem = utils.convert_bytes_to_mega_bytes(float(p.usedGpuMemory))
            except Exception:
                name = ""
                mem = None

            try:
                process = psutil.Process(pid=pid)
                user = process.username()
                time = process.cpu_times().system
            except psutil.Error as ex:
                user = "unknown"
                time = None

            # older versions of pynvml will have name as a byte sting so decode
            try:
                name = name.decode()
            except (UnicodeDecodeError, AttributeError):
                pass

            user_data[user][pid] = dict(mem=mem, time=time, name=name)

        return user_data
