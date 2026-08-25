"""``no-swallowed-exceptions``: ban handlers that swallow the exception.

Python-specific rule (no JS/TS counterpart). An ``except`` handler whose body
does nothing with the failure (``pass`` or ``continue``) converts every error
into silence; the program carries on believing nothing happened. The failure
was either expected (then say so) or it is a bug you will never find. Handle
the failure, log it with context, or re-raise.

Only *broad* handlers are flagged: bare ``except:``, ``except Exception``,
and ``except BaseException`` (including tuples that contain one). A specific
exception type that the code deliberately treats as "not an error" (``except
ZeroDivisionError`` around a division) is a documented decision, not a
blindfold.
"""

from __future__ import annotations

import ast

from anti_slop.core import FileContext, Rule

from ..shared.type_utils import dotted_name

__all__ = ["NoSwallowedExceptionsRule"]

_BROAD_EXCEPTION_NAMES = {
    "Exception",
    "BaseException",
    "builtins.Exception",
    "builtins.BaseException",
}


class NoSwallowedExceptionsRule(Rule):
    """Disallow broad except handlers whose body does nothing with the failure."""

    name = "anti-slop/no-swallowed-exceptions"
    description = (
        "Disallow broad except handlers that swallow the exception with pass "
        "or continue; handle the failure, log it with context, or re-raise."
    )
    messages = {
        "swallowed": (
            "This handler swallows the exception, so the program carries on "
            "believing nothing happened. Handle the failure, log it with "
            "context, or re-raise."
        ),
    }

    def check(self, ctx: FileContext):
        for node in ast.walk(ctx.tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            if not self._is_broad(node.type):
                continue
            if not self._does_nothing(node.body):
                continue
            yield self.report(ctx, node, "swallowed")

    @staticmethod
    def _is_broad(exc_type: ast.expr | None) -> bool:
        """True for bare except and for broad exception types (or tuples of them)."""
        if exc_type is None:
            return True
        if isinstance(exc_type, ast.Tuple):
            return any(
                NoSwallowedExceptionsRule._is_broad(elt) for elt in exc_type.elts
            )
        return dotted_name(exc_type) in _BROAD_EXCEPTION_NAMES

    @staticmethod
    def _does_nothing(body: list[ast.stmt]) -> bool:
        return bool(body) and all(
            isinstance(stmt, (ast.Pass, ast.Continue)) for stmt in body
        )
