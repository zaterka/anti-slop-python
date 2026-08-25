"""``no-unsafe-dict-type``: ban dictionary value contracts without a real type.

Port of ``anti-slop/no-unsafe-dictionary-type``. A ``dict[K, V]`` whose value
type is ``Any``, ``object``, or a union containing one of those gives callers
no concrete value contract. The outermost unsafe dictionary is reported once;
nested unsafe dictionaries inside it are suppressed (the inner declaration is
still caught at its own definition site when it is a type alias).
"""

from __future__ import annotations

import ast

from anti_slop.core import FileContext, Rule

from ..shared.parents import ancestors, build_parent_map
from ..shared.type_utils import (
    annotation_is_broad,
    build_type_aliases,
    dict_value_annotation,
    import_map,
    shadowed_sensitive_symbols,
    union_members,
)

__all__ = ["NoUnsafeDictTypeRule"]


class NoUnsafeDictTypeRule(Rule):
    """Disallow dict contracts whose value type is an unsafe escape hatch."""

    name = "anti-slop/no-unsafe-dict-type"
    description = (
        "Disallow dict type contracts whose value type is Any, object, or a "
        "union/alias containing one of those escape hatches."
    )
    messages = {
        "unsafeDictionary": (
            "This dictionary's {value} value type gives callers no concrete "
            "value contract. Use an owner/schema-derived value type; parse "
            "external payloads before insertion."
        ),
    }

    def check(self, ctx: FileContext):
        tree = ctx.tree
        aliases = build_type_aliases(tree)
        imports = import_map(tree)
        shadowed = shadowed_sensitive_symbols(tree)
        parents = build_parent_map(tree)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Subscript):
                continue
            kind = self._unsafe_value_kind(node, aliases, imports, shadowed)
            if kind is None:
                continue
            # Report the outermost unsafe dictionary only: if an ancestor is
            # itself an unsafe dict, the inner one is suppressed.
            if self._has_unsafe_dict_ancestor(node, parents, aliases, imports, shadowed):
                continue
            yield self.report(ctx, node, "unsafeDictionary", value=kind)

    @staticmethod
    def _unsafe_value_kind(
        node: ast.Subscript,
        aliases: dict[str, ast.AST],
        imports: dict[str, str],
        shadowed: frozenset[str],
    ) -> str | None:
        """Classify the value type of a ``dict[K, V]`` annotation, if unsafe.

        Quoted forward references are resolved like any annotation:
        ``dict[str, "User"]`` is a named type (safe) while
        ``dict[str, "Any"]`` is an escape hatch (unsafe).
        """
        value = dict_value_annotation(node)
        if value is None:
            return None
        broad = annotation_is_broad(value, aliases, imports, shadowed)
        if broad is not None:
            return broad
        members = union_members(value)
        if members is not None and any(
            annotation_is_broad(member, aliases, imports, shadowed) is not None
            for member in members
        ):
            return "union containing Any/object"
        if isinstance(value, ast.Subscript) and dict_value_annotation(value) is not None:
            if NoUnsafeDictTypeRule._unsafe_value_kind(
                value, aliases, imports, shadowed
            ) is not None:
                return "nested unsafe dictionary"
        return None

    @staticmethod
    def _has_unsafe_dict_ancestor(
        node: ast.AST,
        parents: dict[ast.AST, ast.AST],
        aliases: dict[str, ast.AST],
        imports: dict[str, str],
        shadowed: frozenset[str],
    ) -> bool:
        for ancestor in ancestors(parents, node):
            if isinstance(ancestor, ast.Subscript) and dict_value_annotation(
                ancestor
            ) is not None:
                if NoUnsafeDictTypeRule._unsafe_value_kind(
                    ancestor, aliases, imports, shadowed
                ) is not None:
                    return True
        return False
