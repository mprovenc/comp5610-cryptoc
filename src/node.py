import socket
from . import message, peer, util


class Node:
    def __init__(self, tracker_hostname, tracker_port, port,
                 hostname="localhost"):
        self.tracker_addr = (tracker_hostname, tracker_port)
        self.addr = (hostname, port)
        self.peers = {}
        self.peer_sockets = {}
        self.ident = None
        self.socket = None

    def connect(self):
        # connect to the tracker
        self.tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tracker_socket.connect(self.tracker_addr)
        print("Node: connected to tracker on %s:%d" %
              (self.tracker_addr[0], self.tracker_addr[1]))

        # receive our identifier from the tracker
        msg = message.of_string(util.recvall(self.tracker_socket))
        if msg is None or msg.kind != message.Kind.TRACKER_IDENT:
            print("Node: failed to receive TRACKER_IDENT")
            self.disconnect()
            return False
        self.ident = msg.msg["ident"]
        print("Node: received ident %d" % self.ident)

        # reply with the port we want to listen on
        reply = message.NodePort(self.addr[1])
        util.sendall(self.tracker_socket, reply.to_string())

        # receive our peers
        msg = message.of_string(util.recvall(self.tracker_socket))
        if msg is None or msg.kind != message.Kind.TRACKER_PEERS:
            print("Node %d: failed to receive TRACKER_PEERS %s" % self.ident)
            self.disconnect()
            return False

        # populate with the current peers
        peers = msg.msg["peers"]
        for p in peers:
            ident = p["ident"]
            self.peers[ident] = peer.Peer(p["host"], ident, p["port"])

        # wait to start listening
        msg = message.of_string(util.recvall(self.tracker_socket))
        if msg is None or msg.kind != message.Kind.TRACKER_ACCEPT:
            print("Node %d: failed to receive TRACKER_ACCEPT" % self.ident)
            self.disconnect()
            return False
        print("Node %d: accepted by tracker" % self.ident)

        # start listening on our desired port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(self.addr)
        print("Node %d: bind to %s:%d" %
              (self.ident, self.addr[0], self.addr[1]))
        self.socket.listen(5)
        print("Node %d: listen on %s:%d" %
              (self.ident, self.addr[0], self.addr[1]))

        # connect with all of our peers
        for p in self.peers.values():
            # establish connection
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect((p.host, p.port))
            print("Node %d: connected to peer %d on %s:%d" %
                  (self.ident, p.ident, p.host, p.port))

            # tell them our identifier
            msg = message.PeerIdent(self.ident)
            util.sendall(conn, msg.to_string())

            # wait for acceptance
            reply = message.of_string(util.recvall(conn))
            if reply is not None and reply.kind == message.Kind.PEER_ACCEPT:
                print("Node %d: accepted by peer %d on %s:%d" %
                      (self.ident, p.ident, p.host, p.port))
                self.peer_sockets[p.ident] = conn
            else:
                print("Node %d: rejected by peer %d on %s:%d" %
                      (self.ident, p.ident, p.host, p.port))

        return True

    def accept(self):
        assert(self.is_valid())
        conn, addr = self.socket.accept()
        print("Node %d: opened connection %s:%d" %
              (self.ident, addr[0], addr[1]))

        try:
            # the peer must identify themselves
            msg = message.of_string(util.recvall(conn))
            assert(msg.kind == message.Kind.PEER_IDENT)
            ident = msg.msg["ident"]

            # tell them we've accepted them
            reply = message.PeerAccept()
            util.sendall(conn, reply.to_string())
            print("Node %d: accepting connection from peer %d on %s:%d" %
                  (self.ident, ident, addr[0], addr[1]))
            self.peer_sockets[ident] = conn
        except:
            print("Node %d: rejecting connection %s:%d" %
                  (self.ident, addr[0], addr[1]))
            conn.close()

    def recv_tracker(self):
        assert(self.is_valid())

        try:
            msg = message.of_string(util.recvall(self.tracker_socket))

            # a new peer connected, and they will soon attempt to establish
            # a direct connection with us, so register them so that we can
            # recognize them in such an event.
            if msg.kind == message.Kind.TRACKER_NEW_PEER:
                p = msg.msg["peer"]
                ident = p["ident"]
                self.peers[ident] = peer.Peer(p["host"], ident, p["port"])
        except:
            pass

    def disconnect(self):
        self.tracker_socket.close()

    def is_valid(self):
        return self.ident is not None \
            and self.socket is not None
