"""``no-utcnow``: ban ``datetime.utcnow``.

Python-specific rule (no JS/TS counterpart). ``utcnow()`` was deprecated in
Python 3.12: it returns a *naive* timestamp labeled as UTC, which breaks
arithmetic with timezone-aware datetimes (``TypeError`` on subtraction) and
is the most common model mistake around time. Use
``datetime.now(timezone.utc)`` — aware, correct, and not deprecated.

Scope: the receiver must be the datetime class (``datetime.utcnow()`` or
``datetime.datetime.utcnow()``). A bare instance call (``dt.utcnow()``) is
indistinguishable from a same-named method on another object, so it is out
of scope: precision over recall.
"""

from __future__ import annotations

import ast

from anti_slop.core import FileContext, Rule

__all__ = ["NoUtcnowRule"]


class NoUtcnowRule(Rule):
    """Disallow ``utcnow()`` calls; they are deprecated and naive."""

    name = "anti-slop/no-utcnow"
    description = (
        "Disallow datetime.utcnow (deprecated since 3.12, returns a naive "
        "timestamp); use datetime.now(timezone.utc) instead."
    )
    messages = {
        "utcnow": (
            "datetime.utcnow is deprecated and returns a naive timestamp; "
            "use datetime.now(timezone.utc) instead."
        ),
    }

    def check(self, ctx: FileContext):
        for node in ast.walk(ctx.tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute) and func.attr == "utcnow"):
                continue
            if not self._is_datetime(func.value):
                continue
            yield self.report(ctx, node, "utcnow")

    @staticmethod
    def _is_datetime(base: ast.AST) -> bool:
        """True when ``base`` is the datetime class (either import form).

        ``datetime.utcnow()`` after ``from datetime import datetime`` (a
        ``Name``) and ``datetime.datetime.utcnow()`` after ``import datetime``
        (an ``Attribute`` with attr ``datetime``). See the module docstring
        for why bare instance calls are out of scope.
        """
        if isinstance(base, ast.Name):
            return base.id == "datetime"
        if isinstance(base, ast.Attribute):
            return base.attr == "datetime"
        return False
