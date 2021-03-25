import rsa
import multiprocessing


DEFAULT_KEY_SIZE = 2048


class KeyPair:
    def __init__(self, size=DEFAULT_KEY_SIZE):
        # if a large key size is chosen then it can take a while
        # to generate the key pair. luckily we can divide the work
        # among all schedulable cores.
        (self.public_key, self.private_key) = \
            rsa.newkeys(size, poolsize=multiprocessing.cpu_count())

    def encrypt_public(self, msg):
        return rsa.pkcs1.encrypt(msg, self.public_key)

    def decrypt_public(self, msg):
        return rsa.pkcs1.decrypt(msg, self.public_key)

    def encrypt_private(self, msg):
        return rsa.pkcs1.encrypt(msg, self.private_key)

    def decrypt_private(self, msg):
        return rsa.pkcs1.decrypt(msg, self.private_key)

    def sign(self, msg):
        return rsa.pkcs1.sign(msg, self.private_key, 'SHA-256')

    def serialize_public_key(self):
        return (self.public_key.n, self.public_key.e)


def verify(msg, sig, public_key):
    k = rsa.PublicKey(public_key[0], public_key[1])
    return rsa.pkcs1.verify(msg, sig, k) == 'SHA-256'
