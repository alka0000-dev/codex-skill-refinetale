import json
import unittest
from profile_codec import InvalidProfile, Profile, decode, encode


class RequirementTests(unittest.TestCase):
    def test_v2_round_trip_and_default_name(self):
        named = Profile("u1", "Ada")
        self.assertEqual(json.loads(encode(named)), {"version": 2, "user_id": "u1", "display_name": "Ada"})
        restored = decode(encode(named))
        self.assertEqual((restored.user_id, restored.display_name), ("u1", "Ada"))
        self.assertEqual(Profile("u2").display_name, "u2")

    def test_migrates_v1(self):
        profile = decode('{"version": 1, "id": "legacy"}')
        self.assertEqual((profile.user_id, profile.display_name), ("legacy", "legacy"))

    def test_rejects_malformed_profiles_with_domain_error(self):
        invalid = [
            "not-json", "[]", "{}", '{"version":3,"id":"x"}',
            '{"version":1,"id":""}', '{"version":1,"id":4}',
            '{"version":2,"user_id":"u"}',
            '{"version":2,"user_id":"","display_name":"n"}',
            '{"version":2,"user_id":"u","display_name":false}',
        ]
        for raw in invalid:
            with self.subTest(raw=raw), self.assertRaises(InvalidProfile):
                decode(raw)


if __name__ == "__main__":
    unittest.main()
