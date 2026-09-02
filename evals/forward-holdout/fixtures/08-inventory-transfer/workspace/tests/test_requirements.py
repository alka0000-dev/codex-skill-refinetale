import unittest
from inventory import InsufficientStock, Inventory


class RequirementTests(unittest.TestCase):
    def test_success_uses_ordered_adjustments(self):
        source = Inventory({"book": 5})
        destination = Inventory({"book": 2})
        self.assertEqual(source.transfer_to(destination, "book", 3), (2, 5))
        self.assertEqual(source.audit, [("book", -3, 2)])
        self.assertEqual(destination.audit, [("book", 3, 5)])

    def test_insufficient_stock_is_atomic(self):
        source = Inventory({"book": 1})
        destination = Inventory({"book": 2})
        with self.assertRaises(InsufficientStock):
            source.transfer_to(destination, "book", 3)
        self.assertEqual((source.stock, source.audit), ({"book": 1}, []))
        self.assertEqual((destination.stock, destination.audit), ({"book": 2}, []))

    def test_same_inventory_is_noop(self):
        inventory = Inventory({"book": 4})
        self.assertEqual(inventory.transfer_to(inventory, "book", 2), 4)
        self.assertEqual((inventory.stock, inventory.audit), ({"book": 4}, []))

    def test_invalid_input_is_atomic(self):
        cases = [("", 1, Inventory()), ("book", 0, Inventory()), ("book", True, Inventory()), ("book", 1, object())]
        for sku, quantity, destination in cases:
            source = Inventory({"book": 3})
            with self.subTest(sku=sku, quantity=quantity), self.assertRaises(ValueError):
                source.transfer_to(destination, sku, quantity)
            self.assertEqual((source.stock, source.audit), ({"book": 3}, []))


if __name__ == "__main__":
    unittest.main()
