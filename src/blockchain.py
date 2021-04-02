import json
import datetime
import time
from random import randint
from hashlib import sha256


class Block:
    def __init__(self, transactions, previous_block_hash,
                 timestamp=datetime.datetime.now(), nonce=randint(0, 10000)):
        self.transactions = transactions
        self.previous_block_hash = previous_block_hash # hex format
        self.timestamp = timestamp

        self.nonce = nonce
        self.this_hash = self.hash()

    def serialize(self):
        return {"transactions": self.transactions,
                "previous_block_hash": self.previous_block_hash,
                "timestamp": str(self.timestamp),
                "nonce": self.nonce}

    def hash(self):
        return sha256(json.dumps(self.serialize()).encode('utf-8'))

class Blockchain:
    def __init__(self, blocks=[Block([], '')], unconfirmed=[]):
        self.blocks = blocks
        self.unconfirmed = unconfirmed

    def serialize_blocks(self):
        serialized_blocks = []
        for block in self.blocks:
            serialized_blocks.append(block.serialize())
        return serialized_blocks

    def serialize(self):
        return {"blocks": self.serialize_blocks(),
                "unconfirmed": self.unconfirmed}

    def add_block(self, block):
        self.blocks.append(block)
        self.unconfirmed = []


    def add_unconfirmed_transaction(self, transaction, previous_transactions):
        # TODO: check to make sure that sender has enough balance
        # for transaction by looking at previous_transactions
        # return -1 to indicate an invalid transaction
        self.unconfirmed.append(transaction)

        # TODO: the calling program will need to spawn a thread
        # to run the proof of work routine if return value is 1
        return len(self.unconfirmed)

    def proof_of_work(self, q, difficulty=5):
        unconfirmed_block = Block(self.unconfirmed, self.blocks[-1].this_hash.hexdigest())
        
        # keep incrementing nonce until we "crack" the hash
        while True:
            unconfirmed_block.this_hash = unconfirmed_block.hash()
            if int(unconfirmed_block.this_hash.hexdigest()[:difficulty], 16) <= 0:
                break
            unconfirmed_block.nonce += 1

        print("number of rounds to complete pow: %s" % unconfirmed_block.nonce)

        # push the unconfirmed block onto the synchronized queue
        q.put(unconfirmed_block)

