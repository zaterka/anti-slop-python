"""``no-chained-casts``: ban ``cast`` of ``cast``.

Port of ``anti-slop/no-chained-type-assertions``. Every ``typing.cast``
fabricates evidence the type checker cannot verify; chaining one inside
another compounds the fabrication. Exactly one violation is reported per
chain (on the outermost cast).
"""

from __future__ import annotations

import ast

from anti_slop.core import FileContext, Rule

from ..shared.parents import build_parent_map
from ..shared.type_utils import assigned_names, import_map, is_typing_cast

__all__ = ["NoChainedCastsRule"]


class NoChainedCastsRule(Rule):
    """Disallow chained ``typing.cast`` calls that fabricate evidence."""

    name = "anti-slop/no-chained-casts"
    description = (
        "Disallow chained typing.cast calls; each cast fabricates evidence "
        "the type checker cannot verify."
    )
    messages = {
        "chained": (
            "This cast chain discards type evidence. Keep the original "
            "precise type, or parse untrusted input at its boundary before "
            "narrowing it."
        ),
    }

    def check(self, ctx: FileContext):
        tree = ctx.tree
        imports = import_map(tree)
        assigned = assigned_names(tree)
        parents = build_parent_map(tree)

        for node in ast.walk(tree):
            if not is_typing_cast(node, imports, assigned):
                continue
            value_arg = node.args[1]
            if not is_typing_cast(value_arg, imports, assigned):
                continue
            # Report the outermost cast of the chain only: skip when this
            # cast is the value argument of another typing cast.
            outer = parents.get(node)
            if (
                outer is not None
                and isinstance(outer, ast.Call)
                and is_typing_cast(outer, imports, assigned)
                and len(outer.args) >= 2
                and outer.args[1] is node
            ):
                continue
            yield self.report(ctx, node, "chained")
