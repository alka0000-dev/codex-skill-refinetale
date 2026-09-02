class InvoiceService:
    def __init__(self, publisher):
        self.publisher = publisher

    def render(self, invoice):
        if "id" not in invoice or "amount" not in invoice:
            raise ValueError("invalid invoice")
        return f"invoice={invoice['id']};amount={invoice['amount']}"

    def publish_one(self, invoice):
        body = self.render(invoice)
        return self.publisher.publish(invoice["id"], body)
