import datetime
from random import randint
from hashlib import sha256

class Block:
    def __init__(self, transactions, previous_block_hash, timestamp=datetime.datetime.now()):
        self.transactions = transactions
        self.previous_block_hash = previous_block_hash
        self.timestamp = timestamp

    def serialize(self):
        return {"transactions": self.transactions,
                "previous_block_hash": self.previous_block_hash,
                "timestamp": self.timestamp}

    def hash(self):
        transactions_as_bytes = bytes(self.transactions)
        return sha256(transactions_as_bytes)

class Blockchain:
    def __init__(self, blocks=[Block([], '')], unconfirmed=[]):
        # put an empty block at the start of the chain
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

    def add_unconfirmed_transaction(self, sender, receiver, amount, previous_transactions):

        # TODO: check to make sure that sender has enough balance for transaction by looking at previous_transactions
        # return -1 to indicate an invalid transaction

        self.unconfirmed.append({'sender': sender, 'receiver': receiver, 'amount': amount})

        # TODO: the calling program will need to spawn a thread to run the proof of work routine if return value is 1
        return len(self.unconfirmed)

    def assemble_block_to_broadcast(self):
        return Block(self.unconfirmed, self.blocks[-1].hash())

    def proof_of_work(self):
        #TODO: implement an actual simplified proof of work routine, for now it's just a random backoff value between 0 and 30 seconds
        time.sleep(randint(0, 30000) / 1000)

        return(self.assemble_block_to_broadcast())
