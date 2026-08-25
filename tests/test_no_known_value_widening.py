"""Tests for ``anti-slop/no-known-value-widening``."""

from anti_slop.rules.no_known_value_widening import NoKnownValueWideningRule

from tests.harness import RuleTester


def test_no_known_value_widening() -> None:
    RuleTester(NoKnownValueWideningRule()).run(
        "anti-slop/no-known-value-widening",
        valid=[
            # None is the idiomatic optional placeholder, not evidence.
            "from typing import Any\n"
            "x: Any = None",
            # Calls are not evidence: boundary parsers are doing their job.
            "from typing import Any\n"
            "raw = request.json()\n"
            "x: Any = raw",
            "x: object = get_thing()",
            # Annotation without a value.
            "from typing import Any\n"
            "x: Any",
            # Dict value types belong to no-unsafe-dict-type.
            "from typing import Any\n"
            "x: dict[str, Any] = {'a': 1}",
            # Parameters are not bindings, so returning one is not widening.
            "from typing import Any\n"
            "def f(raw) -> Any:\n    return raw",
            # No annotation at all.
            "def f() -> None:\n    x = 42",
            # A reassigned local is not stable evidence.
            "from typing import Any\n"
            "b = 1\n"
            "b = 2\n"
            "x: Any = b",
            # A module global reference is not proven in this scope.
            "from typing import Any\n"
            "x: Any = some_global",
            # Type parameters are not escape hatches.
            "def f[T](x: T) -> T:\n    return x",
        ],
        invalid=[
            {
                "code": "from typing import Any\n"
                "x: Any = 42",
                "count": 1,
            },
            {
                "code": "x: object = {'a': 1}",
                "count": 1,
            },
            {
                "code": "x: object = [1, 2, 3]",
                "count": 1,
            },
            {
                "code": 'x: object = "literal"',
                "count": 1,
            },
            {
                "code": "from typing import Any\n"
                "def f() -> Any:\n    return {'id': 'first'}",
                "count": 1,
            },
            {
                "code": "def f() -> object:\n    return 42",
                "count": 1,
            },
            # A stable local that resolves to a concrete value.
            {
                "code": (
                    "from typing import Any\n"
                    "source = {'id': 'second'}\n"
                    "x: Any = source"
                ),
                "count": 1,
            },
            # Annotation first, concrete value later.
            {
                "code": "from typing import Any\n"
                "x: Any\n"
                "x = 42",
                "count": 1,
            },
            # Init plus a later concrete reassignment.
            {
                "code": "from typing import Any\n"
                "x: Any = 1\n"
                "x = 2",
                "count": 2,
            },
            {
                "code": (
                    "from typing import Any\n"
                    "x: Any = 1\n"
                    "y: object = 2"
                ),
                "count": 2,
            },
            {
                "code": (
                    "from typing import Any\n"
                    "def f() -> Any:\n    return 42\n"
                    "def g() -> Any:\n    return 5"
                ),
                "count": 2,
            },
            # Class-level attribute.
            {
                "code": (
                    "from typing import Any\n"
                    "class C:\n"
                    "    metadata: Any = 42"
                ),
                "count": 1,
            },
            # Nested inside control flow.
            {
                "code": (
                    "from typing import Any\n"
                    "def f(flag) -> None:\n"
                    "    if flag:\n"
                    "        x: Any = 42"
                ),
                "count": 1,
            },
            # A return nested in control flow is reported exactly once.
            {
                "code": (
                    "from typing import Any\n"
                    "def f(flag) -> Any:\n"
                    "    if flag:\n"
                    "        return 42"
                ),
                "count": 1,
            },
        ],
    )
