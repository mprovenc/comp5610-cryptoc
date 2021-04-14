import json
from enum import IntEnum, auto
from . import pkc


class Kind(IntEnum):
    # node sends its public key and verify key
    NODE_KEYS = auto()

    # tracker assigns an identifier to the node,
    # and will now await the port number that the
    # node wishes to listen for peers on.
    # tracker also sends its public key and verify key.
    TRACKER_IDENT = auto()

    # node received the identifier
    NODE_IDENT = auto()

    # node will tell the tracker what port they will listen
    # on for peer connections
    NODE_PORT = auto()

    # tracker has officially registered the client and will
    # now inform the node of its peers
    TRACKER_PEERS = auto()

    # node will tell its peer what identifier it is
    PEER_IDENT = auto()

    # node expects the peer to verify their identity
    PEER_VERIFY = auto()

    # peer has accepted node
    PEER_ACCEPT = auto()

    # tracker informs the node that it may begin listening
    TRACKER_ACCEPT = auto()

    # tracker is informing existing nodes of a new peer
    TRACKER_NEW_PEER = auto()

    # node has received its peers from the tracker
    NODE_PEERS = auto()

    # node is disconnecting
    NODE_DISCONNECT = auto()

    # tracker sends the existing blockchain to a node
    TRACKER_CHAIN = auto()

    # peer sends a transaction to another peer
    PEER_TRANSACTION = auto()

    # peer sends a block to another peer
    PEER_BLOCK = auto()


# a JSON-serializable message
class Message:
    def __init__(self, kind):
        self.kind = kind
        self.msg = {"kind": kind}

    def to_string(self):
        return json.dumps(self.msg)

    def send(self, sock, enc=None):
        data = bytearray(self.to_string().encode())

        if enc:
            data = bytes(data)
            # encrypt the message, also providing the receiver's public key
            data = enc[1].encrypt(data, enc[0])
            # sign the message with our signing key
            data = enc[1].sign(data)
            data = bytearray(data)

        # prepend the length of the message as a big-endian 32-bit number
        # generally speaking, the length is not confidential
        mlen = len(data).to_bytes(4, byteorder='big')
        data = mlen + data
        sock.send(data)


class NodeKeys(Message):
    def __init__(self, public_key, verify_key):
        super().__init__(Kind.NODE_KEYS)
        self.msg["public_key"] = public_key
        self.msg["verify_key"] = verify_key


class TrackerIdent(Message):
    def __init__(self, ident, public_key, verify_key):
        super().__init__(Kind.TRACKER_IDENT)
        self.msg["ident"] = ident
        self.msg["public_key"] = public_key
        self.msg["verify_key"] = verify_key


class NodeIdent(Message):
    def __init__(self):
        super().__init__(Kind.NODE_IDENT)


class TrackerChain(Message):
    def __init__(self, blockchain):
        super().__init__(Kind.TRACKER_CHAIN)
        self.msg["blockchain"] = blockchain


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


class PeerVerify(Message):
    def __init__(self):
        super().__init__(Kind.PEER_VERIFY)


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


class PeerTransaction(Message):
    def __init__(self, transaction):
        super().__init__(Kind.PEER_TRANSACTION)
        self.msg["transaction"] = transaction


class PeerBlock(Message):
    def __init__(self, block):
        super().__init__(Kind.PEER_BLOCK)
        self.msg["block"] = block


def node_keys(j):
    return NodeKeys(j["public_key"], j["verify_key"])


def tracker_ident(j):
    return TrackerIdent(j["ident"], j["public_key"], j["verify_key"])


def node_ident(j):
    return NodeIdent()


def node_port(j):
    return NodePort(j["port"])


def tracker_peers(j):
    return TrackerPeers(j["peers"])


def peer_ident(j):
    return PeerIdent(j["ident"])


def peer_accept(j):
    return PeerAccept()


def peer_verify(j):
    return PeerVerify()


def tracker_accept(j):
    return TrackerAccept()


def tracker_new_peer(j):
    return TrackerNewPeer(j["peer"])


def node_peers(j):
    return NodePeers()


def node_disconnect(j):
    return NodeDisconnect()


def tracker_chain(j):
    return TrackerChain(j["blockchain"])


def peer_transaction(j):
    return PeerTransaction(j["transaction"])


def peer_block(j):
    return PeerBlock(j["block"])


def of_string(s):
    try:
        j = json.loads(s)
        k = j["kind"]
    except Exception:
        return None

    msgs = {Kind.NODE_KEYS: node_keys,
            Kind.TRACKER_IDENT: tracker_ident,
            Kind.NODE_IDENT: node_ident,
            Kind.NODE_PORT: node_port,
            Kind.TRACKER_PEERS: tracker_peers,
            Kind.PEER_IDENT: peer_ident,
            Kind.PEER_VERIFY: peer_verify,
            Kind.PEER_ACCEPT: peer_accept,
            Kind.TRACKER_ACCEPT: tracker_accept,
            Kind.TRACKER_NEW_PEER: tracker_new_peer,
            Kind.NODE_PEERS: node_peers,
            Kind.NODE_DISCONNECT: node_disconnect,
            Kind.TRACKER_CHAIN: tracker_chain,
            Kind.PEER_TRANSACTION: peer_transaction,
            Kind.PEER_BLOCK: peer_block}

    try:
        return msgs[k](j)
    except Exception:
        return None


DEFAULT_RECV = 4096


def recv(sock, enc=None):
    data = bytearray()
    size = None

    while True:
        if size is None:
            packet = sock.recv(DEFAULT_RECV)
        elif size <= 0:
            break
        else:
            packet = sock.recv(size)

        if not packet:
            break
        elif not data:
            size = int.from_bytes(packet[0:4], 'big')
            data.extend(packet[4:])
            size -= len(data)
        else:
            data.extend(packet)
            size -= len(packet)

    if not data:
        raise ValueError

    data = bytes(data)

    if enc:
        try:
            # verify the message with the sender's verify key
            data = pkc.verify(data, enc[0])
            # decrypt the message, providing the sender's public key
            data = enc[2].decrypt(data, enc[1])
        except Exception:
            # failed to verify/decrypt the message
            raise ValueError

    try:
        return of_string(data.decode())
    except UnicodeDecodeError:
        return None
