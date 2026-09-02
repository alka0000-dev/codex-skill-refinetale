class InsufficientStock(Exception):
    pass


class Inventory:
    def __init__(self, stock=None):
        self.stock = dict(stock or {})
        self.audit = []

    def adjust(self, sku, delta):
        updated = self.stock.get(sku, 0) + delta
        if updated < 0:
            raise InsufficientStock(sku)
        self.stock[sku] = updated
        self.audit.append((sku, delta, updated))
        return updated
