"""``no-dynamic-dispatch``: ban ``getattr(obj, name)(...)`` dynamic dispatch.

Port of ``anti-slop/no-reflect-apply``. Calling a method looked up by a
non-literal name bypasses typed function calls; model dynamic dispatch behind
a named interface instead. (Dynamic *reads* are reported by
``no-dynamic-getattr``; this rule owns the dispatch case.)
"""

from __future__ import annotations

import ast

from anti_slop.core import FileContext, Rule

from ..shared.type_utils import assigned_names, import_map

__all__ = ["NoDynamicDispatchRule"]


class NoDynamicDispatchRule(Rule):
    """Disallow dynamic ``getattr`` dispatch in favor of typed calls."""

    name = "anti-slop/no-dynamic-dispatch"
    description = (
        "Disallow dynamic getattr dispatch; call typed functions directly or "
        "model dynamic dispatch behind a named interface."
    )
    messages = {
        "reflectApply": (
            "Replace dynamic `getattr` dispatch with a typed function call. "
            "Model dynamic dispatch behind a named interface."
        ),
    }

    def check(self, ctx: FileContext):
        tree = ctx.tree
        imports = import_map(tree)
        assigned = assigned_names(tree)
        if "getattr" in imports or "getattr" in assigned:
            return  # the builtin is shadowed

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            callee = node.func
            if not isinstance(callee, ast.Call) or len(callee.args) < 2:
                continue
            func = callee.func
            if not (isinstance(func, ast.Name) and func.id == "getattr"):
                continue
            name_arg = callee.args[1]
            if isinstance(name_arg, ast.Constant) and isinstance(name_arg.value, str):
                continue  # getattr(obj, "method")() is a plain method call
            yield self.report(ctx, node, "reflectApply")
