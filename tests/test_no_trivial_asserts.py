"""Tests for ``anti-slop/no-trivial-asserts``."""

from anti_slop.rules.no_trivial_asserts import NoTrivialAssertsRule

from tests.harness import RuleTester


def test_no_trivial_asserts() -> None:
    RuleTester(NoTrivialAssertsRule()).run(
        "anti-slop/no-trivial-asserts",
        valid=[
            # Real assertions.
            "def f(x):\n    assert x == 1",
            "def f(x):\n    assert x is not None",
            "def f(x):\n    assert len(x) > 0",
            # unittest assertions with real values.
            "class T:\n"
            "    def test_a(self):\n"
            "        self.assertEqual(a, b)",
            "class T:\n"
            "    def test_a(self):\n"
            "        self.assertTrue(computed)",
            "class T:\n"
            "    def test_a(self):\n"
            "        self.assertIsNone(result)",
            # Unrelated assert-like calls.
            "self.assert_called_once()",
        ],
        invalid=[
            {"code": "assert True", "count": 1},
            {"code": "def f(x):\n    assert x is x", "count": 1},
            {"code": "def f(x):\n    assert x == x", "count": 1},
            # The contradictory twins: always false, so they always raise.
            {"code": "def f(x):\n    assert x is not x", "count": 1},
            {"code": "def f(x):\n    assert x != x", "count": 1},
            {
                "code": "class T:\n"
                "    def test_a(self):\n"
                "        self.assertEqual(v, v)",
                "count": 1,
            },
            {
                "code": "class T:\n"
                "    def test_a(self):\n"
                "        self.assertEqual(a.b, a.b)",
                "count": 1,
            },
            {
                "code": "class T:\n"
                "    def test_a(self):\n"
                "        self.assertTrue(True)",
                "count": 1,
            },
            {
                "code": "class T:\n"
                "    def test_a(self):\n"
                "        self.assertFalse(False)",
                "count": 1,
            },
            {
                "code": "class T:\n"
                "    def test_a(self):\n"
                "        self.assertIsNone(None)",
                "count": 1,
            },
            {
                "code": "class T:\n"
                "    def test_a(self):\n"
                "        self.assertTrue(True)\n"
                "        self.assertFalse(False)",
                "count": 2,
            },
        ],
    )


def test_no_trivial_asserts_truthy_tuple() -> None:
    RuleTester(NoTrivialAssertsRule()).run(
        "anti-slop/no-trivial-asserts (tuple)",
        valid=[
            # The correct spelling: message as the assert's second operand.
            'assert value == expected, "mismatch"',
            # A tuple *comparison* is a real check, not a truthy tuple.
            "assert (a, b) == (1, 2)",
        ],
        invalid=[
            # Parenthesized assert: the tuple is always truthy, so the check
            # never runs.
            {"code": 'assert (value == expected, "mismatch")', "count": 1},
            {"code": 'assert (result,)', "count": 1},
        ],
    )
