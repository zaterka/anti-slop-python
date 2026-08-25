"""``no-mutable-defaults``: ban mutable literal parameter defaults.

Python-specific rule (no JS/TS counterpart). ``def f(items=[])`` evaluates
the literal once, at function definition time, and every call that omits
``items`` shares that one list — the classic shared-state bug (state leaking
between calls, and the trap that makes dataclass fields require
``field(default_factory=...)``). Default to ``None`` and initialize inside
the function.

Covers ``list``/``dict``/``set`` displays and no-argument ``list()`` /
``dict()`` / ``set()`` calls in any parameter position, including
keyword-only parameters.
"""

from __future__ import annotations

import ast

from anti_slop.core import FileContext, Rule

from ..shared.type_utils import is_mutable_display

__all__ = ["NoMutableDefaultsRule"]


class NoMutableDefaultsRule(Rule):
    """Disallow mutable literal parameter defaults shared across calls."""

    name = "anti-slop/no-mutable-defaults"
    description = (
        "Disallow mutable literal parameter defaults (=[], {}, set()); they "
        "are shared across calls. Default to None and initialize inside the "
        "function."
    )
    messages = {
        "mutableDefault": (
            "Parameter `{parameter}` defaults to a mutable value that is "
            "created once and shared across every call. Default it to None "
            "and initialize inside the function."
        ),
    }

    def check(self, ctx: FileContext):
        for node in ast.walk(ctx.tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            args = node.args
            # ``args.defaults`` applies to the trailing positional parameters.
            positional = [*args.posonlyargs, *args.args]
            offset = len(positional) - len(args.defaults)
            for argument, default in zip(positional[offset:], args.defaults):
                if is_mutable_display(default):
                    yield self.report(
                        ctx, argument, "mutableDefault", parameter=argument.arg
                    )
            for argument, default in zip(args.kwonlyargs, args.kw_defaults or []):
                if default is not None and is_mutable_display(default):
                    yield self.report(
                        ctx, argument, "mutableDefault", parameter=argument.arg
                    )
