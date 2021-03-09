# descriptor for a peer on the network
class Peer:
    def __init__(self, host, ident, port):
        self.host = host
        self.ident = ident
        self.port = port

    def serialize(self):
        return {"host": self.host,
                "ident": self.ident,
                "port": self.port}
