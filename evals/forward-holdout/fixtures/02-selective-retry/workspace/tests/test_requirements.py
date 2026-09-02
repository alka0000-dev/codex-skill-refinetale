import unittest
from delivery import PermanentFailure, TemporaryFailure, deliver


class ScriptedSender:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def send(self, message):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class RequirementTests(unittest.TestCase):
    def test_retries_temporary_failure_then_stops_on_success(self):
        sender = ScriptedSender([TemporaryFailure(), "ok", "extra"])
        self.assertEqual(deliver(sender, "x", max_attempts=3), "ok")
        self.assertEqual(sender.calls, 2)

    def test_raises_after_attempt_budget(self):
        sender = ScriptedSender([TemporaryFailure(), TemporaryFailure()])
        with self.assertRaises(TemporaryFailure):
            deliver(sender, "x", max_attempts=2)
        self.assertEqual(sender.calls, 2)

    def test_does_not_retry_other_errors(self):
        for error in (PermanentFailure(), RuntimeError("boom")):
            sender = ScriptedSender([error, "unused"])
            with self.assertRaises(type(error)):
                deliver(sender, "x", max_attempts=3)
            self.assertEqual(sender.calls, 1)

    def test_validates_attempts_before_sending(self):
        for value in (0, -1, True, 1.5, "3"):
            sender = ScriptedSender(["unused"])
            with self.subTest(value=value), self.assertRaises(ValueError):
                deliver(sender, "x", max_attempts=value)
            self.assertEqual(sender.calls, 0)


if __name__ == "__main__":
    unittest.main()
