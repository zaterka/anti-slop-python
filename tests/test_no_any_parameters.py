"""Tests for ``anti-slop/no-any-parameters``."""

from anti_slop.rules.no_any_parameters import NoAnyParametersRule

from tests.harness import RuleTester


def test_no_any_parameters() -> None:
    RuleTester(NoAnyParametersRule()).run(
        "anti-slop/no-any-parameters",
        valid=[
            "def f(x: str) -> None:\n    pass",
            # Not direct Any: unions, containers, and Optional are valid here
            # (alias declarations are caught by no-any-aliases).
            "from typing import Any\n"
            "def f(x: Any | str) -> None:\n    pass",
            "from typing import Any\n"
            "def f(x: list[Any]) -> None:\n    pass",
            "from typing import Any, Optional\n"
            "def f(x: Optional[Any]) -> None:\n    pass",
            # PEP 695 type parameters.
            "def f[T](x: T) -> None:\n    pass",
            "from typing import Any\n"
            "type Alias = Any\n"
            "def f(x: Alias) -> None:\n    pass",
            "def f(x: int) -> None:\n    pass",
        ],
        invalid=[
            {
                "code": "from typing import Any\n"
                "def f(x: Any) -> None:\n    pass",
                "count": 1,
            },
            {
                "code": "import typing\n"
                "def f(x: typing.Any) -> None:\n    pass",
                "count": 1,
            },
            {
                "code": "from typing import Any\n"
                "def f(a: Any, b: str) -> None:\n    pass",
                "count": 1,
            },
            {
                "code": "from typing import Any\n"
                "def f(*args: Any) -> None:\n    pass",
                "count": 1,
            },
            {
                "code": "from typing import Any\n"
                "def f(**kwargs: Any) -> None:\n    pass",
                "count": 1,
            },
            {
                "code": "from typing import Any\n"
                "def f(x: Any = None) -> None:\n    pass",
                "count": 1,
            },
            {
                "code": "from typing import Any\n"
                "async def f(x: Any) -> None:\n    pass",
                "count": 1,
            },
            {
                "code": (
                    "from typing import Any\n"
                    "class C:\n"
                    "    def m(self, x: Any) -> None:\n"
                    "        pass"
                ),
                "count": 1,
            },
            {
                "code": (
                    "from typing import Any\n"
                    "def f(x: Any, y: Any) -> None:\n    pass"
                ),
                "count": 2,
            },
            {
                "code": (
                    "from typing import Any\n"
                    "def f(cause: Any, x: Any) -> None:\n    pass"
                ),
                "count": 2,
            },
            # No `cause` exemption: Python exception chaining is `raise X from e`,
            # not a `cause` parameter, so an `Any` cause is just unparsed input.
            {
                "code": (
                    "from typing import Any\n"
                    "def f(cause: Any) -> None:\n    pass"
                ),
                "count": 1,
            },
        ],
    )
