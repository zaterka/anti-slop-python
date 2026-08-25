"""``no-shape-in-symbol-names``: reject "shape" in declared symbol names.

Port of ``anti-slop/no-shape-in-symbol-names``, **opt-in in Python**
(``default_enabled = False``). "Shape" is TypeScript naming vocabulary
(``interface UserShape`` = the structure of an object); the JS rule polices a
team convention exported as a generic rule.

In Python the word collides with the ecosystem: ``ndarray.shape``,
``DataFrame.shape``, ``tensor.shape`` — so a variable named ``shape`` read
from one of them is natural, idiomatic code. Enabling the rule makes sense
only for codebases that have deliberately adopted "XShape" naming for domain
types; enable it in your configuration:

    [tool.anti-slop.rules."anti-slop/no-shape-in-symbol-names"]
    enabled = true

The reference rule flags every identifier *reference*; Python reads far more
identifiers than it declares, so the Python rule reports declarations only —
the single place a name is chosen.
"""

from __future__ import annotations

import ast

from anti_slop.core import FileContext, Rule

from ..shared.names import iter_symbol_names

FORBIDDEN_TERM = "shape"

__all__ = ["NoShapeInSymbolNamesRule", "FORBIDDEN_TERM"]


class NoShapeInSymbolNamesRule(Rule):
    """Disallow the case-insensitive substring "shape" in declared symbol names."""

    name = "anti-slop/no-shape-in-symbol-names"
    # Opt-in: "shape" is a TS naming convention that collides with the
    # numpy/pandas/scipy ``.shape`` attribute in Python codebases.
    default_enabled = False
    description = (
        'Disallow the case-insensitive substring "shape" in declared Python '
        "symbol names (functions, classes, parameters, variables, imports, "
        "and other bound names)."
    )
    messages = {
        "forbiddenSymbolName": (
            'Rename symbol "{name}" for its domain role; "shape" describes '
            "structure rather than ownership."
        ),
    }

    def check(self, ctx: FileContext):
        # Dedupe by (line, name): a TypeVar("T") declaration also names its
        # assignment target, and two distinct symbols cannot share a line and
        # name. This reports one violation per chosen name per line.
        seen: set[tuple[int, str]] = set()
        for node, name in iter_symbol_names(ctx.tree):
            if FORBIDDEN_TERM not in name.lower():
                continue
            key = (node.lineno, name)
            if key in seen:
                continue
            seen.add(key)
            yield self.report(ctx, node, "forbiddenSymbolName", name=name)
