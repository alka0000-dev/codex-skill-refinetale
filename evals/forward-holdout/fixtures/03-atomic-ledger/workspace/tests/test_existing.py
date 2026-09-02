import unittest
from ledger import Ledger, Overdraft


class ExistingTests(unittest.TestCase):
    def test_apply_and_reject_overdraft(self):
        ledger = Ledger({"cash": 5})
        self.assertEqual(ledger.apply("cash", -2), 3)
        with self.assertRaises(Overdraft):
            ledger.apply("cash", -4)
        self.assertEqual(ledger.balances["cash"], 3)
        self.assertEqual(ledger.audit, [("cash", -2, 3)])


if __name__ == "__main__":
    unittest.main()
