"""``no-eval-exec``: ban ``eval`` and ``exec``.

Python-specific rule (no JS/TS counterpart — in JS the same smell is
``Function``/indirect ``eval``, rarely hand-written). Dynamic code execution
defeats every static analysis that follows the value, opens injection
attacks when the string is even partly external, and is a hallmark of data
that should have been parsed into a typed domain object at its boundary.
Parse the input (``json``, ``ast.literal_eval``, a schema) instead of
executing it.
"""

from __future__ import annotations

import ast

from anti_slop.core import FileContext, Rule

from ..shared.type_utils import assigned_names, import_map

__all__ = ["NoEvalExecRule"]

_DYNAMIC_CODE_BUILTINS = ("eval", "exec")


class NoEvalExecRule(Rule):
    """Disallow ``eval``/``exec``; parse dynamic input instead of executing it."""

    name = "anti-slop/no-eval-exec"
    description = (
        "Disallow eval/exec; they execute dynamic code. Parse the input into "
        "a named domain type at its boundary instead."
    )
    messages = {
        "dynamicCode": (
            "`{builtin}` executes dynamic code and defeats static analysis; "
            "parse the input into a named domain type (json, ast.literal_eval, "
            "a schema) instead."
        ),
    }

    def check(self, ctx: FileContext):
        tree = ctx.tree
        imports = import_map(tree)
        assigned = assigned_names(tree)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (
                isinstance(func, ast.Name)
                and func.id in _DYNAMIC_CODE_BUILTINS
            ):
                continue
            if func.id in imports or func.id in assigned:
                continue  # the builtin is shadowed by a module-level definition
            yield self.report(ctx, node, "dynamicCode", builtin=func.id)
