import unittest
from invoices import InvoiceService


class Publisher:
    def __init__(self):
        self.calls = []

    def publish(self, invoice_id, body):
        self.calls.append((invoice_id, body))
        return "receipt:" + invoice_id


class ExistingTests(unittest.TestCase):
    def test_publish_one(self):
        publisher = Publisher()
        result = InvoiceService(publisher).publish_one({"id": "a", "amount": 10})
        self.assertEqual(result, "receipt:a")
        self.assertEqual(publisher.calls, [("a", "invoice=a;amount=10")])


if __name__ == "__main__":
    unittest.main()
