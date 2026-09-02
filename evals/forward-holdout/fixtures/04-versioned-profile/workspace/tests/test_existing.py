import unittest
from profile_codec import Profile, decode


class ExistingTests(unittest.TestCase):
    def test_reads_v1_profile(self):
        self.assertEqual(decode('{"version": 1, "id": "u1"}'), Profile("u1"))


if __name__ == "__main__":
    unittest.main()
