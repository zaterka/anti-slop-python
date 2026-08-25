"""Tests for ``anti-slop/no-object-parameters``."""

from anti_slop.rules.no_object_parameters import NoObjectParametersRule

from tests.harness import RuleTester


def test_no_object_parameters() -> None:
    RuleTester(NoObjectParametersRule()).run(
        "anti-slop/no-object-parameters",
        valid=[
            # An alias to object with no consumer is not a parameter problem.
            "type Alias = object",
            "class Owner:\n    pass\n"
            "def f(value: Owner) -> None:\n    pass",
            # PEP 695 type parameters shadow module aliases and builtins.
            "def f[T](value: T) -> None:\n    pass",
            "def f[T: object](value: T) -> None:\n    pass",
            "type Alias = object\n"
            "def consume[Alias](value: Alias) -> None:\n    pass",
            # Nested broad types are out of scope (see no-unsafe-dict-type).
            "def f(value: list[object]) -> None:\n    pass",
            "def f(value: str | int) -> None:\n    pass",
            "def f(*args: int, **kwargs: dict[str, int]) -> None:\n    pass",
            # A broad type nested inside a container is not a direct object
            # parameter (no-unsafe-dict-type covers dict value types).
            "def f(**kwargs: dict[str, object]) -> None:\n    pass",
            "def f(value: int) -> None:\n    pass",
            # Protocol dunders: object is the documented parameter type
            # (official typing docs recommend __eq__(self, other: object)).
            "class User:\n"
            "    def __eq__(self, other: object) -> bool:\n"
            "        return False",
            "class User:\n"
            "    def __ne__(self, other: object) -> bool:\n"
            "        return True",
            "class User:\n"
            "    def __lt__(self, other: object) -> bool:\n"
            "        return False",
            "class User:\n"
            "    def __le__(self, other: object) -> bool:\n"
            "        return False",
            "class User:\n"
            "    def __gt__(self, other: object) -> bool:\n"
            "        return False",
            "class User:\n"
            "    def __ge__(self, other: object) -> bool:\n"
            "        return False",
            "class User:\n"
            "    def __contains__(self, item: object) -> bool:\n"
            "        return False",
        ],
        invalid=[
            {
                "code": "def f(value: object) -> None:\n    pass",
                "count": 1,
            },
            {
                "code": "type Alias = object\n"
                "def f(value: Alias) -> None:\n    pass",
                "count": 1,
            },
            {
                "code": "import typing\n"
                "def f(value: builtins.object) -> None:\n    pass",
                "count": 1,
            },
            # Unions are flagged when a member resolves to object.
            {
                "code": "def f(value: object | str) -> None:\n    pass",
                "count": 1,
            },
            {
                "code": "def f(value: str | object) -> None:\n    pass",
                "count": 1,
            },
            # *args and **kwargs count as parameters.
            {
                "code": "def f(*args: object) -> None:\n    pass",
                "count": 1,
            },
            # Defaults do not exempt the annotation.
            {
                "code": "def f(value: object = None) -> None:\n    pass",
                "count": 1,
            },
            # Async functions and methods are covered too.
            {
                "code": "async def f(value: object) -> None:\n    pass",
                "count": 1,
            },
            {
                "code": (
                    "class C:\n"
                    "    def m(self, value: object) -> None:\n"
                    "        pass"
                ),
                "count": 1,
            },
            {
                "code": (
                    "def f(a: object, b: object) -> None:\n"
                    "    pass"
                ),
                "count": 2,
            },
            # Non-protocol dunders are not exempt: a constructor taking
            # object is still a missing domain contract.
            {
                "code": (
                    "class User:\n"
                    "    def __init__(self, value: object) -> None:\n"
                    "        pass"
                ),
                "count": 1,
            },
            {
                "code": (
                    "class User:\n"
                    "    def __getitem__(self, key: object):\n"
                    "        pass"
                ),
                "count": 1,
            },
        ],
    )
