from datetime import datetime
import socket


def printts(*args, **kwargs):
    print(datetime.now(), *args, **kwargs)


def newsock():
    return socket.socket(socket.AF_INET, socket.SOCK_STREAM)


def is_port_in_use(port):
    with newsock() as s:
        return s.connect_ex(("localhost", port)) == 0


def deserialize_timestamp(t):
    datetime.strptime(t, "%Y-%m-%d %H:%M:%S.%f")


def parse(arg):
    'Convert a series of zero or more numbers to an argument tuple'
    return tuple(map(int, arg.split()))
