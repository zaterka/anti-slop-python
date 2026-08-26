"""``no-fstring-logging``: ban f-strings as logging message arguments.

Python-specific rule (no JS/TS counterpart). ``logger.info(f"job {job_id}
failed")`` builds the string eagerly, even when the log level would discard
the record — wasted work on a hot path, and the classic tell of code written
without reading the logging documentation. Logging methods take a format
string plus arguments so formatting stays lazy:
``logger.info("job %s failed", job_id)``.

The receiver must look like a logger. ``.error`` / ``.warning`` / ``.info``
are common method names on things that are not loggers at all —
``parser.error(f"bad value: {value}")`` is argparse, and formatting it eagerly
is correct — so the rule requires the receiver's trailing name to read as a
logger (``logger``, ``log``, ``_logger``, ``logging``, ``self.logger``, ...).
Projects with a differently named logger can extend the list::

    [tool.anti-slop.rules."anti-slop/no-fstring-logging"]
    receivers = ["audit", "telemetry"]
"""

from __future__ import annotations

import ast

from anti_slop.core import FileContext, Rule

__all__ = ["NoFstringLoggingRule"]

# The stdlib logging levels (and ``exception``, which logs plus a traceback).
_LOG_METHODS = frozenset(
    {"debug", "info", "warning", "warn", "error", "critical", "fatal", "exception"}
)

# Receiver names that identify a logger. Matched against the *last* segment of
# the receiver, so ``self.logger``, ``app.log``, and a bare ``logger`` all hit.
_LOGGER_RECEIVERS = frozenset({"logger", "log", "logging", "_logger", "_log", "LOGGER", "LOG"})


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
        receivers = _LOGGER_RECEIVERS | {
            str(name) for name in ctx.options.get("receivers", ()) or ()
        }
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
            if not self._is_logger(func.value, receivers):
                continue
            yield self.report(ctx, node, "fstringMessage")

    @staticmethod
    def _is_logger(receiver: ast.expr, receivers: frozenset[str] | set[str]) -> bool:
        """True when the call's receiver reads as a logger.

        Uses the trailing name only: ``logger``, ``self.logger``,
        ``app.state.log`` all qualify. A call receiver is unwrapped once so
        ``logging.getLogger(__name__).info(...)`` is still recognized.
        """
        if isinstance(receiver, ast.Call):
            receiver = receiver.func
            if isinstance(receiver, ast.Attribute) and receiver.attr == "getLogger":
                return True
            if isinstance(receiver, ast.Name) and receiver.id == "getLogger":
                return True
        if isinstance(receiver, ast.Attribute):
            return receiver.attr in receivers
        if isinstance(receiver, ast.Name):
            return receiver.id in receivers
        return False
