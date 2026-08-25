"""``no-numbered-symbol-names``: reject numbered and throwaway-suffix names.

Python-specific rule, **opt-in** (``default_enabled = False``): it is
naming policy, not evidence, so it should be a deliberate choice.

LLM-generated code reaches for ``data2``, ``result_final``, and ``temp3``
when it has not chosen a domain name; human Python rarely ends an identifier
in a digit. Two signals are checked on *declared* symbols (declarations are
where a name is chosen, as in ``no-shape-in-symbol-names``):

* a trailing digit after a lowercase letter — ``user1``, ``data2``
  (uppercase constants such as ``V2`` are version identifiers and are
  exempt);
* a throwaway suffix — ``result_final``, ``temp_buffer`` ends in
  ``_final``/``_temp``/``_tmp``.
"""

from __future__ import annotations

import re

from anti_slop.core import FileContext, Rule

from ..shared.names import iter_symbol_names

__all__ = ["NoNumberedSymbolNamesRule"]

_TRAILING_DIGIT = re.compile(r"[a-z]\d+$")
_THROWAWAY_SUFFIX = re.compile(r"_(final|temp|tmp)$")


class NoNumberedSymbolNamesRule(Rule):
    """Disallow numbered/throwaway-suffix declared symbol names (opt-in)."""

    name = "anti-slop/no-numbered-symbol-names"
    # Opt-in: this is opinionated naming policy, not evidence.
    default_enabled = False
    description = (
        'Disallow identifiers ending in a digit ("data2") or a throwaway '
        'suffix ("result_final"); name symbols for their domain role.'
    )
    messages = {
        "numberedName": (
            'Identifier "{name}" looks like throwaway naming; rename it for '
            "its domain role."
        ),
    }

    def check(self, ctx: FileContext):
        # Dedupe by (line, name): e.g. TypeVar("T2") names both its assignment
        # target and its first argument.
        seen: set[tuple[int, str]] = set()
        for node, name in iter_symbol_names(ctx.tree):
            if not (
                _TRAILING_DIGIT.search(name) or _THROWAWAY_SUFFIX.search(name)
            ):
                continue
            key = (node.lineno, name)
            if key in seen:
                continue
            seen.add(key)
            yield self.report(ctx, node, "numberedName", name=name)
