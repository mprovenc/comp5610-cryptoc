from nacl.public import PublicKey, PrivateKey, Box
from nacl.signing import SigningKey, VerifyKey
import base64


def serialize_key(key):
    return base64.b64encode(key.encode()).decode()


class KeyPair:
    def __init__(self):
        self.private_key = PrivateKey.generate()
        self.signing_key = SigningKey.generate()

    def encrypt(self, msg, public_key):
        box = Box(self.private_key, public_key)
        enc = box.encrypt(msg)
        return bytes(enc)

    def decrypt(self, msg, public_key):
        box = Box(self.private_key, public_key)
        return bytes(box.decrypt(msg))

    def sign(self, msg):
        return bytes(self.signing_key.sign(msg))

    def public_key(self):
        return self.private_key.public_key

    def serialize_public_key(self):
        return serialize_key(self.public_key())

    def verify_key(self):
        return self.signing_key.verify_key

    def serialize_verify_key(self):
        return serialize_key(self.verify_key())


def deserialize_public_key(public_key):
    return PublicKey(base64.b64decode(public_key))


def deserialize_verify_key(verify_key):
    return VerifyKey(base64.b64decode(verify_key))


def verify(msg, verify_key):
    return verify_key.verify(msg)
