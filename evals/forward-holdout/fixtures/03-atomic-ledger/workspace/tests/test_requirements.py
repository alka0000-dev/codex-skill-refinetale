import unittest
from ledger import Ledger, Overdraft


class RequirementTests(unittest.TestCase):
    def test_applies_in_order_and_returns_balances(self):
        ledger = Ledger({"a": 5})
        self.assertEqual(ledger.apply_batch((("a", -2), ("a", 4))), [3, 7])
        self.assertEqual(ledger.audit, [("a", -2, 3), ("a", 4, 7)])

    def test_intermediate_overdraft_is_atomic(self):
        ledger = Ledger({"a": 2})
        before_balances = dict(ledger.balances)
        before_audit = list(ledger.audit)
        with self.assertRaises(Overdraft):
            ledger.apply_batch([("a", -3), ("a", 5)])
        self.assertEqual(ledger.balances, before_balances)
        self.assertEqual(ledger.audit, before_audit)

    def test_invalid_entry_is_atomic(self):
        invalid_batches = [
            [("a", 1), ("", 2)],
            [("a", 1), ("b", True)],
            [("a", 1), ["b", 2]],
            [("a", 1), ("b", 2, 3)],
        ]
        for entries in invalid_batches:
            ledger = Ledger({"a": 1})
            with self.subTest(entries=entries), self.assertRaises(ValueError):
                ledger.apply_batch(entries)
            self.assertEqual(ledger.balances, {"a": 1})
            self.assertEqual(ledger.audit, [])


if __name__ == "__main__":
    unittest.main()
