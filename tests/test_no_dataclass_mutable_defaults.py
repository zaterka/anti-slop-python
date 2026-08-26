"""Tests for ``anti-slop/no-dataclass-mutable-defaults``."""

from anti_slop.rules.no_dataclass_mutable_defaults import (
    NoDataclassMutableDefaultsRule,
)

from tests.harness import RuleTester


def test_no_dataclass_mutable_defaults() -> None:
    RuleTester(NoDataclassMutableDefaultsRule()).run(
        "anti-slop/no-dataclass-mutable-defaults",
        valid=[
            # field(default_factory=...) is the documented fix.
            "from dataclasses import dataclass, field\n"
            "@dataclass\n"
            "class C:\n"
            "    items: list = field(default_factory=list)",
            # Immutable defaults are fine.
            "from dataclasses import dataclass\n"
            "@dataclass\n"
            "class C:\n"
            "    n: int = 0\n"
            "    flag: bool = True",
            # Plain class (no dataclass decorator).
            "class C:\n"
            "    items: list = []",
            # A different decorator named dataclass-ish is out of scope.
            "def my_dataclass(cls):\n"
            "    return cls\n"
            "@my_dataclass\n"
            "class C:\n"
            "    items: list = []",
            # No default at all.
            "from dataclasses import dataclass\n"
            "@dataclass\n"
            "class C:\n"
            "    items: list",
            # ClassVar is a pseudo-field: dataclasses skips it, so a mutable
            # default raises nothing and is deliberate shared class state.
            "from dataclasses import dataclass\n"
            "from typing import ClassVar\n"
            "@dataclass\n"
            "class C:\n"
            "    registry: ClassVar[dict[str, int]] = {}\n"
            "    cache: ClassVar[list] = []\n"
            "    name: str = 'x'",
            "import typing\n"
            "from dataclasses import dataclass\n"
            "@dataclass\n"
            "class C:\n"
            "    registry: typing.ClassVar[dict] = {}",
        ],
        invalid=[
            {
                "code": (
                    "from dataclasses import dataclass\n"
                    "@dataclass\n"
                    "class C:\n"
                    "    items: list = []"
                ),
                "count": 1,
            },
            {
                "code": (
                    "from dataclasses import dataclass\n"
                    "@dataclass\n"
                    "class C:\n"
                    "    cache: dict = {}"
                ),
                "count": 1,
            },
            {
                "code": (
                    "from dataclasses import dataclass\n"
                    "@dataclass(frozen=True)\n"
                    "class C:\n"
                    "    tags: set = set()"
                ),
                "count": 1,
            },
            {
                "code": (
                    "from dataclasses import dataclass\n"
                    "@dataclass\n"
                    "class C:\n"
                    "    a: list = []\n"
                    "    b: dict = {}"
                ),
                "count": 2,
            },
        ],
    )
