"""Inline suppression comments.

Opinionated rules need an escape hatch that is cheaper than switching the rule
off for the whole project. A suppression comment marks one line, or one file,
as a deliberate exception::

    value = eval(expression)  # anti-slop: ignore[no-eval-exec] sandboxed input
    print(banner)             # anti-slop: ignore

    # anti-slop: ignore-file[no-debug-prints]

Rule names may be bare (``no-eval-exec``) or fully qualified
(``anti-slop/no-eval-exec``). Omitting the bracket list suppresses every rule
on that line — blunt, and worth avoiding in favor of naming the rule.

A line suppression applies to a violation reported on the comment's own line,
or on the line directly below when the comment sits alone on its line. That
covers both idioms::

    # anti-slop: ignore[no-any-parameters]
    def handle(payload: Any) -> None: ...

    def handle(payload: Any) -> None: ...  # anti-slop: ignore[no-any-parameters]

``ignore-file`` may appear anywhere in the file and applies to the whole file.
"""

from __future__ import annotations

import io
import re
import tokenize
from dataclasses import dataclass, field

__all__ = ["Suppressions", "ALL_RULES_TOKEN", "parse_suppressions"]

# Sentinel stored in a rule set meaning "every rule".
ALL_RULES_TOKEN = "*"

_RULE_PREFIX = "anti-slop/"

_DIRECTIVE_RE = re.compile(
    r"""
    \#\s*anti-slop\s*:\s*        # the directive marker
    (?P<scope>ignore-file|ignore)  # line scope or whole-file scope
    (?:\s*\[(?P<rules>[^\]]*)\])?  # optional rule list
    """,
    re.VERBOSE | re.IGNORECASE,
)


def _normalize(rule: str) -> str:
    """Accept ``no-eval-exec`` and ``anti-slop/no-eval-exec`` alike."""
    rule = rule.strip()
    if rule.startswith(_RULE_PREFIX):
        return rule
    return _RULE_PREFIX + rule


def _parse_rule_list(raw: str | None) -> set[str]:
    if raw is None:
        return {ALL_RULES_TOKEN}
    names = {_normalize(part) for part in raw.split(",") if part.strip()}
    # ``ignore[]`` names nothing; treat the empty list as "every rule" rather
    # than as a suppression that silently does nothing.
    return names or {ALL_RULES_TOKEN}


@dataclass
class Suppressions:
    """The suppression directives found in one file."""

    file_rules: set[str] = field(default_factory=set)
    line_rules: dict[int, set[str]] = field(default_factory=dict)

    def suppresses(self, rule: str, line: int) -> bool:
        """Whether ``rule`` is suppressed at ``line``."""
        if ALL_RULES_TOKEN in self.file_rules or rule in self.file_rules:
            return True
        at_line = self.line_rules.get(line)
        if at_line is None:
            return False
        return ALL_RULES_TOKEN in at_line or rule in at_line

    def __bool__(self) -> bool:
        return bool(self.file_rules or self.line_rules)


def parse_suppressions(source: str) -> Suppressions:
    """Collect the suppression directives in ``source``.

    Comments are not in the AST, so this tokenizes. A file that will not
    tokenize suppresses nothing — the parse error is reported separately.
    """
    result = Suppressions()
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError, ValueError):
        return result

    lines = source.splitlines()
    for token in tokens:
        if token.type != tokenize.COMMENT:
            continue
        match = _DIRECTIVE_RE.search(token.string)
        if match is None:
            continue
        rules = _parse_rule_list(match.group("rules"))
        if match.group("scope").lower() == "ignore-file":
            result.file_rules |= rules
            continue

        line = token.start[0]
        result.line_rules.setdefault(line, set()).update(rules)
        # A comment alone on its line refers to the statement below it. The
        # directive may head a multi-line comment block explaining itself, so
        # look past any further comment lines to reach the code.
        if _is_own_line_comment(token):
            target = _next_code_line(lines, line)
            if target is not None:
                result.line_rules.setdefault(target, set()).update(rules)
    return result


def _is_own_line_comment(token: tokenize.TokenInfo) -> bool:
    """True when only indentation precedes the comment on its own line."""
    return not token.line[: token.start[1]].strip()


def _next_code_line(lines: list[str], after: int) -> int | None:
    """The first line after ``after`` (1-based) that is neither comment nor blank.

    Stops at a blank line: a directive separated from the code by whitespace
    is a detached remark, not a suppression for whatever happens to follow.
    """
    for number in range(after + 1, len(lines) + 1):
        text = lines[number - 1].strip()
        if not text:
            return None
        if not text.startswith("#"):
            return number
    return None
