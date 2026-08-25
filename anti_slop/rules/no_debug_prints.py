"""``no-debug-prints``: ban ``print`` calls outside the ``__main__`` guard.

Python-specific rule (no JS/TS counterpart). ``print`` in application code is
a debug artifact: it bypasses logging (no levels, no sinks, no timestamps)
and shows up in places stdout is not the interface. Output belongs in a
logger or the program's declared output channel.

Exemption: a print inside an ``if __name__ == "__main__":`` block is the
script's entry point, where stdout *is* the interface — those are allowed.
A function defined at module level (even one called from the guard) is
application code and is still flagged.
"""

from __future__ import annotations

import ast

from anti_slop.core import FileContext, Rule

from ..shared.parents import ancestors, build_parent_map
from ..shared.type_utils import assigned_names, import_map

__all__ = ["NoDebugPrintsRule"]


class NoDebugPrintsRule(Rule):
    """Disallow ``print`` calls outside an ``if __name__ == "__main__":`` block."""

    name = "anti-slop/no-debug-prints"
    description = (
        "Disallow print calls outside the `if __name__ == '__main__':` "
        "block; use a logger or the program's output channel."
    )
    messages = {
        "debugPrint": (
            "print is a debug artifact; use a logger or the program's output "
            "channel. Prints inside the `__main__` guard are exempt."
        ),
    }

    def check(self, ctx: FileContext):
        tree = ctx.tree
        imports = import_map(tree)
        assigned = assigned_names(tree)
        if "print" in imports or "print" in assigned:
            return  # the builtin is shadowed
        parents = build_parent_map(tree)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Name) and func.id == "print"):
                continue
            if self._inside_main_guard(parents, node):
                continue
            yield self.report(ctx, node, "debugPrint")

    @staticmethod
    def _inside_main_guard(
        parents: dict[ast.AST, ast.AST], node: ast.AST
    ) -> bool:
        """True when ``node`` is inside a module-level ``if __name__ == "__main__":``."""
        for ancestor in ancestors(parents, node):
            if isinstance(ancestor, ast.If) and NoDebugPrintsRule._is_main_guard(
                ancestor.test
            ):
                return True
            if isinstance(ancestor, ast.Module):
                return False
        return False

    @staticmethod
    def _is_main_guard(test: ast.expr) -> bool:
        """True for the ``__name__ == "__main__"`` comparison (either order)."""
        if not (
            isinstance(test, ast.Compare)
            and len(test.ops) == 1
            and isinstance(test.ops[0], ast.Eq)
            and len(test.comparators) == 1
        ):
            return False
        left, right = test.left, test.comparators[0]
        pairs = ((left, right), (right, left))
        for name_node, literal in pairs:
            if (
                isinstance(name_node, ast.Name)
                and name_node.id == "__name__"
                and isinstance(literal, ast.Constant)
                and literal.value == "__main__"
            ):
                return True
        return False
