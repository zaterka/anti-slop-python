"""``no-async-without-await``: ban async functions that never await.

Python-specific rule (no JS/TS counterpart). An ``async def`` that contains
no ``await`` buys a coroutine wrapper and an event-loop dependency for
nothing — it cannot yield to the loop, it just runs synchronously and hands
back a future. Make it a plain function.

An async *generator* contains no ``await`` by definition, so a body that
yields (making the function an async generator) is exempt.

Known false positive: a synchronous implementation of an async protocol
(``async def`` required by the interface, no ``await`` in the body) is
flagged. That shape is indistinguishable from pointless async without type
information; suppress the finding or the rule for protocol adapters.
"""

from __future__ import annotations

import ast

from anti_slop.core import FileContext, Rule

from ..shared.bindings import iter_scope_nodes

__all__ = ["NoAsyncWithoutAwaitRule"]


class NoAsyncWithoutAwaitRule(Rule):
    """Disallow async functions that contain no ``await`` (or ``yield``)."""

    name = "anti-slop/no-async-without-await"
    description = (
        "Disallow async functions that never await; they are synchronous "
        "with extra steps. Make them plain functions (async generators are "
        "exempt)."
    )
    messages = {
        "pointlessAsync": (
            "This async function never awaits; make it synchronous, or await "
            "the work it was written for."
        ),
    }

    def check(self, ctx: FileContext):
        for node in ast.walk(ctx.tree):
            # ``AsyncFunctionDef`` (a ``FunctionDef`` subclass) marks an
            # ``async def``; plain ``FunctionDef`` nodes are synchronous.
            if not isinstance(node, ast.AsyncFunctionDef):
                continue
            if self._has_async_work(node.body):
                continue
            yield self.report(ctx, node, "pointlessAsync")

    @staticmethod
    def _has_async_work(body: list[ast.stmt]) -> bool:
        """True when the scope awaits, or yields (making it an async generator).

        Walks expressions but stops at nested functions/classes, whose
        coroutines are their own.
        """
        for node in iter_scope_nodes(body):
            if isinstance(node, (ast.Await, ast.Yield, ast.YieldFrom)):
                return True
        return False
