"""``no-dynamic-getattr``: ban dynamic attribute access with a non-literal name.

Port of ``anti-slop/no-reflect-get``. ``getattr(obj, dynamic_name)`` bypasses
typed attribute access and the evidence it provides; read attributes directly
(``obj.attr``) or parse dynamic input into a named domain type first.

Python adaptation: the JS rule only saw ``Reflect.get``, but Python's dynamic
attribute family is four builtins, and all of them bypass typing the same way:
``getattr`` (read), ``hasattr`` (probe), ``setattr`` (write), and ``delattr``
(delete). All four with a non-literal name argument are reported here.
``getattr(obj, name)()`` — dynamic *dispatch* — is reported by
``no-dynamic-dispatch`` instead, to avoid double reporting.
"""

from __future__ import annotations

import ast

from anti_slop.core import FileContext, Rule

from ..shared.parents import build_parent_map
from ..shared.type_utils import assigned_names, import_map

__all__ = ["NoDynamicGetattrRule"]

# The dynamic attribute-access family (see the module docstring).
_DYNAMIC_ATTR_BUILTINS = ("getattr", "hasattr", "setattr", "delattr")


class NoDynamicGetattrRule(Rule):
    """Disallow dynamic attribute access (getattr/hasattr/setattr/delattr)
    with a non-literal name; use typed attribute access."""

    name = "anti-slop/no-dynamic-getattr"
    description = (
        "Disallow dynamic attribute access (getattr/hasattr/setattr/delattr) "
        "with a non-literal name; use typed attribute access or parse dynamic "
        "input into a named domain type."
    )
    messages = {
        "reflectGet": (
            "Replace dynamic `{builtin}` with typed attribute access. Parse "
            "dynamic input into a named domain type before using it."
        ),
    }

    def check(self, ctx: FileContext):
        tree = ctx.tree
        imports = import_map(tree)
        assigned = assigned_names(tree)

        parents = build_parent_map(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or len(node.args) < 2:
                continue
            func = node.func
            if not (
                isinstance(func, ast.Name) and func.id in _DYNAMIC_ATTR_BUILTINS
            ):
                continue
            if func.id in imports or func.id in assigned:
                continue  # the builtin is shadowed by a module-level definition
            name_arg = node.args[1]
            if isinstance(name_arg, ast.Constant) and isinstance(name_arg.value, str):
                continue  # getattr(obj, "literal") is attribute access in disguise
            # getattr(obj, name)(...) is dynamic dispatch: the sibling rule
            # reports it.
            if func.id == "getattr":
                caller = parents.get(node)
                if (
                    caller is not None
                    and isinstance(caller, ast.Call)
                    and caller.func is node
                ):
                    continue
            yield self.report(ctx, node, "reflectGet", builtin=func.id)
