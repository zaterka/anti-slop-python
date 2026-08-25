"""Tests for ``anti-slop/no-any-aliases``."""

from anti_slop.rules.no_any_aliases import NoAnyAliasesRule

from tests.harness import RuleTester


def test_no_any_aliases() -> None:
    RuleTester(NoAnyAliasesRule()).run(
        "anti-slop/no-any-aliases",
        valid=[
            "class Owner:\n    pass",
            "def f(value: int) -> None:\n    pass",
            "value = 42",
            'value = "a string"',
            # A class named Alias is not a type alias declaration.
            "class Alias:\n    pass",
            # Shadowed Any: imported from elsewhere.
            "from foo import Any\n"
            "Alias = Any",
            # Shadowed Any: a local class.
            "class Any:\n    pass\n"
            "Alias = Any",
            # Concrete aliases are fine.
            "type Owner = int",
            "class User:\n    pass\n"
            "type Owner = User",
            "from typing import Optional\n"
            "type Name = Optional[str]",
            # A union containing Any is not a pure concealment of Any
            # (mirrors the reference rule, which flags exact concealment).
            "from typing import Any\n"
            "type Mixed = Any | str",
            # Annotation-only assignment is not an alias declaration.
            "from typing import Any\n"
            "value: Any",
        ],
        invalid=[
            {
                "code": "from typing import Any\n"
                "Alias = Any",
                "count": 1,
            },
            {
                "code": "from typing import Any\n"
                "type Alias = Any",
                "count": 1,
            },
            {
                "code": (
                    "from typing import Any, TypeAlias\n"
                    "Alias: TypeAlias = Any"
                ),
                "count": 1,
            },
            {
                "code": "import typing\n"
                "Alias = typing.Any",
                "count": 1,
            },
            # Chained aliases: every level that conceals Any is reported.
            {
                "code": "from typing import Any\n"
                "A = Any\n"
                "B = A",
                "count": 2,
            },
            {
                "code": (
                    "from typing import Any\n"
                    "A = Any\n"
                    "B = A\n"
                    "C = B"
                ),
                "count": 3,
            },
            {
                "code": (
                    "from typing import Any\n"
                    "class C:\n"
                    "    Inner = Any"
                ),
                "count": 1,
            },
        ],
    )
