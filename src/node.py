from queue import Queue
from threading import Thread, Lock
from . import blockchain, message, peer, util, pkc, proof_of_work


class Node:
    def __init__(self, tracker_hostname, tracker_port, port,
                 hostname="localhost"):
        self.tracker_addr = (tracker_hostname, tracker_port)
        self.addr = (hostname, port)
        self.peers = {}
        self.peer_sockets = {}
        self.ident = None
        self.socket = None
        self.chain = None
        self.lock = Lock()
        self.connected = False
        self.key_pair = pkc.KeyPair()
        self.tracker_public_key = None
        self.tracker_verify_key = None
        self.block_queue = None

    def __unlock(self):
        try:
            self.lock.release()
        except RuntimeError:
            pass

    def __lock(self):
        self.lock.acquire()

    def __recv_any(self, sock, enc=None, disc=True):
        try:
            return message.recv(sock, enc)
        except ValueError:
            if disc:
                self.disconnect()
            return False

    def __recv_expect(self, sock, kind, enc=None, disc=True):
        try:
            msg = message.recv(sock, enc)
            if not msg or msg.kind != kind:
                raise ValueError
        except ValueError:
            if disc:
                self.disconnect()
            return False

        return msg

    def __try_connect(self):
        try:
            self.tracker_socket.connect(self.tracker_addr)
            return True
        except ConnectionRefusedError:
            return False

    def connect(self):
        # connect to the tracker
        self.tracker_socket = util.newsock()
        if not self.__try_connect():
            print("Node: connection to tracker on %s:%d refused" %
                  (self.tracker_addr[0], self.tracker_addr[1]))
            return False

        print("Node: connected to tracker on %s:%d" %
              (self.tracker_addr[0], self.tracker_addr[1]))

        self.connected = True

        message.NodeKeys(self.key_pair.serialize_public_key(),
                         self.key_pair.serialize_verify_key()) \
               .send(self.tracker_socket)

        # receive our identifier from the tracker
        msg = self.__recv_expect(self.tracker_socket,
                                 message.Kind.TRACKER_IDENT)
        if msg is False:
            print("Node: failed to receive TRACKER_IDENT")
            return False

        self.ident = msg.msg["ident"]
        self.tracker_public_key = \
            pkc.deserialize_public_key(msg.msg["public_key"])
        self.tracker_verify_key = \
            pkc.deserialize_verify_key(msg.msg["verify_key"])
        print("Node: received ident %d" % self.ident)

        enc_recv = (self.tracker_verify_key,
                    self.tracker_public_key,
                    self.key_pair)

        enc_send = (self.tracker_public_key, self.key_pair)

        message.NodeIdent().send(self.tracker_socket, enc_send)

        # receive our blockchain from the tracker
        msg = self.__recv_expect(self.tracker_socket,
                                 message.Kind.TRACKER_CHAIN,
                                 enc_recv)
        if msg is False:
            print("Node %d: failed to receive TRACKER_CHAIN" % self.ident)
            return False

        chain = msg.msg["blockchain"]
        blocks = []
        for b in chain["blocks"]:
            trans = b["transactions"]
            h = b["previous_block_hash"]
            t = util.deserialize_timestamp(b["timestamp"])
            blocks.append(blockchain.Block(trans, h, t))

        self.chain = blockchain.Blockchain(blocks, chain["unconfirmed"])
        print("Node %d: received chain %s" %
              (self.ident, str(self.chain.serialize())))

        # reply with the port we want to listen on
        message.NodePort(self.addr[1]).send(self.tracker_socket, enc_send)

        # receive our peers
        msg = self.__recv_expect(self.tracker_socket,
                                 message.Kind.TRACKER_PEERS,
                                 enc_recv)
        if msg is False:
            print("Node %d: failed to receive TRACKER_PEERS" % self.ident)
            return False

        # populate with the current peers
        peers = msg.msg["peers"]
        for p in peers:
            ident = p["ident"]
            public_key = pkc.deserialize_public_key(p["public_key"])
            verify_key = pkc.deserialize_verify_key(p["verify_key"])
            self.peers[ident] = peer.Peer(p["host"],
                                          ident,
                                          p["port"],
                                          public_key,
                                          verify_key)

        # tell the tracker we received the peers
        message.NodePeers().send(self.tracker_socket, enc_send)

        # wait to start listening
        msg = self.__recv_expect(self.tracker_socket,
                                 message.Kind.TRACKER_ACCEPT,
                                 enc_recv)
        if msg is False:
            print("Node %d: failed to receive TRACKER_ACCEPT" % self.ident)
            return False

        print("Node %d: accepted by tracker" % self.ident)

        # start listening on our desired port
        self.socket = util.newsock()
        self.socket.bind(self.addr)
        print("Node %d: bind to %s:%d" %
              (self.ident, self.addr[0], self.addr[1]))
        self.socket.listen(5)
        print("Node %d: listen on %s:%d" %
              (self.ident, self.addr[0], self.addr[1]))

        # connect with all of our peers
        rejected = []
        for ident, p in self.peers.items():
            # establish connection
            conn = util.newsock()
            conn.connect((p.host, p.port))
            print("Node %d: connected to peer %d on %s:%d" %
                  (self.ident, p.ident, p.host, p.port))

            # tell them our identifier
            message.PeerIdent(self.ident).send(conn)

            enc_send_p = (p.public_key, self.key_pair)
            enc_recv_p = (p.verify_key, p.public_key, self.key_pair)

            def rej():
                rejected.append((conn, p.ident))
                print("Node %d: rejected by peer %d on %s:%d" %
                      (self.ident, p.ident, p.host, p.port))

            # wait for the peer to ask for verification
            reply = self.__recv_expect(conn, message.Kind.PEER_VERIFY,
                                       enc_recv_p, disc=False)
            if reply is False:
                rej()
                continue

            print("Node %d: verifying identity with peer %d" %
                  (self.ident, p.ident))
            message.PeerVerify().send(conn, enc_send_p)

            # wait for acceptance
            reply = self.__recv_expect(conn, message.Kind.PEER_ACCEPT,
                                       enc_recv_p, disc=False)
            if reply is False:
                rej()
                continue

            # register the connection
            print("Node %d: accepted by peer %d on %s:%d" %
                  (self.ident, p.ident, p.host, p.port))
            self.peer_sockets[p.ident] = conn

        # we can't communicate with peers that rejected us
        for conn, ident in rejected:
            self.__remove_peer(conn, ident)

        for ident in self.peers.keys():
            self.__start_receiver(ident)

        return True

    def __start_receiver(self, ident, conn=None):
        self.__lock()

        # register the node and spawn a thread to listen for messages
        if conn:
            self.peer_sockets[ident] = conn

        thread = Thread(target=self.__recv_peer, args=(ident,),
                        daemon=True)
        thread.start()

        self.__unlock()

    def accept(self):
        conn, addr = self.socket.accept()
        print("Node %d: opened connection %s:%d" %
              (self.ident, addr[0], addr[1]))

        # the peer must identify themselves
        msg = self.__recv_expect(conn, message.Kind.PEER_IDENT, disc=False)
        if msg is False:
            print("Node %d: rejecting connection %s:%d" %
                  (self.ident, addr[0], addr[1]))
            conn.close()
            return

        ident = msg.msg["ident"]
        if ident not in self.peers:
            print("Node %d: rejecting connection %s:%d" %
                  (self.ident, addr[0], addr[1]))
            conn.close()
            return

        pk = self.peers[ident].public_key
        enc_send = (pk, self.key_pair)
        enc_recv = (self.peers[ident].verify_key, pk, self.key_pair)

        # the peer should verify their identity with us
        # since we were provided by the tracker with their
        # public key and verify key. this should let us
        # know if they are who they say they are.
        message.PeerVerify().send(conn, enc_send)

        msg = self.__recv_expect(conn, message.Kind.PEER_VERIFY,
                                 enc_recv, disc=False)
        if msg is False:
            print("Node %d: rejecting connection %s:%d from peer %d" %
                  (self.ident, addr[0], addr[1], ident))
            conn.close()
            return

        # tell them we've accepted them
        message.PeerAccept().send(conn, enc_send)
        print("Node %d: accepting connection from peer %d on %s:%d" %
              (self.ident, ident, addr[0], addr[1]))

        self.__start_receiver(ident, conn)

    def recv_tracker(self):
        msg = None
        enc_recv = (self.tracker_verify_key,
                    self.tracker_public_key,
                    self.key_pair)

        msg = self.__recv_any(self.tracker_socket, enc_recv)
        if msg is False:
            print("Node %d: connection with tracker broken" % self.ident)
            return False

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
            public_key = pkc.deserialize_public_key(p["public_key"])
            verify_key = pkc.deserialize_verify_key(p["verify_key"])

            print("Node %d: received new peer %d on %s:%d" %
                  (self.ident, ident, host, port))

            self.__lock()

            self.peers[ident] = peer.Peer(host,
                                          ident,
                                          port,
                                          public_key,
                                          verify_key)

            self.__unlock()

        return True

    def disconnect(self):
        if not self.connected:
            return

        if self.ident is None:
            print("Node: disconnecting")
        else:
            print("Node %d: disconnecting" % self.ident)

        msg = message.NodeDisconnect()

        def do_send(conn, enc=None):
            try:
                # the socket might contain a bad file descriptor
                # (i.e. the connection is already gone)
                # so just continue as normal if sending fails
                msg.send(conn, enc)
            except OSError:
                pass

        self.__lock()

        if self.tracker_public_key:
            do_send(self.tracker_socket,
                    (self.tracker_public_key, self.key_pair))
        else:
            do_send(self.tracker_socket)

        for p in self.peers.values():
            conn = self.peer_sockets[p.ident]
            do_send(conn, (p.public_key, self.key_pair))

        self.tracker_socket.close()
        self.peers = {}
        self.peer_sockets = {}
        self.connected = False

        self.__unlock()

    def __recv_peer(self, ident):
        print("Node %d: monitoring messages from peer %d" %
              (self.ident, ident))

        conn = self.peer_sockets[ident]
        enc_recv = (self.peers[ident].verify_key,
                    self.peers[ident].public_key,
                    self.key_pair)

        while True:
            msg = self.__recv_any(conn, enc_recv, disc=False)
            if msg is False:
                print("Node %d: connection with peer %d broken" %
                      (self.ident, ident))
                self.__remove_peer(conn, ident)
                break

            if not msg:
                continue

            if msg.kind == message.Kind.NODE_DISCONNECT:
                print("Node %d: peer %d is disconnecting" %
                      (self.ident, ident))
                self.__remove_peer(conn, ident)
                break
            elif msg.kind == message.Kind.PEER_TRANSACTION:
                print("Node %d: received transaction from peer %s" %
                      (self.ident, ident))
                self.recv_transaction(msg.msg["transaction"])
            elif msg.kind == message.Kind.PEER_BLOCK:
                util.printts("Node %d: received block from peer %s" %
                             (self.ident, ident))
                self.recv_block(msg.msg["block"])

    def __remove_peer(self, conn, ident):
        self.__lock()

        if conn:
            conn.close()

        if ident in self.peers:
            self.peers.pop(ident, None)
            self.peer_sockets.pop(ident, None)

        self.__unlock()

    def __broadcast_message(self, msg):
        util.printts("Node %d: sending a broadcast message" % self.ident)

        invalid = []
        for ident, p in self.peers.items():
            conn = self.peer_sockets.get(ident, None)
            if conn:
                msg.send(conn, enc=(p.public_key, self.key_pair))
            else:
                invalid.append(ident)

        # we may have tried to send to peers that we never
        # established a connection with, so it's best to
        # remove them once we attempt to send them a message.
        for ident in invalid:
            self.__remove_peer(None, ident)

    def send_transaction(self, receiver, amount):
        # serialize the transaction before broadcast
        transaction = {'sender': self.ident,
                       'receiver': receiver,
                       'amount': amount}
        msg = message.PeerTransaction(transaction)

        self.__broadcast_message(msg)

        # make sure it is added to this node's list of unconfirmed transactions
        self.recv_transaction(transaction)

    def recv_transaction(self, transaction):
        if self.chain.add_unconfirmed_transaction(transaction, []) == 3:
            # start mining block
            self.block_queue = Queue()
            mining_thread = proof_of_work.ProofOfWork(self.chain,
                                                      self.block_queue)
            mining_thread.start()
            val = self.block_queue.get()
            if val == "STOP":
                mining_thread.stop()
                mining_thread.join()
            else:
                self.send_block(val)

    def send_block(self, block):
        util.printts("Node %d: finished mining, sending the block..." %
                     self.ident)
        msg = message.PeerBlock(block.serialize())

        # make sure it is added to this node's chain
        self.recv_block(block.serialize())

        self.__broadcast_message(msg)

    def recv_block(self, block):
        util.printts("Node %d: receiving block" % self.ident)
        self.block_queue.put("STOP")
        self.chain.add_block(blockchain.Block(block["transactions"],
                                              block["previous_block_hash"]))
