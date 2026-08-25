"""Tests for ``anti-slop/no-widen-then-assert``."""

from anti_slop.rules.no_widen_then_assert import NoWidenThenAssertRule

from tests.harness import RuleTester


def test_no_widen_then_assert() -> None:
    RuleTester(NoWidenThenAssertRule()).run(
        "anti-slop/no-widen-then-assert",
        valid=[
            # Widened but never cast back.
            "from typing import Any\n"
            "source = {'id': 'first'}\n"
            "widened: Any = source",
            # A parameter is not a widened local.
            "from typing import Any, cast\n"
            "def f(raw: Any) -> dict:\n"
            "    return cast(dict, raw)",
            # Casting back to a broad type is not recreating evidence.
            "from typing import Any, cast\n"
            "source = {'a': 1}\n"
            "widened: Any = source\n"
            "parsed = cast(Any, widened)",
            # Casting a value that was never widened.
            "from typing import Any, cast\n"
            "x = cast(dict, other)",
            # A cast in another scope than the widening.
            "from typing import Any, cast\n"
            "source = {'a': 1}\n"
            "widened: Any = source\n"
            "def f() -> None:\n"
            "    parsed = cast(dict, source_global)",
            # The cast before the binding (source order).
            "from typing import Any, cast\n"
            "x = cast(dict, widened)\n"
            "widened: Any = source",
        ],
        invalid=[
            {
                "code": (
                    "from typing import Any, cast\n"
                    "source = {'id': 'second'}\n"
                    "widened: Any = source\n"
                    "parsed = cast(dict, widened)"
                ),
                "count": 1,
            },
            {
                "code": (
                    "from typing import Any, cast\n"
                    "source = {'id': 'second'}\n"
                    "widened: object = source\n"
                    "parsed = cast(dict, widened)"
                ),
                "count": 1,
            },
            {
                "code": (
                    "from typing import Any, cast\n"
                    "source = [1, 2]\n"
                    "widened: Any = source\n"
                    "x = cast(list, widened)"
                ),
                "count": 1,
            },
            {
                "code": (
                    "from typing import Any, cast\n"
                    "a = 1\n"
                    "wa: Any = a\n"
                    "b = 2\n"
                    "wb: Any = b\n"
                    "x = cast(int, wa)\n"
                    "y = cast(int, wb)"
                ),
                "count": 2,
            },
            {
                "code": (
                    "from typing import Any, cast\n"
                    "def f() -> None:\n"
                    "    source = {'id': 'second'}\n"
                    "    widened: Any = source\n"
                    "    parsed = cast(dict, widened)"
                ),
                "count": 1,
            },
            # A cast nested in control flow is reported exactly once.
            {
                "code": (
                    "from typing import Any, cast\n"
                    "source = {'id': 'second'}\n"
                    "widened: Any = source\n"
                    "if True:\n"
                    "    parsed = cast(dict, widened)"
                ),
                "count": 1,
            },
        ],
    )
