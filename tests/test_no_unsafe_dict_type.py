"""Tests for ``anti-slop/no-unsafe-dict-type``."""

from anti_slop.rules.no_unsafe_dict_type import NoUnsafeDictTypeRule

from tests.harness import RuleTester


def test_no_unsafe_dict_type() -> None:
    RuleTester(NoUnsafeDictTypeRule()).run(
        "anti-slop/no-unsafe-dict-type",
        valid=[
            "def f(x: dict[str, int]) -> None:\n    pass",
            "class User:\n    pass\n"
            "def f(x: dict[str, User]) -> None:\n    pass",
            # Forward references are named types.
            'def f(x: dict[str, "User"]) -> None:\n    pass',
            # Type parameters are not escape hatches.
            "def f[V](x: dict[str, V]) -> None:\n    pass",
            # Non-dict containers are out of scope.
            "from typing import Any\n"
            "def f(x: list[Any]) -> None:\n    pass",
            # Dict literals are values, not type contracts.
            "def f() -> None:\n    d = {'a': 1}",
            # Value-position containers are not directly unsafe
            # (faithful to the JS rule, which does not special-case Promise).
            "from typing import Any, Awaitable\n"
            "def f(x: dict[str, Awaitable[Any]]) -> None:\n    pass",
            "type M = dict[str, int]",
            "class C(dict[str, int]):\n    pass",
        ],
        invalid=[
            {
                "code": "from typing import Any\n"
                "def f(x: dict[str, Any]) -> None:\n    pass",
                "count": 1,
            },
            {
                "code": "import typing\n"
                "def f(x: typing.Dict[str, Any]) -> None:\n    pass",
                "count": 1,
            },
            {
                "code": "from typing import Any\n"
                "def f() -> dict[str, Any]:\n    return {}",
                "count": 1,
            },
            {
                "code": "from typing import Any\n"
                "x: dict[str, Any]",
                "count": 1,
            },
            {
                "code": "from typing import Any\n"
                "type M = dict[str, Any]",
                "count": 1,
            },
            {
                "code": "from typing import Any\n"
                "def f(x: dict[str, Any | int]) -> None:\n    pass",
                "count": 1,
            },
            {
                "code": "def f(x: dict[str, object]) -> None:\n    pass",
                "count": 1,
            },
            {
                "code": "from typing import Any\n"
                "type Alias = Any\n"
                "def f(x: dict[str, Alias]) -> None:\n    pass",
                "count": 1,
            },
            # Outermost unsafe dictionary only.
            {
                "code": "from typing import Any\n"
                "def f(x: dict[str, dict[str, Any]]) -> None:\n    pass",
                "count": 1,
            },
            {
                "code": (
                    "from typing import Any\n"
                    "class C:\n"
                    "    metadata: dict[str, Any]"
                ),
                "count": 1,
            },
            {
                "code": (
                    "from typing import Any\n"
                    "def f(x: dict[str, Any]) -> None:\n    pass\n"
                    "def g(x: dict[str, Any]) -> None:\n    pass"
                ),
                "count": 2,
            },
        ],
    )
