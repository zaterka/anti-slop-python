"""``require-safety-comment-for-cast``: require a ``SAFETY:`` comment per cast.

Port of ``anti-slop/require-safety-comment-for-type-assertion``. A
``typing.cast`` asserts an invariant the type checker cannot verify; the
invariant must be stated in a ``SAFETY:`` comment immediately before the
statement (or trailing on the cast's own line).
"""

from __future__ import annotations

import ast
import io
import re
import tokenize

from anti_slop.core import FileContext, Rule

from ..shared.parents import build_parent_map, enclosing_statement
from ..shared.type_utils import assigned_names, import_map, is_typing_cast

__all__ = ["RequireSafetyCommentForCastRule", "SAFETY_RE"]

SAFETY_RE = re.compile(r"\bSAFETY\s*:")


class RequireSafetyCommentForCastRule(Rule):
    """Require a nearby ``SAFETY:`` comment for every ``typing.cast`` call."""

    name = "anti-slop/require-safety-comment-for-cast"
    description = "Require a nearby `SAFETY:` comment for every typing.cast call."
    messages = {
        "missingSafetyComment": (
            "This type cast has no `SAFETY:` justification. State the checked "
            "invariant immediately before the cast or its containing "
            "statement."
        ),
    }

    def check(self, ctx: FileContext):
        tree = ctx.tree
        imports = import_map(tree)
        assigned = assigned_names(tree)
        comments = self._collect_comments(ctx.source)
        parents = build_parent_map(tree)

        for node in ast.walk(tree):
            if not is_typing_cast(node, imports, assigned):
                continue
            if self._has_safety_comment(node, comments, parents):
                continue
            yield self.report(ctx, node, "missingSafetyComment")

    @staticmethod
    def _collect_comments(source: str) -> list[tuple[int, str]]:
        """Comment tokens as ``(line, text)`` — comments are not in the AST."""
        try:
            tokens = tokenize.generate_tokens(io.StringIO(source).readline)
            return [
                (tok.start[0], tok.string) for tok in tokens if tok.type == tokenize.COMMENT
            ]
        except (tokenize.TokenError, IndentationError, SyntaxError, ValueError):
            return []

    @staticmethod
    def _has_safety_comment(
        call: ast.Call,
        comments: list[tuple[int, str]],
        parents: dict[ast.AST, ast.AST],
    ) -> bool:
        stmt = enclosing_statement(parents, call)
        if stmt is None:
            stmt_start, prev_end = call.lineno, 0
        else:
            stmt_start = stmt.lineno
            prev_end = 0
            container = parents.get(stmt)
            if container is not None:
                for _field, value in ast.iter_fields(container):
                    if isinstance(value, list) and stmt in value:
                        index = value.index(stmt)
                        if index > 0:
                            previous = value[index - 1]
                            prev_end = previous.end_lineno or previous.lineno
                        break
        for line, text in comments:
            if not SAFETY_RE.search(text):
                continue
            if prev_end < line <= stmt_start or line == call.lineno:
                return True
        return False
