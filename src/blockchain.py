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

    def check_transaction_validity(self, tran2check):
        """ check blockchain to make sure transaction to be added is valid """
        sender = tran2check["sender"]
        sender_balance = 0

        for block in self.blocks:
            for transaction in block.transactions:
                if transaction["sender"] == sender:
                    sender_balance -= transaction["amount"]
                elif transaction["receiver"] == sender:
                    sender_balance += transaction["amount"]

        return sender_balance >= tran2check["amount"]

    def add_unconfirmed_transaction(self, transaction):
        valid = self.check_transaction_validity(transaction)

        if valid:
            self.unconfirmed.append(transaction)

        return valid
