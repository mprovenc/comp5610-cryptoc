import socket
from . import message, peer, util


class Tracker:
    def __init__(self, port, hostname="localhost"):
        self.addr = (hostname, port)
        self.nodes = {}
        self.node_ports = {}
        self.node_sockets = {}
        self.ident_count = 0

    def start(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(self.addr)
        print("Tracker: bind to %s:%d" % (self.addr[0], self.addr[1]))
        self.socket.listen(5)
        print("Tracker: listen on %s:%d" % (self.addr[0], self.addr[1]))

    def accept(self):
        conn, addr = self.socket.accept()
        print("Tracker: opened connection %s:%d" % (addr[0], addr[1]))

        try:
            # assign the next available identifier
            ident = self.ident_count
            msg = message.TrackerIdent(ident)
            util.sendall(conn, msg.to_string())

            # node must tell us what port they intend to listen on
            reply = message.of_string(util.recvall(conn))
            assert(reply.kind == message.Kind.NODE_PORT)
            port = reply.msg["port"]
            print("Tracker: connection %s:%d will listen on port %d" %
                  (addr[0], addr[1], port))

            # inform the node of its peers
            peers = []
            for p in self.nodes.values():
                peers.append(p.serialize())
            msg = message.TrackerPeers(peers)
            util.sendall(conn, msg.to_string())

            # inform existing nodes of their new peer
            new_peer = peer.Peer(addr[0], ident, port).serialize()
            for nconn in self.node_sockets.values():
                msg = message.TrackerNewPeer(new_peer)
                util.sendall(nconn, msg.to_string())

            # inform the node that it has been accepted
            msg = message.TrackerAccept()
            util.sendall(conn, msg.to_string())

            # register the node
            self.nodes[ident] = peer.Peer(addr[0], ident, port)
            self.node_ports[ident] = addr[1]
            self.node_sockets[ident] = conn
            self.ident_count += 1
        except:
            print("Tracker: rejecting connection %s:%d" % (addr[0], addr[1]))
            conn.close()

    def stop(self):
        print("Tracker: shutting down")
        for conn in self.node_sockets.values():
            conn.close()
        self.socket.close()
