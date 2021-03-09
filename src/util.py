import socket


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def sendall(sock, s):
    # extend with an extra dummy character if
    # the length is exactly the buffer size
    if len(s) == 4096:
        s += ' '
    sock.sendall(s.encode())


def recvall(sock):
    data = bytearray()
    while True:
        packet = sock.recv(4096)
        if not packet:
            break
        data.extend(packet)
        if len(packet) < 4096:
            break
    return data.decode()
