"""Tests for ``anti-slop/no-conditional-empty-dict-spread``."""

from anti_slop.rules.no_conditional_empty_dict_spread import (
    NoConditionalEmptyDictSpreadRule,
)

from tests.harness import RuleTester


def test_no_conditional_empty_dict_spread() -> None:
    RuleTester(NoConditionalEmptyDictSpreadRule()).run(
        "anti-slop/no-conditional-empty-dict-spread",
        valid=[
            "options = {**defaults}",
            "options = {**d, **second}",
            # A conditional spread where neither branch is empty.
            "options = {**(a if c else b)}",
            "x = {**d, 'k': 1}",
            "def f(d) -> dict:\n    return {**d}",
            # and/or conditionals with no empty-dict branch.
            "options = {**(a and b)}",
            "options = {**(a or b)}",
            # An empty dict literal by itself is fine.
            "x = {}",
        ],
        invalid=[
            {
                "code": "options = {**(timeout if timeout is not None else {})}",
                "count": 1,
            },
            {
                "code": "options = {**({} if timeout is None else timeout_map)}",
                "count": 1,
            },
            {
                "code": (
                    "def f(d, extra) -> dict:\n"
                    "    return {**d, **(extra if extra else {})}"
                ),
                "count": 1,
            },
            {
                "code": "x = {**(a if c else {}), **(b if d else {})}",
                "count": 2,
            },
            {
                "code": "def f() -> dict:\n    return {**(opts if opts else {})}",
                "count": 1,
            },
            # The documented `cond and d or {}` form: the empty dict is the
            # falsy fallback that omits the keys.
            {
                "code": "options = {**(timeout and {'timeout': timeout} or {})}",
                "count": 1,
            },
            # `d or {}`: falsy fallback to an empty dict.
            {
                "code": "options = {**(extra or {})}",
                "count": 1,
            },
        ],
    )
