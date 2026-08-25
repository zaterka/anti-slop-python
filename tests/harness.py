"""A minimal RuleTester, mirroring the oxlint RuleTester the JS project uses.

Each rule's test file looks like::

    from anti_slop.rules.no_object_parameters import NoObjectParametersRule
    from tests.harness import RuleTester

    def test_no_object_parameters() -> None:
        RuleTester(NoObjectParametersRule()).run(
            "anti-slop/no-object-parameters",
            valid=[...],
            invalid=[...],
        )

``valid`` entries are code strings that must produce zero violations.
``invalid`` entries are either code strings (at least one violation expected)
or dicts ``{"code": ..., "count": N}`` pinning the exact violation count.
"""

from __future__ import annotations

import ast

from anti_slop.core import FileContext, Rule


class RuleError(AssertionError):
    """Raised when a rule does not behave as the test case expects."""


def _render(violations: list) -> str:
    return "\n".join(f"  {v.format()}" for v in violations)


class RuleTester:
    """Run one rule's valid/invalid cases against the current interpreter's AST."""

    def __init__(self, rule: Rule):
        self.rule = rule

    def lint(self, code: str) -> list:
        tree = ast.parse(code)
        ctx = FileContext(
            path="<rule-test>",
            source=code,
            tree=tree,
            options=dict(self.rule.default_options),
        )
        return list(self.rule.check(ctx))

    def run(self, name: str, *, valid: list[str], invalid: list[str | dict]) -> None:
        for index, code in enumerate(valid):
            try:
                violations = self.lint(code)
            except Exception as exc:  # a crash on valid code is a rule bug
                raise RuleError(
                    f"{name} valid[{index}] raised {exc!r}:\n{code}"
                ) from exc
            if violations:
                raise RuleError(
                    f"{name} valid[{index}] unexpectedly produced violations:\n"
                    f"{code}\n{_render(violations)}"
                )

        for index, case in enumerate(invalid):
            if isinstance(case, str):
                code, expected_count = case, None
            else:
                code = case["code"]
                expected_count = case.get("count")
            try:
                violations = self.lint(code)
            except Exception as exc:
                raise RuleError(
                    f"{name} invalid[{index}] raised {exc!r}:\n{code}"
                ) from exc
            if not violations:
                raise RuleError(
                    f"{name} invalid[{index}] produced no violations:\n{code}"
                )
            if expected_count is not None and len(violations) != expected_count:
                raise RuleError(
                    f"{name} invalid[{index}] expected {expected_count} violation(s), "
                    f"got {len(violations)}:\n{code}\n{_render(violations)}"
                )
