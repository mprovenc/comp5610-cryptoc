import nacl.utils
from nacl.public import PublicKey, PrivateKey, Box
from nacl.signing import SigningKey, VerifyKey


class KeyPair:
    def __init__(self):
        self.private_key = PrivateKey.generate()
        self.signing_key = SigningKey.generate()

    def encrypt(self, msg, public_key):
        box = Box(self.private_key, public_key)
        nonce = nacl.utils.random(Box.NONCE_SIZE)
        enc = box.encrypt(msg, nonce)
        return bytes(enc)

    def decrypt(self, msg, public_key):
        box = Box(self.private_key, public_key)
        return bytes(box.decrypt(msg))

    def sign(self, msg):
        return bytes(self.signing_key.sign(msg))

    def serialize_public_key(self):
        return self.private_key.public_key.encode()

    def serialize_verify_key(self):
        return self.signing_key.verify_key.encode()


def deserialize_public_key(public_key):
    return PublicKey(public_key)


def deserialize_verify_key(verify_key):
    return VerifyKey(verify_key)


def verify(msg, verify_key):
    return verify_key.verify(msg)
