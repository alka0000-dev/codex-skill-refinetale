import unittest
from invoices import InvoiceService


class Publisher:
    def __init__(self, fail_on=None):
        self.calls = []
        self.fail_on = fail_on

    def publish(self, invoice_id, body):
        self.calls.append((invoice_id, body))
        if invoice_id == self.fail_on:
            raise RuntimeError("publish failed")
        return "receipt:" + invoice_id


class TrackingService(InvoiceService):
    def __init__(self, publisher, events):
        super().__init__(publisher)
        self.events = events

    def render(self, invoice):
        self.events.append("render:" + invoice.get("id", "missing"))
        return super().render(invoice)


class RequirementTests(unittest.TestCase):
    def test_prepares_all_before_publishing(self):
        events = []
        publisher = Publisher()
        original_publish = publisher.publish
        publisher.publish = lambda invoice_id, body: (events.append("publish:" + invoice_id), original_publish(invoice_id, body))[1]
        service = TrackingService(publisher, events)
        result = service.publish_all([{"id": "a", "amount": 1}, {"id": "b", "amount": 2}])
        self.assertEqual(result, ["receipt:a", "receipt:b"])
        self.assertEqual(events, ["render:a", "render:b", "publish:a", "publish:b"])

    def test_render_failure_publishes_nothing(self):
        publisher = Publisher()
        with self.assertRaises(ValueError):
            InvoiceService(publisher).publish_all([{"id": "a", "amount": 1}, {"id": "bad"}])
        self.assertEqual(publisher.calls, [])

    def test_publish_failure_stops_following_items(self):
        publisher = Publisher(fail_on="b")
        with self.assertRaises(RuntimeError):
            InvoiceService(publisher).publish_all([
                {"id": "a", "amount": 1}, {"id": "b", "amount": 2}, {"id": "c", "amount": 3}
            ])
        self.assertEqual([call[0] for call in publisher.calls], ["a", "b"])

    def test_empty_input(self):
        publisher = Publisher()
        self.assertEqual(InvoiceService(publisher).publish_all([]), [])
        self.assertEqual(publisher.calls, [])


if __name__ == "__main__":
    unittest.main()
