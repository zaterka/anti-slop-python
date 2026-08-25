"""Tests for ``anti-slop/no-dynamic-dispatch``."""

from anti_slop.rules.no_dynamic_dispatch import NoDynamicDispatchRule

from tests.harness import RuleTester


def test_no_dynamic_dispatch() -> None:
    RuleTester(NoDynamicDispatchRule()).run(
        "anti-slop/no-dynamic-dispatch",
        valid=[
            'getattr(obj, "method")()',
            "obj.method(arg)",
            # Shadowed getattr.
            "def getattr(o, n):\n    return n\n"
            "getattr(o, name)()",
            "import operator\n"
            'operator.methodcaller("m")(obj)',
            # A read, not a dispatch (no-dynamic-getattr owns it).
            "x = getattr(obj, name)",
        ],
        invalid=[
            {"code": "result = getattr(obj, method_name)(arg)", "count": 1},
            {"code": "getattr(obj, name)()", "count": 1},
            {"code": "x = [getattr(o, n)() for o in objs]", "count": 1},
            {
                "code": (
                    "def f(o, n):\n"
                    "    return getattr(o, n)(1)\n"
                    "getattr(o, n)()"
                ),
                "count": 2,
            },
        ],
    )
