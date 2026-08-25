"""Tests for ``anti-slop/no-shape-in-symbol-names``."""

from anti_slop.rules.no_shape_in_symbol_names import NoShapeInSymbolNamesRule

from tests.harness import RuleTester


def test_no_shape_in_symbol_names_is_opt_in() -> None:
    # "shape" is TS naming vocabulary that collides with the numpy/pandas
    # ``.shape`` attribute; the rule must not run unless explicitly enabled.
    assert NoShapeInSymbolNamesRule.default_enabled is False


def test_no_shape_in_symbol_names() -> None:
    RuleTester(NoShapeInSymbolNamesRule()).run(
        "anti-slop/no-shape-in-symbol-names",
        valid=[
            "def format_name(name: str) -> str:\n    return name",
            "class User:\n    pass",
            # A string value is not a symbol name.
            'def f() -> str:\n    return "shape"',
            # A reference to a module-level name is not a declaration.
            "def f() -> int:\n    return shape",
            "def f(payload: dict[str, int]) -> None:\n    pass",
        ],
        invalid=[
            {
                "code": "def user_shape() -> None:\n    pass",
                "count": 1,
            },
            {
                "code": "class UserShape:\n    pass",
                "count": 1,
            },
            {
                "code": "def f(shape_id: int) -> None:\n    pass",
                "count": 1,
            },
            {
                "code": "from models import user_shape",
                "count": 1,
            },
            {
                "code": "user_shape = 1",
                "count": 1,
            },
            {
                "code": "def f(items) -> None:\n    for item_shape in items:\n        pass",
                "count": 1,
            },
            # Attribute assignments choose the attribute name.
            {
                "code": "class C:\n    def f(self) -> None:\n        self.user_shape = 1",
                "count": 1,
            },
            # Case-insensitive.
            {
                "code": "class USER_SHAPE:\n    pass",
                "count": 1,
            },
            {
                "code": (
                    "def f(shape: int) -> None:\n"
                    "    pass\n"
                    "class Shape:\n"
                    "    pass"
                ),
                "count": 2,
            },
            # The TypeVar's declared name, reported once.
            {
                "code": 'from typing import TypeVar\nShapeT = TypeVar("ShapeT")',
                "count": 1,
            },
        ],
    )
