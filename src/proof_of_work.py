from . import blockchain, util
from threading import Thread, Event


class ProofOfWork:
    def __init__(self, chain, q, difficulty=5):
        self.thread = Thread(target=self.__run, args=(),
                             daemon=False)
        self._stop_event = Event()
        self.chain = chain
        self.q = q
        self.difficulty = difficulty
        super().__init__()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def __run(self):
        h = self.chain.blocks[-1].this_hash.hexdigest()
        unconfirmed_block = blockchain.Block(self.chain.unconfirmed, h)
        # keep incrementing nonce until we "crack"
        # the hash or the thread gets stopped
        n = 0
        while True:
            if self.stopped():
                return

            h = unconfirmed_block.this_hash = unconfirmed_block.hash()
            if int(h.hexdigest()[:self.difficulty], 16) <= 0:
                break

            unconfirmed_block.nonce += 1
            n += 1

        util.printts("Number of rounds to complete pow: %d" % n)

        # push the unconfirmed block onto the synchronized queue
        self.q.put(unconfirmed_block)
