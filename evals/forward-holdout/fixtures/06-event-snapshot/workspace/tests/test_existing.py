import unittest
from event_bus import EventBus


class ExistingTests(unittest.TestCase):
    def test_emit_in_registration_order(self):
        bus = EventBus()
        bus.on("ready", lambda value: "a" + value)
        bus.on("ready", lambda value: "b" + value)
        self.assertEqual(bus.emit("ready", "!"), ["a!", "b!"])
        self.assertEqual(bus.emit("other", "!"), [])


if __name__ == "__main__":
    unittest.main()
