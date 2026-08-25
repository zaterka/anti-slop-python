"""Core data types and the :class:`Rule` base class.

Every anti-slop rule is a small, self-contained subclass of :class:`Rule` that
receives a :class:`FileContext` (the parsed file plus per-rule options) and yields
zero or more :class:`Violation` objects. Rules never talk to each other; the
:class:`~anti_slop.engine.Engine` composes them.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any, Iterator

__all__ = ["FileContext", "Violation", "Rule"]


@dataclass
class FileContext:
    """Everything a rule needs to analyze one Python file.

    ``options`` is the merged option bag for the *current* rule only: the rule's
    :attr:`Rule.default_options` overlaid with any project-configured options.
    """

    path: str
    source: str
    tree: ast.Module
    options: dict[str, Any]


@dataclass
class Violation:
    """A single reported problem."""

    rule: str
    line: int  # 1-based (from ``ast``)
    column: int  # 0-based (from ``ast``)
    message: str
    end_line: int | None = None
    end_column: int | None = None

    def location(self) -> str:
        """``line:column`` with a 1-based column, matching most linters."""
        return f"{self.line}:{self.column + 1}"

    def format(self) -> str:
        return f"{self.location()}: {self.rule} {self.message}"


class Rule:
    """Base class for anti-slop rules.

    Subclasses set the class attributes :attr:`name`, :attr:`description`,
    :attr:`messages` and :attr:`default_options`, and implement :meth:`check`.

    ``name`` is the stable rule identifier used in configuration, e.g.
    ``"anti-slop/no-object-parameters"``. ``messages`` maps a short key to a
    message template (``str.format`` fields); rules emit a violation by calling
    :meth:`report` with one of those keys.
    """

    name: str = ""
    description: str = ""
    messages: dict[str, str] = {}
    default_options: dict[str, Any] = {}

    def report(self, ctx: FileContext, node: ast.AST, key: str, **data: Any) -> Violation:
        """Build a :class:`Violation` for ``node`` using the ``messages[key]`` template."""
        template = self.messages.get(key, key)
        try:
            message = template.format(**data)
        except (KeyError, IndexError, ValueError):
            message = template
        return Violation(
            rule=self.name,
            line=getattr(node, "lineno", 0) or 0,
            column=getattr(node, "col_offset", 0) or 0,
            message=message,
            end_line=getattr(node, "end_lineno", None),
            end_column=getattr(node, "end_col_offset", None),
        )

    def check(self, ctx: FileContext) -> Iterator[Violation]:
        """Yield the violations this rule finds in ``ctx.tree``."""
        raise NotImplementedError
