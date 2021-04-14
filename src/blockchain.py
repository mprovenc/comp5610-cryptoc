import json
import datetime
from random import randint
from hashlib import sha256


class Block:
    def __init__(self, transactions, previous_block_hash,
                 timestamp=datetime.datetime.now(), nonce=randint(0, 10000)):
        self.transactions = transactions
        self.previous_block_hash = previous_block_hash  # hex format
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

        return len(self.unconfirmed)
