import unittest
from router import NotFound, Router


class RequirementTests(unittest.TestCase):
    def test_exact_route_wins_over_mount(self):
        router = Router()
        exact, mounted = object(), object()
        router.add("/api/users", exact)
        router.mount("/api", mounted)
        self.assertIs(router.resolve("/api/users"), exact)

    def test_longest_segment_mount_and_remainder(self):
        router = Router()
        api, users = object(), object()
        router.mount("/api/", api)
        router.mount("/api/users", users)
        self.assertEqual(router.resolve("/api"), (api, "/"))
        self.assertEqual(router.resolve("/api/users"), (users, "/"))
        self.assertEqual(router.resolve("/api/users/42"), (users, "/42"))

    def test_segment_boundary(self):
        router = Router()
        router.mount("/api", object())
        with self.assertRaises(NotFound):
            router.resolve("/apix")

    def test_root_mount_keeps_full_path_as_remainder(self):
        router = Router()
        root = object()
        router.mount("/", root)
        self.assertEqual(router.resolve("/"), (root, "/"))
        self.assertEqual(router.resolve("/anything"), (root, "/anything"))

    def test_invalid_values_do_not_register(self):
        router = Router()
        for prefix in (None, "", "api"):
            with self.subTest(prefix=prefix), self.assertRaises(ValueError):
                router.mount(prefix, object())
        self.assertEqual(getattr(router, "_mounts", {}), {})
        for path in (None, "", "api"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                router.resolve(path)


if __name__ == "__main__":
    unittest.main()
