"""Tests for ``anti-slop/no-runtime-isinstance``."""

from anti_slop.rules.no_runtime_isinstance import NoRuntimeIsinstanceRule

from tests.harness import RuleTester


def test_no_runtime_isinstance() -> None:
    RuleTester(NoRuntimeIsinstanceRule()).run(
        "anti-slop/no-runtime-isinstance",
        valid=[
            "x = type(v) is str",
            "issubclass(A, B)",
            # Shadowed builtin.
            "isinstance = my_check\n"
            "isinstance(x, str)",
            "x = my_isinstance(v, User)",
        ],
        invalid=[
            {
                "code": "if isinstance(x, str):\n    pass",
                "count": 1,
            },
            {
                "code": "x = isinstance(value, (int, float))",
                "count": 1,
            },
            {
                "code": "def f(v) -> bool:\n    return isinstance(v, User)",
                "count": 1,
            },
            {
                "code": (
                    "def f(v) -> bool:\n"
                    "    return isinstance(v, User) or isinstance(v, str)"
                ),
                "count": 2,
            },
            {
                "code": "[i for i in x if isinstance(i, int)]",
                "count": 1,
            },
        ],
    )


def test_no_runtime_isinstance_allows_type_guards_when_enabled() -> None:
    code = (
        "from typing import TypeGuard\n"
        "def is_user(v) -> TypeGuard[User]:\n"
        "    return isinstance(v, User)"
    )
    # Default: flagged.
    RuleTester(NoRuntimeIsinstanceRule()).run(
        "anti-slop/no-runtime-isinstance (default)",
        valid=[],
        invalid=[{"code": code, "count": 1}],
    )
    # allow_in_type_guards: clean.
    rule = NoRuntimeIsinstanceWithGuards()
    RuleTester(rule).run(
        "anti-slop/no-runtime-isinstance (allow_in_type_guards)",
        valid=[code],
        invalid=[
            {
                # A non-guard function is still flagged.
                "code": (
                    "from typing import TypeGuard\n"
                    "def f(v) -> bool:\n"
                    "    return isinstance(v, User)"
                ),
                "count": 1,
            }
        ],
    )


class NoRuntimeIsinstanceWithGuards(NoRuntimeIsinstanceRule):
    """Test double: same rule with the option turned on."""

    default_options = {"allow_in_type_guards": True}
