"""``no-fstring-logging``: ban f-strings as logging message arguments.

Python-specific rule (no JS/TS counterpart). ``logger.info(f"job {job_id}
failed")`` builds the string eagerly, even when the log level would discard
the record — wasted work on a hot path, and the classic tell of code written
without reading the logging documentation. Logging methods take a format
string plus arguments so formatting stays lazy:
``logger.info("job %s failed", job_id)``.
"""

from __future__ import annotations

import ast

from anti_slop.core import FileContext, Rule

__all__ = ["NoFstringLoggingRule"]

# The stdlib logging levels (and ``exception``, which logs plus a traceback).
_LOG_METHODS = frozenset(
    {"debug", "info", "warning", "error", "critical", "exception"}
)


class NoFstringLoggingRule(Rule):
    """Disallow f-strings as the message argument of logging calls."""

    name = "anti-slop/no-fstring-logging"
    description = (
        "Disallow f-strings as logging message arguments; pass the format "
        "string and its values separately so formatting stays lazy."
    )
    messages = {
        "fstringMessage": (
            "This f-string is built even when the log level discards the "
            "record. Pass the format string and its values separately: "
            'logger.info("job %s failed", job_id).'
        ),
    }

    def check(self, ctx: FileContext):
        for node in ast.walk(ctx.tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            func = node.func
            if not (
                isinstance(func, ast.Attribute)
                and func.attr in _LOG_METHODS
                and isinstance(node.args[0], ast.JoinedStr)
            ):
                continue
            yield self.report(ctx, node, "fstringMessage")
