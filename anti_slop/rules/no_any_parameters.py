"""``no-any-parameters``: ban explicit ``Any`` on function inputs.

Port of ``anti-slop/no-unknown-parameters``. Function inputs must use a named
domain type; ``Any`` inputs mean the function accepts unparsed data. (The JS
rule's ``cause`` exemption is not ported: Python exception chaining is
``raise X from e``, not a ``cause`` parameter, so there is no convention to
honor — an ``Any``-typed ``cause`` is just unparsed data in disguise.)
"""

from __future__ import annotations

import ast

from anti_slop.core import FileContext, Rule

from ..shared.parents import build_parent_map, enclosing_type_params
from ..shared.type_utils import (
    BUILTIN_ANY_NAMES,
    assigned_names,
    dotted_name,
    import_map,
    is_typing_symbol,
)

__all__ = ["NoAnyParametersRule"]


class NoAnyParametersRule(Rule):
    """Disallow explicit ``Any`` function parameters."""

    name = "anti-slop/no-any-parameters"
    description = (
        "Disallow explicitly Any function parameters; decode unknown input "
        "at its I/O boundary instead."
    )
    messages = {
        "unknownParameter": (
            "Parameter `{parameter}` leaves input unparsed. Accept a named "
            "domain type; run the expected parser at the I/O boundary before "
            "calling this function."
        ),
    }

    def check(self, ctx: FileContext):
        tree = ctx.tree
        imports = import_map(tree)
        assigned = assigned_names(tree)
        parents = build_parent_map(tree)

        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            type_params = frozenset(enclosing_type_params(parents, node))
            for argument in self._parameters(node):
                if argument.annotation is None:
                    continue
                if self._is_direct_any(argument.annotation, imports, assigned, type_params):
                    yield self.report(
                        ctx, argument.annotation, "unknownParameter", parameter=argument.arg
                    )

    @staticmethod
    def _is_direct_any(
        annotation: ast.AST,
        imports: dict[str, str],
        assigned: set[str],
        type_params: frozenset[str],
    ) -> bool:
        """True when the annotation is *exactly* ``typing.Any``.

        Faithful to the JS rule, this is a direct check: local aliases are NOT
        followed here (their declarations are caught by no-any-aliases), and
        unions/containers/``Optional`` do not count.
        """
        name = dotted_name(annotation)
        if name is None or name not in BUILTIN_ANY_NAMES:
            return False
        if name in type_params:
            return False
        if name == name.split(".")[0] and name in assigned:
            # A module-level ``class Any`` / ``Any = ...`` shadows the symbol.
            return False
        return is_typing_symbol(name, imports)

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
