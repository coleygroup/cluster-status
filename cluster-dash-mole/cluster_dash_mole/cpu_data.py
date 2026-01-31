
import psutil


class CPUData:
    @staticmethod
    def get_cpu_percentage():
            return psutil.cpu_percent(interval=0.1, percpu=False)  # nb blocks for 0.1 secs

    @staticmethod
    def get_num_cpus():
            return psutil.cpu_count()

    @staticmethod
    def get_load_avg():
        return psutil.getloadavg()

    @classmethod
    def get_all_data_as_dict(cls):
        load_avgs = cls.get_load_avg()
        return {
            "cpu_percent": cls.get_cpu_percentage(),
            "num_cpus": cls.get_num_cpus(),
            "load_avgs": load_avgs
        }
