"""``no-any-aliases``: ban named aliases that merely conceal ``Any``.

Port of ``anti-slop/no-unknown-type-aliases``. An alias whose resolved type is
``Any`` hides the escape hatch from its consumers; ``Any`` must stay explicit
at the parsing boundary.
"""

from __future__ import annotations

import ast

from anti_slop.core import FileContext, Rule

from ..shared.type_utils import (
    annotation_is_any,
    build_type_aliases,
    dotted_name,
    import_map,
    shadowed_sensitive_symbols,
)

__all__ = ["NoAnyAliasesRule", "iter_alias_declarations"]


def _is_type_alias_annotation(node: ast.AST) -> bool:
    return dotted_name(node) in {"TypeAlias", "typing.TypeAlias"}


def _looks_like_type(node: ast.AST) -> bool:
    """Heuristic: does this expression read as a type, not a value?"""
    return isinstance(node, (ast.Name, ast.Attribute, ast.Subscript, ast.BinOp, ast.Call))


def iter_alias_declarations(tree: ast.Module):
    """Yield ``(name, target_node, right_hand_node)`` for each alias declaration.

    Matches :func:`anti_slop.shared.type_utils.build_type_aliases` (PEP 695
    ``type`` statements, ``X: TypeAlias = ...``, and type-like ``X = ...``) but
    reports *every* declaration, so chained aliases are each checked.
    """
    for node in tree.body:
        body = [node]
        if isinstance(node, ast.ClassDef):
            body.extend(node.body)
        for statement in body:
            if isinstance(statement, ast.TypeAlias):
                name = dotted_name(statement.name)
                if name is not None and "." not in name:
                    yield (name, statement.name, statement.value)
            elif (
                isinstance(statement, ast.AnnAssign)
                and isinstance(statement.target, ast.Name)
                and statement.value is not None
                and _is_type_alias_annotation(statement.annotation)
            ):
                yield (statement.target.id, statement.target, statement.value)
            elif (
                isinstance(statement, ast.Assign)
                and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)
                and _looks_like_type(statement.value)
            ):
                yield (statement.targets[0].id, statement.targets[0], statement.value)


class NoAnyAliasesRule(Rule):
    """Disallow type aliases whose resolved type is ``Any``."""

    name = "anti-slop/no-any-aliases"
    description = (
        "Disallow type aliases whose resolved type is Any; Any must remain "
        "visible at an allowed boundary."
    )
    messages = {
        "unknownAlias": (
            "Type alias `{alias}` hides `Any`. Keep `Any` explicit at the "
            "parsing boundary or on an allowed `cause` field; otherwise use "
            "the parsed owner type."
        ),
    }

    def check(self, ctx: FileContext):
        tree = ctx.tree
        aliases = build_type_aliases(tree)
        imports = import_map(tree)
        shadowed = shadowed_sensitive_symbols(tree)

        for name, target, rhs in iter_alias_declarations(tree):
            # The alias being defined shadows itself during resolution, so a
            # recursive ``A = A`` cannot loop; it also means a self-reference
            # is not treated as typing.Any.
            if annotation_is_any(rhs, aliases, imports, shadowed | frozenset({name})):
                yield self.report(ctx, target, "unknownAlias", alias=name)
