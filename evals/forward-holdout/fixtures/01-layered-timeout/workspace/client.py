class Client:
    def __init__(self, transport):
        self._transport = transport

    def request(self, path):
        return self._transport.send(path)
