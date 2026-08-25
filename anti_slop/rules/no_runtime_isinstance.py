"""``no-runtime-isinstance``: ban ad hoc ``isinstance`` narrowing.

Port of ``anti-slop/no-runtime-typeof``. An ``isinstance`` check deep in the
logic narrows a representation without establishing its contract; external
values should be decoded into meaningful types at their I/O boundary.

Python adaptations (``typeof`` in JS is a rare, strong smell, while
``isinstance`` is everyday Python, so the carve-outs are wider):

* **Exception narrowing is exempt.** ``except ... as exc`` already establishes
  the failure contract, so ``isinstance(exc, SpecificError)`` — narrowing the
  caught exception itself — is the language's designed mechanism there, not
  ad hoc value narrowing. An ``isinstance`` on a *different* variable inside
  the handler is still reported.
* With ``allow_in_type_guards`` enabled, ``isinstance`` is additionally
  permitted inside functions whose return contract is ``TypeGuard[...]`` /
  ``TypeIs[...]`` — the explicit, named form of the same check.
"""

from __future__ import annotations

import ast

from anti_slop.core import FileContext, Rule

from ..shared.parents import ancestors, build_parent_map, enclosing_function
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
        parents = build_parent_map(tree)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Name) and func.id == "isinstance"):
                continue
            if self._narrows_caught_exception(parents, node):
                continue
            if allow_in_type_guards and self._inside_type_guard(
                parents, node, imports, assigned
            ):
                continue
            yield self.report(ctx, node, "runtimeIsinstance")

    @staticmethod
    def _narrows_caught_exception(
        parents: dict[ast.AST, ast.AST], call: ast.AST
    ) -> bool:
        """True when the check narrows the exception caught by the nearest
        ``except`` clause (``except ... as exc: isinstance(exc, ...)``).

        The ``except`` already establishes the failure contract, and
        narrowing the caught exception's type is the language's designed
        mechanism there. An ``isinstance`` on a *different* variable inside
        the handler is still ad hoc value narrowing and is not exempt.
        """
        handler = next(
            (
                ancestor
                for ancestor in ancestors(parents, call)
                if isinstance(ancestor, ast.ExceptHandler)
            ),
            None,
        )
        if handler is None or handler.name is None:
            return False
        if len(call.args) < 1:
            return False
        first = call.args[0]
        return isinstance(first, ast.Name) and first.id == handler.name

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
