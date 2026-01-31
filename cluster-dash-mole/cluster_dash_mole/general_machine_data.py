
import socket
import time
import os

import psutil

from . import utils

class MachineData:
    @staticmethod
    def get_hostname():
        return socket.gethostname()

    @staticmethod
    def get_time():
        return time.time()

    @staticmethod
    def get_bootime():
        return psutil.boot_time()

    @staticmethod
    def get_memory_information():
        mem = psutil.virtual_memory()
        total = utils.convert_bytes_to_giga_bytes(mem.total)
        available = utils.convert_bytes_to_giga_bytes(mem.available)
        used = utils.convert_bytes_to_giga_bytes(mem.used)
        return total, available, used

    @staticmethod
    def get_disk_usage():
        out = {}
        for disk_partitions in psutil.disk_partitions(all=False):
            if os.name == 'nt':
                if 'cdrom' in disk_partitions.opts or disk_partitions.fstype == '':
                    # skip cd-rom drives with no disk in it; they may raise
                    # ENOENT, pop-up a Windows GUI error for a non-ready
                    # partition or just hang.
                    # from: https://github.com/giampaolo/psutil/blob/master/scripts/disk_usage.py
                    continue
            device = disk_partitions.device
            mount_point = disk_partitions.mountpoint

            usage = psutil.disk_usage(disk_partitions.mountpoint)
            total_gb = utils.convert_bytes_to_giga_bytes(usage.total)
            used_gb = utils.convert_bytes_to_giga_bytes(usage.used)
            percent_used = usage.percent

            out[mount_point] = {
                "device": device,
                "mount_point": mount_point,
                "total_gb": total_gb,
                "used_gb": used_gb,
                "percent_used": percent_used,
            }
        return out

    @classmethod
    def get_all_data_as_dict(cls):
        total, available, used = cls.get_memory_information()
        return {
            "general": {
                "hostname": cls.get_hostname(),
                "system_time": cls.get_time(),
                "boottime": cls.get_bootime(),
            },
            "memory": {
                "total_gb": total,
                "available_gb": available,
                "used_gb": used,
            },
            "disk": cls.get_disk_usage()
        }

