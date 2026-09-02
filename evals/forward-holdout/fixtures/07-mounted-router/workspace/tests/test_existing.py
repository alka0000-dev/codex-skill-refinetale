import unittest
from router import NotFound, Router


class ExistingTests(unittest.TestCase):
    def test_exact_route_and_not_found(self):
        router = Router()
        handler = object()
        router.add("/health", handler)
        self.assertIs(router.resolve("/health"), handler)
        with self.assertRaises(NotFound):
            router.resolve("/missing")


if __name__ == "__main__":
    unittest.main()
