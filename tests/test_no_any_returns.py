"""Tests for ``anti-slop/no-any-returns``."""

from anti_slop.rules.no_any_returns import NoAnyReturnsRule

from tests.harness import RuleTester


def test_no_any_returns() -> None:
    RuleTester(NoAnyReturnsRule()).run(
        "anti-slop/no-any-returns",
        valid=[
            "def f() -> str:\n    return ''",
            "async def f() -> User:\n    pass",
            # Coroutine[Any, None, T]: only position 2 is the value position.
            "from typing import Any, Coroutine\n"
            "def f() -> Coroutine[Any, None, str]:\n    pass",
            "from typing import Awaitable\n"
            "def f() -> Awaitable[str]:\n    pass",
            "def f() -> None:\n    return None",
            "from typing import Any\n"
            "def f[T](x: T) -> T:\n    return x",
            "def f() -> str | int:\n    return 1",
            "def f() -> list[int]:\n    return []",
        ],
        invalid=[
            {
                "code": "from typing import Any\n"
                "def f() -> Any:\n    return None",
                "count": 1,
            },
            {
                "code": "from typing import Any\n"
                "async def f() -> Any:\n    return None",
                "count": 1,
            },
            {
                "code": "from typing import Any\n"
                "def f() -> Any | str:\n    pass",
                "count": 1,
            },
            {
                "code": "from typing import Any, Awaitable\n"
                "def f() -> Awaitable[Any]:\n    pass",
                "count": 1,
            },
            {
                "code": "from typing import Any, Coroutine\n"
                "def f() -> Coroutine[Any, None, Any]:\n    pass",
                "count": 1,
            },
            {
                "code": "from typing import Any, Generator\n"
                "def f() -> Generator[Any, str, None]:\n    pass",
                "count": 1,
            },
            {
                "code": "from typing import Any\n"
                "type Alias = Any\n"
                "def f() -> Alias:\n    pass",
                "count": 1,
            },
            {
                "code": (
                    "from typing import Any\n"
                    "class C:\n"
                    "    def m(self) -> Any:\n        pass"
                ),
                "count": 1,
            },
            {
                "code": (
                    "from typing import Any\n"
                    "def outer() -> None:\n"
                    "    def inner() -> Any:\n        pass\n"
                    "    inner()"
                ),
                "count": 1,
            },
        ],
    )
