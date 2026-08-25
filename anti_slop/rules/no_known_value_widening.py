"""``no-known-value-widening``: ban broad annotations over concrete values.

Python adaptation of ``anti-slop/no-known-value-widening``. Python has no
``satisfies``, so the rule targets the clearest case: an explicit ``Any`` or
``object`` annotation placed over a value whose type is established by syntax
(a literal, a container display, or a stable local that resolves to one).
``None`` and function calls are deliberately not evidence — ``x: Any = None``
is an idiomatic placeholder and ``x: Any = parse(raw)`` is a boundary parser
doing its job.
"""

from __future__ import annotations

import ast

from anti_slop.core import FileContext, Rule

from ..shared.bindings import (
    Binding,
    collect_bindings,
    is_stable,
    iter_scope_nodes,
    scope_bodies,
)
from ..shared.type_utils import (
    annotation_is_broad,
    build_type_aliases,
    dotted_name,
    import_map,
    is_known_evidence,
    shadowed_sensitive_symbols,
)

__all__ = ["NoKnownValueWideningRule"]


class NoKnownValueWideningRule(Rule):
    """Disallow concrete values flowing into explicit ``Any``/``object`` annotations."""

    name = "anti-slop/no-known-value-widening"
    description = (
        "Disallow syntactically established values from flowing into explicit "
        "Any or object annotations that discard useful evidence."
    )
    messages = {
        "widening": (
            "The explicit {target} annotation on {subject} discards known "
            "type evidence. Drop the annotation to keep inference, or use a "
            "named owner contract."
        ),
    }

    def check(self, ctx: FileContext):
        tree = ctx.tree
        aliases = build_type_aliases(tree)
        imports = import_map(tree)
        shadowed = shadowed_sensitive_symbols(tree)

        for owner, body in scope_bodies(tree):
            bindings = collect_bindings(body)
            type_params = (
                frozenset(tp.name for tp in getattr(owner, "type_params", []))
                if owner is not None
                else frozenset()
            )

            for name, binding in bindings.items():
                if binding.annotation is None:
                    continue
                kind = self._broad_kind(
                    binding.annotation, aliases, imports, shadowed, type_params
                )
                if kind is None:
                    continue
                # Check 1: the annotated init holds a concrete value.
                if binding.init_value is not None and self._has_evidence(
                    binding.init_value, bindings, frozenset({name})
                ):
                    yield self.report(
                        ctx,
                        binding.init_value,
                        "widening",
                        target=kind,
                        subject=f"binding `{name}`",
                    )
                # Check 2: a later assignment puts a concrete value into the
                # broad binding (`x: Any` then `x = 42`, or `x: Any = 1` then `x = 2`).
                for write in binding.writes:
                    if write is binding.init or not isinstance(write, ast.Assign):
                        continue
                    if any(
                        isinstance(target, ast.Name) and target.id == name
                        for target in write.targets
                    ) and self._has_evidence(write.value, bindings, frozenset()):
                        yield self.report(
                            ctx,
                            write.value,
                            "widening",
                            target=kind,
                            subject=f"assignment to `{name}`",
                        )

            # Check 3: a concrete value returned through a broad contract.
            if (
                owner is not None
                and isinstance(owner, (ast.FunctionDef, ast.AsyncFunctionDef))
                and owner.returns is not None
            ):
                kind = self._broad_kind(
                    owner.returns, aliases, imports, shadowed, type_params
                )
                if kind is not None:
                    for node in iter_scope_nodes(body):
                        if (
                            isinstance(node, ast.Return)
                            and node.value is not None
                            and self._has_evidence(node.value, bindings, frozenset())
                        ):
                            yield self.report(
                                ctx,
                                node.value,
                                "widening",
                                target=kind,
                                subject=f"return value of `{owner.name}`",
                            )

    @staticmethod
    def _broad_kind(
        annotation: ast.AST,
        aliases: dict[str, ast.AST],
        imports: dict[str, str],
        shadowed: frozenset[str],
        type_params: frozenset[str],
    ) -> str | None:
        name = dotted_name(annotation)
        if name is not None and name in type_params:
            return None
        return annotation_is_broad(annotation, aliases, imports, shadowed)

    def _has_evidence(
        self,
        expr: ast.AST,
        bindings: dict[str, Binding],
        visited: frozenset[str] = frozenset(),
    ) -> bool:
        """A syntactically established value, or a stable local that resolves to one."""
        if is_known_evidence(expr):
            return True
        if isinstance(expr, ast.Name):
            binding = bindings.get(expr.id)
            if (
                binding is not None
                and binding.init_value is not None
                and is_stable(binding)
                and expr.id not in visited
            ):
                return self._has_evidence(
                    binding.init_value, bindings, visited | {expr.id}
                )
        return False
