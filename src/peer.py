from . import pkc


# descriptor for a peer on the network
class Peer:
    def __init__(self, host, ident, port, public_key, verify_key):
        self.host = host
        self.ident = ident
        self.port = port
        self.public_key = public_key
        self.verify_key = verify_key

    def serialize(self):
        return {"host": self.host,
                "ident": self.ident,
                "port": self.port,
                "public_key": pkc.serialize_key(self.public_key),
                "verify_key": pkc.serialize_key(self.verify_key)}
