import socket
from threading import Thread, Lock
from . import message, peer


class Node:
    def __init__(self, tracker_hostname, tracker_port, port,
                 hostname="localhost"):
        self.tracker_addr = (tracker_hostname, tracker_port)
        self.addr = (hostname, port)
        self.peers = {}
        self.peer_sockets = {}
        self.ident = None
        self.socket = None
        self.lock = Lock()

    def __unlock(self):
        try:
            self.lock.release()
        except RuntimeError:
            pass

    def __lock(self):
        self.lock.acquire()

    def connect(self):
        # connect to the tracker
        self.tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tracker_socket.connect(self.tracker_addr)
        print("Node: connected to tracker on %s:%d" %
              (self.tracker_addr[0], self.tracker_addr[1]))

        # receive our identifier from the tracker
        msg = message.recv(self.tracker_socket)
        if not msg or msg.kind != message.Kind.TRACKER_IDENT:
            print("Node: failed to receive TRACKER_IDENT")
            self.disconnect()
            return False
        self.ident = msg.msg["ident"]
        print("Node: received ident %d" % self.ident)

        # reply with the port we want to listen on
        message.NodePort(self.addr[1]).send(self.tracker_socket)

        # receive our peers
        msg = message.recv(self.tracker_socket)
        if not msg or msg.kind != message.Kind.TRACKER_PEERS:
            print("Node %d: failed to receive TRACKER_PEERS" % self.ident)
            self.disconnect()
            return False

        # populate with the current peers
        peers = msg.msg["peers"]
        for p in peers:
            ident = p["ident"]
            self.peers[ident] = peer.Peer(p["host"], ident, p["port"])

        # tell the tracker we received the peers
        message.NodePeers().send(self.tracker_socket)

        # wait to start listening
        msg = message.recv(self.tracker_socket)
        if not msg or msg.kind != message.Kind.TRACKER_ACCEPT:
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
            message.PeerIdent(self.ident).send(conn)

            # wait for acceptance
            reply = message.recv(conn)
            if reply and reply.kind == message.Kind.PEER_ACCEPT:
                # register the connection
                print("Node %d: accepted by peer %d on %s:%d" %
                      (self.ident, p.ident, p.host, p.port))
                self.peer_sockets[p.ident] = conn
            else:
                print("Node %d: rejected by peer %d on %s:%d" %
                      (self.ident, p.ident, p.host, p.port))

        return True

    def accept(self):
        conn, addr = self.socket.accept()
        print("Node %d: opened connection %s:%d" %
              (self.ident, addr[0], addr[1]))

        # the peer must identify themselves
        msg = message.recv(conn)
        if not msg or msg.kind != message.Kind.PEER_IDENT:
            print("Node %d: rejecting connection %s:%d" %
                  (self.ident, addr[0], addr[1]))
            conn.close()
            return

        ident = msg.msg["ident"]

        # tell them we've accepted them
        message.PeerAccept().send(conn)
        print("Node %d: accepting connection from peer %d on %s:%d" %
              (self.ident, ident, addr[0], addr[1]))

        self.__lock()
        self.peer_sockets[ident] = conn
        thread = Thread(target=self.__recv_peer, args=(ident,),
                        daemon=True)
        thread.start()
        self.__unlock()

    def recv_tracker(self):
        msg = message.recv(self.tracker_socket)
        if not msg:
            return

        # a new peer connected, and they will soon attempt to establish
        # a direct connection with us, so register them so that we can
        # recognize them in such an event.
        if msg.kind == message.Kind.TRACKER_NEW_PEER:
            p = msg.msg["peer"]
            ident = p["ident"]
            host = p["host"]
            port = p["port"]
            print("Node %d: received new peer %d on %s:%d" %
                  (self.ident, ident, host, port))

            self.__lock()
            self.peers[ident] = peer.Peer(host, ident, port)
            self.__unlock()

    def disconnect(self):
        if self.ident:
            print("Node %d: disconnecting" % self.ident)
        else:
            print("Node: disconnecting")

        msg = message.NodeDisconnect()
        msg.send(self.tracker_socket)
        for conn in self.peer_sockets.values():
            msg.send(conn)

    def __recv_peer(self, ident):
        print("Node %d: monitoring messages from peer %d" %
              (self.ident, ident))

        while True:
            conn = self.peer_sockets[ident]
            msg = message.recv(conn)
            if not msg:
                continue

            if msg.kind == message.Kind.NODE_DISCONNECT:
                print("Node %d: peer %d is disconnecting" %
                      (self.ident, ident))

                self.__lock()
                conn.close()
                self.peers.pop(ident)
                self.peer_sockets.pop(ident)
                self.__unlock()
                break
