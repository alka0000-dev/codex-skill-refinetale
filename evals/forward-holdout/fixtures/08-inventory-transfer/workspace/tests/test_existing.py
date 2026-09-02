import unittest
from inventory import InsufficientStock, Inventory


class ExistingTests(unittest.TestCase):
    def test_adjust(self):
        inventory = Inventory({"book": 3})
        self.assertEqual(inventory.adjust("book", -1), 2)
        with self.assertRaises(InsufficientStock):
            inventory.adjust("book", -3)
        self.assertEqual(inventory.audit, [("book", -1, 2)])


if __name__ == "__main__":
    unittest.main()
