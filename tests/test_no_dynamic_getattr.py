"""Tests for ``anti-slop/no-dynamic-getattr``."""

from anti_slop.rules.no_dynamic_getattr import NoDynamicGetattrRule

from tests.harness import RuleTester


def test_no_dynamic_getattr() -> None:
    RuleTester(NoDynamicGetattrRule()).run(
        "anti-slop/no-dynamic-getattr",
        valid=[
            'x = getattr(obj, "literal")',
            'x = getattr(obj, "field", default)',
            'x = hasattr(obj, "literal")',
            'setattr(obj, "literal", value)',
            'delattr(obj, "literal")',
            # Locally shadowed.
            "def getattr(o, n):\n    return n\n"
            "x = getattr(o, dynamic)",
            # Imported from elsewhere.
            "from tools import getattr\n"
            "x = getattr(o, dynamic)",
            # Plain attribute access.
            "x = obj.lit_attr",
            # Dispatch belongs to no-dynamic-dispatch.
            'x = getattr(obj, "a")()',
        ],
        invalid=[
            {"code": "x = getattr(obj, field)", "count": 1},
            {"code": "x = getattr(obj, name, None)", "count": 1},
            {"code": 'x = getattr(obj, f"{name}")', "count": 1},
            {"code": "for key in keys:\n    x = getattr(obj, key)", "count": 1},
            {
                "code": "x = getattr(obj, field)\ny = getattr(other, field)",
                "count": 2,
            },
            # The whole dynamic attribute family is covered.
            {"code": "x = hasattr(obj, field)", "count": 1},
            {"code": "setattr(obj, field, value)", "count": 1},
            {"code": "delattr(obj, field)", "count": 1},
            {
                "code": (
                    "x = getattr(obj, field)\n"
                    "y = hasattr(obj, field)\n"
                    "setattr(obj, field, value)\n"
                    "delattr(obj, field)"
                ),
                "count": 4,
            },
        ],
    )
