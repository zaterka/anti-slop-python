"""Deliberately sloppy sample code.

Not a test module and not imported by one: this file exists so CI can point
the action at something with known findings and assert that it annotates them.
It is excluded from the self-lint in pyproject.toml for that reason.
"""

from typing import Any


def handle(payload: Any) -> Any:
    return payload


def load(items=[]):
    try:
        return items[0]
    except Exception:
        pass
