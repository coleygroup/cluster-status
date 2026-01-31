
import threading


class Counter(object):
    def __init__(self, starting_value=0):
        self._value = starting_value
        self.thread_lock = threading.Lock()

    def increment(self, increment_amount=1):
        with self.thread_lock:
            self._value += increment_amount

    def reset(self):
        with self.thread_lock:
            self._value = 0

    @property
    def value(self):
        with self.thread_lock:
            val = self._value
        return val

