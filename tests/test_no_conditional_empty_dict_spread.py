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
        ],
    )
