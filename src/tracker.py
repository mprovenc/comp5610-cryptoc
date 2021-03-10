import socket
from threading import Lock
from . import message, peer


class Tracker:
    def __init__(self, port, hostname="localhost"):
        self.addr = (hostname, port)
        self.nodes = {}
        self.node_ports = {}
        self.node_sockets = {}
        self.ident_count = 0
        self.lock = Lock()

    def __unlock(self):
        if self.lock.locked():
            self.lock.release()

    def __lock(self):
        self.lock.acquire()

    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(self.addr)
        print("Tracker: bind to %s:%d" % (self.addr[0], self.addr[1]))
        self.socket.listen(5)
        print("Tracker: listen on %s:%d" % (self.addr[0], self.addr[1]))

    def accept(self):
        conn, addr = self.socket.accept()
        print("Tracker: opened connection %s:%d" % (addr[0], addr[1]))

        self.__lock()

        try:
            # assign the next available identifier
            ident = self.ident_count
            message.TrackerIdent(ident).send(conn)

            # node must tell us what port they intend to listen on
            reply = message.recv(conn)
            assert(reply and reply.kind == message.Kind.NODE_PORT)
            port = reply.msg["port"]
            print("Tracker: connection %s:%d will listen on port %d" %
                  (addr[0], addr[1], port))

            # inform the node of its peers
            peers = []
            for p in self.nodes.values():
                peers.append(p.serialize())
            message.TrackerPeers(peers).send(conn)

            # wait for the node to inform us that it received the peers
            reply = message.recv(conn)
            assert(reply and reply.kind == message.Kind.NODE_PEERS)
            print("Tracker: node %d accepted peers" % ident)

            # inform existing nodes of their new peer
            new_peer = peer.Peer(addr[0], ident, port).serialize()
            for nconn in self.node_sockets.values():
                message.TrackerNewPeer(new_peer).send(nconn)

            # inform the node that it has been accepted
            message.TrackerAccept().send(conn)

            # register the node
            self.nodes[ident] = peer.Peer(addr[0], ident, port)
            self.node_ports[ident] = addr[1]
            self.node_sockets[ident] = conn
            self.ident_count += 1
        except AssertionError:
            print("Tracker: rejecting connection %s:%d" % (addr[0], addr[1]))
            conn.close()

        self.__unlock()

    def stop(self):
        print("Tracker: shutting down")

        for conn in self.node_sockets.values():
            conn.close()

        self.socket.close()
