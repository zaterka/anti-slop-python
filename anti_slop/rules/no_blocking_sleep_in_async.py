"""``no-blocking-sleep-in-async``: ban ``time.sleep`` inside async functions.

Python-specific rule (no JS/TS counterpart — the JS equivalent is
``setTimeout`` misuse, which is framework-shaped). ``time.sleep`` blocks the
thread, and in an async context that thread runs the event loop: every other
coroutine stalls for the whole sleep. The model-written version of an async
delay. Use ``await asyncio.sleep(...)``.

Only ``time.sleep`` (including aliased imports, ``import time as t``) is
flagged; ``asyncio.sleep`` is the fix, and a ``.sleep`` method on anything
else is out of scope.
"""

from __future__ import annotations

import ast

from anti_slop.core import FileContext, Rule

from ..shared.parents import build_parent_map, enclosing_function
from ..shared.type_utils import assigned_names, import_map

__all__ = ["NoBlockingSleepInAsyncRule"]


class NoBlockingSleepInAsyncRule(Rule):
    """Disallow ``time.sleep`` inside async functions; it blocks the loop."""

    name = "anti-slop/no-blocking-sleep-in-async"
    description = (
        "Disallow time.sleep inside async functions; it blocks the event "
        "loop. Use await asyncio.sleep() instead."
    )
    messages = {
        "blockingSleep": (
            "time.sleep blocks the event loop while this coroutine waits; "
            "use `await asyncio.sleep(...)` instead."
        ),
    }

    def check(self, ctx: FileContext):
        tree = ctx.tree
        imports = import_map(tree)
        assigned = assigned_names(tree)
        parents = build_parent_map(tree)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Attribute) and func.attr == "sleep"):
                continue
            base = func.value
            if not (
                isinstance(base, ast.Name)
                and self._is_time_module(base, imports, assigned)
            ):
                continue
            owner = enclosing_function(parents, node)
            if not self._is_async_function(owner):
                continue
            yield self.report(ctx, node, "blockingSleep")

    @staticmethod
    def _is_async_function(node: ast.AST | None) -> bool:
        # ``AsyncFunctionDef`` (a ``FunctionDef`` subclass) marks an
        # ``async def``; plain ``FunctionDef`` nodes are synchronous.
        return isinstance(node, ast.AsyncFunctionDef)

    @staticmethod
    def _is_time_module(
        base: ast.Name, imports: dict[str, str], assigned: set[str]
    ) -> bool:
        """True when ``base`` names the stdlib ``time`` module.

        ``time.sleep``; aliased as ``import time as t`` -> ``t.sleep``. An
        unimported bare ``time`` is assumed to be the stdlib module (the
        conventional assumption, same as for typing symbols); a module-level
        definition shadows it.
        """
        if base.id in assigned:
            return False
        return imports.get(base.id) == "time" or base.id == "time"
