import json
from enum import IntEnum


class Kind(IntEnum):
    # tracker assigns an identifier to the node,
    # and will now await the port number that the
    # node wishes to listen for peers on
    TRACKER_IDENT = 0

    # node will tell the tracker what port they will listen
    # on for peer connections
    NODE_PORT = 1

    # tracker has officially registered the client and will
    # now inform the node of its peers
    TRACKER_PEERS = 2

    # node will tell its peer what identifier it is
    PEER_IDENT = 3

    # peer has accepted node
    PEER_ACCEPT = 4

    # tracker informs the node that it may begin listening
    TRACKER_ACCEPT = 5

    # tracker is informing existing nodes of a new peer
    TRACKER_NEW_PEER = 6

    # node has received its peers from the tracker
    NODE_PEERS = 7

    # node is disconnecting
    NODE_DISCONNECT = 8


# a JSON-serializable message
class Message:
    def __init__(self, kind):
        self.kind = kind
        self.msg = {"kind": kind}

    def to_string(self):
        return json.dumps(self.msg)

    def send(self, sock):
        data = bytearray(self.to_string().encode())
        data.extend(b'\xFF')
        sock.send(data)


class TrackerIdent(Message):
    def __init__(self, ident):
        super().__init__(Kind.TRACKER_IDENT)
        self.msg["ident"] = ident


class NodePort(Message):
    def __init__(self, port):
        super().__init__(Kind.NODE_PORT)
        self.msg["port"] = port


class TrackerPeers(Message):
    def __init__(self, peers):
        super().__init__(Kind.TRACKER_PEERS)
        self.msg["peers"] = peers


class PeerIdent(Message):
    def __init__(self, ident):
        super().__init__(Kind.PEER_IDENT)
        self.msg["ident"] = ident


class PeerAccept(Message):
    def __init__(self):
        super().__init__(Kind.PEER_ACCEPT)


class TrackerAccept(Message):
    def __init__(self):
        super().__init__(Kind.TRACKER_ACCEPT)


class TrackerNewPeer(Message):
    def __init__(self, peer):
        super().__init__(Kind.TRACKER_NEW_PEER)
        self.msg["peer"] = peer


class NodePeers(Message):
    def __init__(self):
        super().__init__(Kind.NODE_PEERS)


class NodeDisconnect(Message):
    def __init__(self):
        super().__init__(Kind.NODE_DISCONNECT)


def of_string(s):
    try:
        j = json.loads(s)
        k = j["kind"]
        if k == Kind.TRACKER_IDENT:
            return TrackerIdent(j["ident"])
        elif k == Kind.NODE_PORT:
            return NodePort(j["port"])
        elif k == Kind.TRACKER_PEERS:
            return TrackerPeers(j["peers"])
        elif k == Kind.PEER_IDENT:
            return PeerIdent(j["ident"])
        elif k == Kind.PEER_ACCEPT:
            return PeerAccept()
        elif k == Kind.TRACKER_ACCEPT:
            return TrackerAccept()
        elif k == Kind.TRACKER_NEW_PEER:
            return TrackerNewPeer(j["peer"])
        elif k == Kind.NODE_PEERS:
            return NodePeers()
        elif k == Kind.NODE_DISCONNECT:
            return NodeDisconnect()
        else:
            return None
    except:
        return None


def recv(sock):
    data = bytearray()

    while True:
        packet = sock.recv(4096)
        n = len(packet)
        if n == 0:
            break
        n1 = n - 1
        if packet[n1] == 255:
            data.extend(packet[:n1])
            break
        else:
            data.extend(packet)

    try:
        return of_string(data.decode())
    except UnicodeDecodeError:
        # this may happen if more than one message
        # was available on the socket, so perhaps
        # we may need to handle the case where
        # this function may return a list of messages
        None
