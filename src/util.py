import socket


def newsock():
    return socket.socket(socket.AF_INET, socket.SOCK_STREAM)


def is_port_in_use(port):
    with newsock() as s:
        return s.connect_ex(("localhost", port)) == 0
