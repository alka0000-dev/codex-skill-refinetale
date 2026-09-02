import unittest
from client import Client


class Transport:
    def __init__(self):
        self.calls = []

    def send(self, path, **options):
        self.calls.append((path, options))
        return "ok"


class ExistingTests(unittest.TestCase):
    def test_request_returns_transport_result(self):
        transport = Transport()
        self.assertEqual(Client(transport).request("/health"), "ok")
        self.assertEqual(transport.calls[0][0], "/health")


if __name__ == "__main__":
    unittest.main()
