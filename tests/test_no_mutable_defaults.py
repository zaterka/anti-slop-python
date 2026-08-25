"""Tests for ``anti-slop/no-mutable-defaults``."""

from anti_slop.rules.no_mutable_defaults import NoMutableDefaultsRule

from tests.harness import RuleTester


def test_no_mutable_defaults() -> None:
    RuleTester(NoMutableDefaultsRule()).run(
        "anti-slop/no-mutable-defaults",
        valid=[
            "def f(items=None):\n    return items or []",
            "def f(n: int = 3):\n    return n",
            "def f(flag: bool = False):\n    return flag",
            # Immutable literals are fine.
            "def f(items: tuple = ()): \n    return items",
            # A name default: mutability cannot be established from syntax.
            "def f(cache=DEFAULT_CACHE):\n    return cache",
            # *args/**kwargs cannot have defaults.
            "def f(*args, **kwargs):\n    return args, kwargs",
        ],
        invalid=[
            {"code": "def f(items=[]):\n    return items", "count": 1},
            {"code": "def f(d={}):\n    return d", "count": 1},
            {"code": "def f(s=set()):\n    return s", "count": 1},
            # No-argument constructors are equally shared.
            {"code": "def f(items=list()):\n    return items", "count": 1},
            {"code": "def f(d=dict()):\n    return d", "count": 1},
            # Trailing positional defaults and keyword-only defaults.
            {
                "code": "def f(a, b, c=[]):\n    return c",
                "count": 1,
            },
            {
                "code": "def f(*, cache={}):\n    return cache",
                "count": 1,
            },
            # Positional-only parameter with a mutable default.
            {
                "code": "def f(items=[], /):\n    return items",
                "count": 1,
            },
            # Async functions too.
            {
                "code": "async def f(items=[]):\n    return items",
                "count": 1,
            },
            {
                "code": "def f(a=[], b={}):\n    return a, b",
                "count": 2,
            },
        ],
    )
