import datetime
import socket
from threading import Thread, Event

class StoppableThread(Thread):
    '''Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition.'''

    def __init__(self, *args, **kwargs):
        super(StoppableThread, self).__init__(*args, **kwargs)
        self._stop_event = Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()


def newsock():
    return socket.socket(socket.AF_INET, socket.SOCK_STREAM)


def is_port_in_use(port):
    with newsock() as s:
        return s.connect_ex(("localhost", port)) == 0


def deserialize_timestamp(t):
    datetime.datetime.strptime(t, "%Y-%m-%d %H:%M:%S.%f")


def parse(arg):
    'Convert a series of zero or more numbers to an argument tuple'
    return tuple(map(int, arg.split()))
