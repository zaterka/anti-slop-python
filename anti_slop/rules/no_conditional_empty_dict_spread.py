"""``no-conditional-empty-dict-spread``: ban ``{**(cond and d or {})}``-style omission.

Port of ``anti-slop/no-conditional-empty-object-spread``. A conditional spread
whose branch is an empty dict hides key omission behind ``{}``; the omission
should be explicit in the code flow instead.
"""

from __future__ import annotations

import ast

from anti_slop.core import FileContext, Rule

__all__ = ["NoConditionalEmptyDictSpreadRule"]


class NoConditionalEmptyDictSpreadRule(Rule):
    """Disallow dict spreads that conditionally spread an empty dict."""

    name = "anti-slop/no-conditional-empty-dict-spread"
    description = (
        "Disallow dict spreads that conditionally spread an empty dict to "
        "omit keys."
    )
    messages = {
        "avoid": (
            "This conditional spread hides key omission behind an empty "
            "dict. Build the dict in separate statements and add the key "
            "only when present."
        ),
    }

    def check(self, ctx: FileContext):
        for node in ast.walk(ctx.tree):
            if not isinstance(node, ast.Dict):
                continue
            # In a dict display, ``**expr`` is recorded as a None key with the
            # spread expression as the value (no Starred node).
            for key, value in zip(node.keys, node.values):
                if key is not None:
                    continue
                if self._is_conditional_empty_spread(value):
                    yield self.report(ctx, value, "avoid")

    @staticmethod
    def _is_conditional_empty_spread(expression: ast.AST) -> bool:
        """True for ``cond and d or {}`` / ``d if cond else {}`` with an empty-dict branch."""
        if not isinstance(expression, ast.IfExp):
            return False
        return (
            NoConditionalEmptyDictSpreadRule._is_empty_dict(expression.body)
            or NoConditionalEmptyDictSpreadRule._is_empty_dict(expression.orelse)
        )

    @staticmethod
    def _is_empty_dict(node: ast.AST) -> bool:
        return isinstance(node, ast.Dict) and not node.keys and not node.values
