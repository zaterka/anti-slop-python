"""``no-dynamic-getattr``: ban ``getattr`` with a non-literal name.

Port of ``anti-slop/no-reflect-get``. ``getattr(obj, dynamic_name)`` bypasses
typed attribute access and the evidence it provides; read attributes directly
(``obj.attr``) or parse dynamic input into a named domain type first.
``getattr(obj, name)()`` — dynamic *dispatch* — is reported by
``no-dynamic-dispatch`` instead, to avoid double reporting.
"""

from __future__ import annotations

import ast

from anti_slop.core import FileContext, Rule

from ..shared.parents import build_parent_map
from ..shared.type_utils import assigned_names, import_map

__all__ = ["NoDynamicGetattrRule"]


class NoDynamicGetattrRule(Rule):
    """Disallow dynamic ``getattr`` reads; use typed attribute access."""

    name = "anti-slop/no-dynamic-getattr"
    description = (
        "Disallow dynamic getattr reads; use typed attribute access or parse "
        "dynamic input into a named domain type."
    )
    messages = {
        "reflectGet": (
            "Replace `getattr` with typed attribute access. Parse dynamic "
            "input into a named domain type before reading it."
        ),
    }

    def check(self, ctx: FileContext):
        tree = ctx.tree
        imports = import_map(tree)
        assigned = assigned_names(tree)
        if "getattr" in imports or "getattr" in assigned:
            return  # the builtin is shadowed

        parents = build_parent_map(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or len(node.args) < 2:
                continue
            func = node.func
            if not (isinstance(func, ast.Name) and func.id == "getattr"):
                continue
            name_arg = node.args[1]
            if isinstance(name_arg, ast.Constant) and isinstance(name_arg.value, str):
                continue  # getattr(obj, "literal") is attribute access in disguise
            # getattr(obj, name)(...) is dynamic dispatch: the sibling rule
            # reports it.
            caller = parents.get(node)
            if caller is not None and isinstance(caller, ast.Call) and caller.func is node:
                continue
            yield self.report(ctx, node, "reflectGet")
