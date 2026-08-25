"""Tests for ``anti-slop/no-chained-casts``."""

from anti_slop.rules.no_chained_casts import NoChainedCastsRule

from tests.harness import RuleTester


def test_no_chained_casts() -> None:
    RuleTester(NoChainedCastsRule()).run(
        "anti-slop/no-chained-casts",
        valid=[
            "from typing import cast\n"
            "x = cast(User, raw)",
            "import typing\n"
            "x = typing.cast(User, raw)",
            # A local function named cast shadows typing.cast.
            "def cast(t, v):\n    return v\n"
            "x = cast(User, raw)",
            # Two independent single casts are fine.
            "from typing import cast\n"
            "x = cast(User, raw)\n"
            "y = cast(User, other)",
        ],
        invalid=[
            {
                "code": (
                    "from typing import cast\n"
                    "x = cast(User, cast(object, raw))"
                ),
                "count": 1,
            },
            {
                "code": (
                    "from typing import cast\n"
                    "x = cast(User, cast(str, cast(object, raw)))"
                ),
                "count": 1,  # outermost only
            },
            {
                "code": (
                    "import typing\n"
                    "x = typing.cast(User, cast(str, raw))"
                ),
                "count": 1,
            },
            {
                "code": (
                    "from typing import cast\n"
                    "def f(raw) -> User:\n"
                    "    return cast(User, cast(object, raw))"
                ),
                "count": 1,
            },
        ],
    )
