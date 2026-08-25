"""``no-trivial-asserts``: ban assertions that can never fail.

Python-specific rule (no JS/TS counterpart). ``assert True``, ``assert x is
x``, ``self.assertEqual(a, a)`` — and their contradictory twins like
``assert x is not x`` — look like coverage but check nothing. Models under
pressure pad test suites with exactly these to make the file look tested.
Assert on the value the code computes.

Covers plain ``assert`` statements and the unittest family:
``assertTrue(True)``, ``assertFalse(False)``, ``assertIsNone(None)``,
``assertIsNotNone(None)``, and ``assertEqual(a, a)`` with structurally
identical operands.
"""

from __future__ import annotations

import ast

from anti_slop.core import FileContext, Rule

__all__ = ["NoTrivialAssertsRule"]

# unittest methods that are trivial when given an obvious literal.
_SELF_TEST_LITERAL_METHODS = {
    "assertTrue",
    "assertFalse",
    "assertIsNone",
    "assertIsNotNone",
}


def _same_expression(a: ast.expr, b: ast.expr) -> bool:
    """True when two expressions are structurally identical (``ast.dump``)."""
    return ast.dump(a) == ast.dump(b)


class NoTrivialAssertsRule(Rule):
    """Disallow assertions that are always true (or always false)."""

    name = "anti-slop/no-trivial-asserts"
    description = (
        "Disallow assertions that can never fail (assert True, assert x is "
        "x, assertEqual(a, a)); they look like coverage but check nothing."
    )
    messages = {
        "trivialAssert": (
            "This assertion can never fail; it checks nothing. Assert on the "
            "value the code computes."
        ),
    }

    def check(self, ctx: FileContext):
        for node in ast.walk(ctx.tree):
            if isinstance(node, ast.Assert) and self._trivial_test(node.test):
                yield self.report(ctx, node, "trivialAssert")
            elif isinstance(node, ast.Call) and isinstance(
                node.func, ast.Attribute
            ):
                if self._trivial_selftest(node):
                    yield self.report(ctx, node, "trivialAssert")

    @staticmethod
    def _trivial_test(test: ast.expr) -> bool:
        if isinstance(test, ast.Constant):
            return test.value is True
        if (
            isinstance(test, ast.Compare)
            and len(test.ops) == 1
            and len(test.comparators) == 1
            and isinstance(test.ops[0], (ast.Is, ast.IsNot, ast.Eq, ast.NotEq))
        ):
            return _same_expression(test.left, test.comparators[0])
        return False

    @staticmethod
    def _trivial_selftest(node: ast.Call) -> bool:
        func = node.func
        if func.attr in _SELF_TEST_LITERAL_METHODS:
            if len(node.args) != 1:
                return False
            arg = node.args[0]
            if not isinstance(arg, ast.Constant):
                return False
            value = arg.value
            if func.attr == "assertTrue":
                return value is True
            if func.attr == "assertFalse":
                return value is False
            # assertIsNone / assertIsNotNone: trivial with a None literal.
            return value is None
        if func.attr == "assertEqual" and len(node.args) == 2:
            return _same_expression(node.args[0], node.args[1])
        return False
