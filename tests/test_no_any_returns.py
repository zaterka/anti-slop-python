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
            "def f() -> tuple[str, int]:\n    return ('a', 1)",
            "from typing import Callable\n"
            "def f() -> Callable[[int], str]:\n    return g",
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
            # Built-in generics carry value types too, not just typing wrappers.
            {
                "code": "from typing import Any\n"
                "def f() -> list[Any]:\n    return []",
                "count": 1,
            },
            {
                "code": "from typing import Any\n"
                "def f() -> set[Any]:\n    return set()",
                "count": 1,
            },
            {
                "code": "from typing import Any\n"
                "def f() -> tuple[Any, ...]:\n    return ()",
                "count": 1,
            },
            {
                "code": "from typing import Any\n"
                "def f() -> frozenset[Any]:\n    return frozenset()",
                "count": 1,
            },
            {
                "code": (
                    "from typing import Any, Callable\n"
                    "def f() -> Callable[[], Any]:\n    return g"
                ),
                "count": 1,
            },
            # Quoted forward references resolve like any annotation.
            {
                "code": "from typing import Any\n"
                "def f() -> 'Any':\n    return 1",
                "count": 1,
            },
        ],
    )
