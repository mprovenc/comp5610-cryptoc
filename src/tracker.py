from threading import Thread, Lock
from . import blockchain, message, peer, util, pkc


class Tracker:
    def __init__(self, port, hostname="localhost"):
        self.addr = (hostname, port)
        self.nodes = {}
        self.node_sockets = {}
        self.ident_count = 0
        self.lock = Lock()
        self.chain = blockchain.Blockchain()
        self.key_pair = pkc.KeyPair()

    def __unlock(self):
        try:
            self.lock.release()
        except RuntimeError:
            pass

    def __lock(self):
        self.lock.acquire()

    def start(self):
        self.socket = util.newsock()
        self.socket.bind(self.addr)
        print("Tracker: bind to %s:%d" % (self.addr[0], self.addr[1]))
        self.socket.listen(5)
        print("Tracker: listen on %s:%d" % (self.addr[0], self.addr[1]))

    def accept(self):
        conn, addr = self.socket.accept()
        print("Tracker: opened connection %s:%d" % (addr[0], addr[1]))

        ident = None
        try:
            initial = message.recv(conn)
            assert(initial and initial.kind == message.Kind.NODE_KEYS)

            public_key = pkc.deserialize_public_key(initial.msg["public_key"])
            verify_key = pkc.deserialize_verify_key(initial.msg["verify_key"])

            # assign the next available identifier
            ident = self.ident_count
            message.TrackerIdent(ident,
                                 self.key_pair.serialize_public_key(),
                                 self.key_pair.serialize_verify_key()) \
                   .send(conn)

            enc_send = (public_key, self.key_pair)
            enc_recv = (verify_key, public_key, self.key_pair)

            reply = message.recv(conn, enc_recv)
            assert(reply and reply.kind == message.Kind.NODE_IDENT)
            print("Tracker: node %d (connection %s:%d) received identifier" %
                  (ident, addr[0], addr[1]))

            # send the most current blockchain
            message.TrackerChain(self.chain.serialize()).send(conn, enc_send)

            # node must tell us what port they intend to listen on
            reply = message.recv(conn, enc_recv)
            assert(reply and reply.kind == message.Kind.NODE_PORT)
            port = reply.msg["port"]
            print("Tracker: node %d will listen on port %d" % (ident, port))

            # tell the node that it must start listening
            message.NodeListen().send(conn, enc_send)

            reply = message.recv(conn, enc_recv)
            assert(reply and reply.kind == message.Kind.NODE_LISTEN)
            print("Tracker: node %d is ready to listen on port %d" %
                  (ident, port))

            # inform the node of its peers
            peers = []
            for p in self.nodes.values():
                peers.append(p.serialize())
            message.TrackerPeers(peers).send(conn, enc_send)

            # wait for the node to inform us that it received the peers
            reply = message.recv(conn, enc_recv)
            assert(reply and reply.kind == message.Kind.NODE_PEERS)
            print("Tracker: node %d accepted peers" % ident)

            # inform existing nodes of their new peer
            new_peer = peer.Peer(addr[0], ident, port, public_key, verify_key)
            new_peer_s = new_peer.serialize()
            for n in self.nodes.values():
                nconn = self.node_sockets[n.ident]
                nenc = (n.public_key, self.key_pair)
                message.TrackerNewPeer(new_peer_s).send(nconn, nenc)

            # inform the node that it has been accepted
            message.TrackerAccept().send(conn, enc_send)

            self.__lock()

            # register the node.
            # this operation shouldn't ever fail, so we can
            # have confidence that the lock will be released.
            self.nodes[ident] = peer.Peer(addr[0],
                                          ident,
                                          port,
                                          public_key,
                                          verify_key)

            self.node_sockets[ident] = conn
            self.ident_count += 1

            self.__unlock()

            # start a thread to listen for node messages
            thread = Thread(target=self.__recv_node, args=(ident,),
                            daemon=True)
            thread.start()

        except AssertionError:
            print("Tracker: rejecting connection %s:%d" % (addr[0], addr[1]))
            conn.close()

        except ValueError:
            print("Tracker: connection %s:%d broken" % (addr[0], addr[1]))
            self.__remove_node(conn, ident)

    def stop(self):
        print("Tracker: shutting down")

        for conn in self.node_sockets.values():
            conn.close()

        self.socket.close()
        self.nodes = {}
        self.node_sockets = {}

    def __recv_node(self, ident):
        print("Tracker: monitoring messages from node %d" % ident)

        conn = self.node_sockets[ident]
        n = self.nodes[ident]
        enc_recv = (n.verify_key, n.public_key, self.key_pair)

        while True:
            msg = None
            try:
                msg = message.recv(conn, enc_recv)
            except ValueError:
                print("Tracker: connection with node %d was broken" % ident)
                self.__remove_node(conn, ident)
                break

            if not msg:
                continue

            if msg.kind == message.Kind.NODE_DISCONNECT:
                print("Tracker: node %d is disconnecting" % ident)
                self.__remove_node(conn, ident)
                break

    def __remove_node(self, conn, ident):
        self.__lock()

        conn.close()

        if ident is not None and ident in self.nodes:
            self.nodes.pop(ident, None)
            self.node_sockets.pop(ident, None)

        self.__unlock()
