"""``no-runtime-isinstance``: ban ad hoc ``isinstance`` narrowing.

Port of ``anti-slop/no-runtime-typeof``. An ``isinstance`` check deep in the
logic narrows a representation without establishing its contract; external
values should be decoded into meaningful types at their I/O boundary. With
``allow_in_type_guards`` enabled, ``isinstance`` is permitted inside functions
whose return contract is ``TypeGuard[...]`` / ``TypeIs[...]`` — the explicit,
named form of the same check.
"""

from __future__ import annotations

import ast

from anti_slop.core import FileContext, Rule

from ..shared.parents import build_parent_map, enclosing_function
from ..shared.type_utils import assigned_names, dotted_name, import_map, is_typing_symbol

__all__ = ["NoRuntimeIsinstanceRule"]

_TYPE_GUARD_NAMES = {
    "TypeGuard",
    "typing.TypeGuard",
    "TypeIs",
    "typing.TypeIs",
    "typing_extensions.TypeGuard",
    "typing_extensions.TypeIs",
}


class NoRuntimeIsinstanceRule(Rule):
    """Disallow runtime ``isinstance`` checks that narrow unparsed values."""

    name = "anti-slop/no-runtime-isinstance"
    description = (
        "Disallow runtime isinstance checks; external values must be decoded "
        "into meaningful types at their I/O boundary."
    )
    messages = {
        "runtimeIsinstance": (
            "An `isinstance` check narrows a representation without "
            "establishing its contract. Parse input at its I/O boundary, then "
            "branch on the domain value."
        ),
    }
    default_options = {"allow_in_type_guards": False}

    def check(self, ctx: FileContext):
        tree = ctx.tree
        imports = import_map(tree)
        assigned = assigned_names(tree)
        if "isinstance" in imports or "isinstance" in assigned:
            return  # the builtin is shadowed; not a runtime narrowing check

        allow_in_type_guards = bool(ctx.options.get("allow_in_type_guards", False))
        parents = build_parent_map(tree) if allow_in_type_guards else None

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Name) and func.id == "isinstance"):
                continue
            if (
                allow_in_type_guards
                and parents is not None
                and self._inside_type_guard(parents, node, imports, assigned)
            ):
                continue
            yield self.report(ctx, node, "runtimeIsinstance")

    @staticmethod
    def _inside_type_guard(
        parents: dict[ast.AST, ast.AST],
        call: ast.AST,
        imports: dict[str, str],
        assigned: set[str],
    ) -> bool:
        owner = enclosing_function(parents, call)
        if owner is None or owner.returns is None:
            return False
        # `TypeGuard[User]` is a Subscript; the guard name is its base.
        annotation = owner.returns
        if isinstance(annotation, ast.Subscript):
            annotation = annotation.value
        name = dotted_name(annotation)
        if name is None or name not in _TYPE_GUARD_NAMES:
            return False
        if name == name.split(".")[0] and name in assigned:
            return False  # a local class named TypeGuard/TypeIs shadows it
        return is_typing_symbol(name, imports)
