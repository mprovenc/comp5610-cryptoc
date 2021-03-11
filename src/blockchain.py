import time
from random import randint
from hashlib import sha256

class Block:
    def __init__(self, transactions, previous_block_hash):
        self.transactions = transactions
        self.previous_block_hash = previous_block_hash
        self.timestamp = time.localtime()

    def hash(self):
        transactions_as_bytes = bytes(self.transactions)
        return sha256(transactions_as_bytes)

class Blockchain:
    def __init__(self):
        # put an empty block at the start of the chain
        self.chain = [Block([], '')]
        self.unconfirmed = []

    def add_unconfirmed_transaction(self, sender, receiver, amount, previous_transactions):

        # TODO: check to make sure that sender has enough balance for transaction by looking at previous_transactions
        # return -1 to indicate an invalid transaction

        self.unconfirmed.append({'sender': sender, 'receiver': receiver, 'amount': amount})

        # TODO: the calling program will need to spawn a thread to run the proof of work routine if return value is 1
        return len(self.unconfirmed)

    def assemble_block_to_broadcast(self):
        return Block(self.unconfirmed, self.chain[-1].hash())

    def proof_of_work(self):
        #TODO: implement an actual simplified proof of work routine, for now it's just a random backoff value between 0 and 30 seconds
        time.sleep(randint(0, 30000) / 1000)

        return(self.assemble_block_to_broadcast())
