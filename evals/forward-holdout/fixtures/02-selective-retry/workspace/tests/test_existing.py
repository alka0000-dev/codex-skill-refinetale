import unittest
from delivery import deliver


class Sender:
    def send(self, message):
        return "sent:" + message


class ExistingTests(unittest.TestCase):
    def test_delivers_once(self):
        self.assertEqual(deliver(Sender(), "hello"), "sent:hello")


if __name__ == "__main__":
    unittest.main()
