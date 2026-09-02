import unittest
from event_bus import EventBus


class RequirementTests(unittest.TestCase):
    def test_off_removes_only_first_duplicate(self):
        bus = EventBus()
        handler = lambda value: value
        bus.on("x", handler)
        bus.on("x", handler)
        self.assertTrue(bus.off("x", handler))
        self.assertEqual(bus.emit("x", 3), [3])
        self.assertTrue(bus.off("x", handler))
        self.assertFalse(bus.off("x", handler))

    def test_changes_during_emit_apply_next_time(self):
        bus = EventBus()
        calls = []

        def first(value):
            calls.append("first")
            bus.off("x", second)
            bus.on("x", third)

        def second(value):
            calls.append("second")

        def third(value):
            calls.append("third")

        bus.on("x", first)
        bus.on("x", second)
        bus.emit("x", None)
        self.assertEqual(calls, ["first", "second"])
        calls.clear()
        bus.emit("x", None)
        self.assertEqual(calls, ["first", "third"])

    def test_exception_stops_later_handlers(self):
        bus = EventBus()
        calls = []
        bus.on("x", lambda value: (_ for _ in ()).throw(RuntimeError("boom")))
        bus.on("x", lambda value: calls.append("late"))
        with self.assertRaises(RuntimeError):
            bus.emit("x", None)
        self.assertEqual(calls, [])

    def test_unknown_off_does_not_create_event(self):
        bus = EventBus()
        self.assertFalse(bus.off("missing", lambda value: value))
        self.assertNotIn("missing", bus._handlers)


if __name__ == "__main__":
    unittest.main()
