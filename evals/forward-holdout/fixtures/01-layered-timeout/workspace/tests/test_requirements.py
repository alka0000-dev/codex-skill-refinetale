import math
import unittest
from client import Client


class Transport:
    def __init__(self):
        self.calls = []

    def send(self, path, **options):
        self.calls.append((path, options))
        return options["timeout"]


class RequirementTests(unittest.TestCase):
    def test_precedence_and_default(self):
        transport = Transport()
        client = Client(transport, timeout=3)
        self.assertEqual(client.request("/a", timeout=1.5), 1.5)
        self.assertEqual(client.request("/b"), 3)
        self.assertEqual(Client(transport).request("/c"), 5.0)

    def test_invalid_explicit_values_do_not_send_or_fallback(self):
        for value in (0, -1, True, math.nan, math.inf):
            with self.subTest(value=value):
                transport = Transport()
                client = Client(transport, timeout=2)
                with self.assertRaises(ValueError):
                    client.request("/bad", timeout=value)
                self.assertEqual(transport.calls, [])

    def test_invalid_client_value_is_rejected(self):
        for value in (False, 0, float("-inf")):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    Client(Transport(), timeout=value)


if __name__ == "__main__":
    unittest.main()
