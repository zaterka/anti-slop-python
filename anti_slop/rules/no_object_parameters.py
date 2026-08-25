"""``no-object-parameters``: ban the broad ``object`` type on function inputs.

Port of ``anti-slop/no-object-parameters``. Inputs must use an owner-provided
type and be parsed at their boundary, not the bottom of the type hierarchy.
"""

from __future__ import annotations

import ast

from anti_slop.core import FileContext, Rule

from ..shared.parents import build_parent_map, enclosing_type_params
from ..shared.type_utils import (
    annotation_is_object,
    build_type_aliases,
    dotted_name,
    import_map,
    union_members,
)

__all__ = ["NoObjectParametersRule"]


class NoObjectParametersRule(Rule):
    """Disallow ``object`` function parameters, including local aliases to it."""

    name = "anti-slop/no-object-parameters"
    description = (
        "Disallow object function parameters; inputs must use an owner-provided "
        "type and be parsed at their boundary."
    )
    messages = {
        "objectParameter": (
            "Parameter `{parameter}` uses the broad `object` type. Accept a "
            "named owner type; parse external input at its boundary before "
            "calling this function."
        ),
    }

    def check(self, ctx: FileContext):
        tree = ctx.tree
        aliases = build_type_aliases(tree)
        imports = import_map(tree)
        parents = build_parent_map(tree)

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for argument in self._parameters(node):
                if argument.annotation is None:
                    continue
                shadowed = frozenset(enclosing_type_params(parents, argument))
                if self._resolves_to_object(
                    argument.annotation, aliases, imports, shadowed
                ):
                    yield self.report(
                        ctx, argument.annotation, "objectParameter", parameter=argument.arg
                    )

    @staticmethod
    def _parameters(node: ast.FunctionDef):
        """All parameter nodes, including ``*args`` and ``**kwargs``."""
        args = node.args
        yield from args.posonlyargs
        yield from args.args
        if args.vararg is not None:
            yield args.vararg
        yield from args.kwonlyargs
        if args.kwarg is not None:
            yield args.kwarg

    @staticmethod
    def _resolves_to_object(
        annotation: ast.AST,
        aliases: dict[str, ast.AST],
        imports: dict[str, str],
        shadowed: frozenset[str],
    ) -> bool:
        """True when the annotation (or a union member) resolves to ``object``."""
        members = union_members(annotation)
        if members is not None:
            return any(
                NoObjectParametersRule._resolves_to_object(
                    member, aliases, imports, shadowed
                )
                for member in members
            )
        name = dotted_name(annotation)
        if name is not None and name in shadowed:
            return False
        return annotation_is_object(annotation, aliases, imports, shadowed)
