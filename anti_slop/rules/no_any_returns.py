"""``no-any-returns``: ban ``Any`` in function return contracts.

Port of ``anti-slop/no-unknown-returns``. A function that returns ``Any``
pushes the parsing responsibility onto its callers. ``Any`` must stay at the
I/O boundary, not in the contract.
"""

from __future__ import annotations

import ast

from anti_slop.core import FileContext, Rule

from ..shared.parents import build_parent_map, enclosing_type_params
from ..shared.type_utils import (
    annotation_is_any,
    build_type_aliases,
    import_map,
    shadowed_sensitive_symbols,
    union_members,
    wrapper_value_args,
)

__all__ = ["NoAnyReturnsRule"]


class NoAnyReturnsRule(Rule):
    """Disallow function contracts that return ``Any`` (directly, in a union,
    or in a value-carrying typing container)."""

    name = "anti-slop/no-any-returns"
    description = (
        "Disallow functions whose explicit return contract is Any, directly, "
        "through a union, or through a value-carrying typing container."
    )
    messages = {
        "unknownReturn": (
            "This function exposes `Any` to its caller. Parse the value at "
            "its boundary and return a named domain type."
        ),
    }

    def check(self, ctx: FileContext):
        tree = ctx.tree
        aliases = build_type_aliases(tree)
        imports = import_map(tree)
        shadowed = shadowed_sensitive_symbols(tree)
        parents = build_parent_map(tree)

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if node.returns is None:
                continue
            type_params = frozenset(enclosing_type_params(parents, node))
            if self._resolves_to_any(
                node.returns, aliases, imports, shadowed | type_params
            ):
                yield self.report(ctx, node.returns, "unknownReturn")

    @staticmethod
    def _resolves_to_any(
        annotation: ast.AST,
        aliases: dict[str, ast.AST],
        imports: dict[str, str],
        shadowed: frozenset[str],
    ) -> bool:
        """True when a return annotation resolves to ``Any``.

        Direct ``Any`` (through local aliases), any union member, or any
        value-position argument of a typing container
        (``Awaitable[Any]``, ``Coroutine[Any, None, Any]``, ...). Position 0/1
        of ``Coroutine`` is conventional ``Any`` boilerplate and is not a
        value position.
        """
        if annotation_is_any(annotation, aliases, imports, shadowed):
            return True
        value_args = wrapper_value_args(annotation)
        if value_args:
            return any(
                NoAnyReturnsRule._resolves_to_any(
                    arg, aliases, imports, shadowed
                )
                for arg in value_args
            )
        members = union_members(annotation)
        if members is not None:
            return any(
                NoAnyReturnsRule._resolves_to_any(
                    member, aliases, imports, shadowed
                )
                for member in members
            )
        return False
