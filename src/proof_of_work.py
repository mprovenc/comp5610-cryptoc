from . import blockchain
from threading import Thread, Event

class ProofOfWork(Thread):
    def __init__(self, chain, q, difficulty=5):
        self._stop_event = Event()
        self.chain = chain
        self.q = q
        self.difficulty = difficulty
        super().__init__()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self):
        unconfirmed_block = blockchain.Block(self.chain.unconfirmed, self.chain.blocks[-1].this_hash.hexdigest())

        # keep incrementing nonce until we "crack" the hash or the thread gets stopped
        while True:
            if self.stopped():
                return
            unconfirmed_block.this_hash = unconfirmed_block.hash()
            if int(unconfirmed_block.this_hash.hexdigest()[:self.difficulty], 16) <= 0:
                break
            unconfirmed_block.nonce += 1

        print("number of rounds to complete pow: %s" % unconfirmed_block.nonce)

        # push the unconfirmed block onto the synchronized queue
        self.q.put(unconfirmed_block)