"""Tests for ``anti-slop/no-numbered-symbol-names``."""

from anti_slop.rules.no_numbered_symbol_names import NoNumberedSymbolNamesRule

from tests.harness import RuleTester


def test_no_numbered_symbol_names_is_opt_in() -> None:
    # Opinionated naming policy; must not run unless explicitly enabled.
    assert NoNumberedSymbolNamesRule.default_enabled is False


def test_no_numbered_symbol_names() -> None:
    RuleTester(NoNumberedSymbolNamesRule()).run(
        "anti-slop/no-numbered-symbol-names",
        valid=[
            # Uppercase version constants.
            "V2 = 2",
            "SCHEMA_V3 = 3",
            # Normal names.
            "user = 1",
            "def fetch_items(limit: int) -> list:\n    return []",
            # A string value is not a symbol name.
            'def f() -> str:\n    return "data2"',
        ],
        invalid=[
            {"code": "data2 = 1", "count": 1},
            {"code": "def f() -> None:\n    user1 = 1", "count": 1},
            {"code": "def f() -> None:\n    result_final = 1", "count": 1},
            {"code": "def f() -> None:\n    temp_buffer_tmp = 1", "count": 1},
            {
                "code": "def f(item2, items_tmp) -> None:\n    pass",
                "count": 2,
            },
            # The TypeVar's declared name, reported once (assignment target
            # and first argument share the name). All-uppercase names like
            # V2 are constants by PEP 8 and stay exempt.
            {
                "code": 'from typing import TypeVar\nt2 = TypeVar("t2")',
                "count": 1,
            },
        ],
    )
