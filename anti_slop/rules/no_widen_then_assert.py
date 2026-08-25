"""``no-widen-then-assert``: ban widen-to-``Any``-then-``cast``-back flows.

Port of ``anti-slop/no-widen-then-assert``. A local binding that discards the
evidence of a known value into ``Any``/``object`` and is later cast back to a
narrower type recreates, by hand, the type the initial value already had.
Keep the precise type from initialization through use; parse boundary input
once.
"""

from __future__ import annotations

import ast

from anti_slop.core import FileContext, Rule

from ..shared.bindings import Binding, collect_bindings, iter_scope_nodes, scope_bodies
from ..shared.type_utils import (
    annotation_is_broad,
    assigned_names,
    build_type_aliases,
    dotted_name,
    import_map,
    is_known_evidence,
    is_typing_cast,
    shadowed_sensitive_symbols,
)

__all__ = ["NoWidenThenAssertRule"]


class NoWidenThenAssertRule(Rule):
    """Disallow widen-then-``cast``-back flows that recreate discarded evidence."""

    name = "anti-slop/no-widen-then-assert"
    description = (
        "Disallow local bindings that widen a known value to Any or object "
        "and are later cast back to a narrower type."
    )
    messages = {
        "widenThenAssert": (
            'Binding "{name}" discards type evidence and later recreates it '
            "with a cast. Keep the precise type from initialization through "
            "use; parse boundary input once."
        ),
    }

    def check(self, ctx: FileContext):
        tree = ctx.tree
        aliases = build_type_aliases(tree)
        imports = import_map(tree)
        shadowed = shadowed_sensitive_symbols(tree)
        assigned = assigned_names(tree)

        for owner, body in scope_bodies(tree):
            bindings = collect_bindings(body)
            type_params = (
                frozenset(tp.name for tp in getattr(owner, "type_params", []))
                if owner is not None
                else frozenset()
            )

            widened = {
                name: binding
                for name, binding in bindings.items()
                if self._is_widened(
                    binding, aliases, imports, shadowed, type_params, bindings
                )
            }
            if not widened:
                continue

            for node in iter_scope_nodes(body):
                if not is_typing_cast(node, imports, assigned):
                    continue
                value_arg = node.args[1]
                if not isinstance(value_arg, ast.Name):
                    continue
                binding = widened.get(value_arg.id)
                if binding is None:
                    continue
                if node.lineno <= binding.init.lineno:
                    continue  # the cast must come after the widening
                target = node.args[0]
                if annotation_is_broad(target, aliases, imports, shadowed) is not None:
                    continue  # cast(Any, ...) is not recreating evidence
                yield self.report(ctx, node, "widenThenAssert", name=value_arg.id)

    def _is_widened(
        self,
        binding: Binding,
        aliases: dict[str, ast.AST],
        imports: dict[str, str],
        shadowed: frozenset[str],
        type_params: frozenset[str],
        bindings: dict[str, Binding],
    ) -> bool:
        """True when the binding widens a known value into Any/object."""
        if binding.annotation is None or binding.init_value is None:
            return False
        name = dotted_name(binding.annotation)
        if name is not None and name in type_params:
            return False
        if annotation_is_broad(binding.annotation, aliases, imports, shadowed) is None:
            return False
        return self._has_evidence(
            binding.init_value, bindings, frozenset({binding.name})
        )

    @staticmethod
    def _has_evidence(expr, bindings, visited: frozenset[str] = frozenset()) -> bool:
        if is_known_evidence(expr):
            return True
        if isinstance(expr, ast.Name):
            binding = bindings.get(expr.id)
            if (
                binding is not None
                and binding.init_value is not None
                and len(binding.writes) == 1
                and expr.id not in visited
            ):
                return NoWidenThenAssertRule._has_evidence(
                    binding.init_value, bindings, visited | {expr.id}
                )
        return False
