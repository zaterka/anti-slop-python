"""``no-dataclass-mutable-defaults``: ban mutable defaults on dataclass fields.

Python-specific rule (no JS/TS counterpart). A ``@dataclass`` field with a
mutable literal default (``items: list = []``) is a runtime ``ValueError`` at
class-creation time — Python refuses the field because the default would be
shared by every instance. Models produce this constantly; the dataclass form
of the fix is ``field(default_factory=list)``.

Recognized decorators: ``@dataclass``, ``@dataclasses.dataclass``, and their
called forms (``@dataclass(frozen=True)``). Field annotations with
``field(...)`` defaults are correct and are not flagged.

``ClassVar`` annotations are exempt: dataclasses treats them as pseudo-fields
and never installs them as instance state, so ``registry: ClassVar[dict] = {}``
raises nothing and is the ordinary way to declare shared class-level state.
"""

from __future__ import annotations

import ast

from anti_slop.core import FileContext, Rule

from ..shared.type_utils import dotted_name, is_mutable_display

__all__ = ["NoDataclassMutableDefaultsRule"]

_DATACLASS_DECORATOR_NAMES = frozenset({"dataclass", "dataclasses.dataclass"})

# ``ClassVar[...]`` marks a pseudo-field: dataclasses skips it entirely, so a
# mutable default on one is legal and deliberate, not the shared-state bug.
_CLASS_VAR_NAMES = frozenset({"ClassVar", "typing.ClassVar", "typing_extensions.ClassVar"})


def _is_dataclass_decorator(decorator: ast.expr) -> bool:
    target = decorator.func if isinstance(decorator, ast.Call) else decorator
    return dotted_name(target) in _DATACLASS_DECORATOR_NAMES


def _is_class_var(annotation: ast.expr) -> bool:
    """True for ``ClassVar`` and ``ClassVar[X]`` in any qualified spelling."""
    target = annotation.value if isinstance(annotation, ast.Subscript) else annotation
    return dotted_name(target) in _CLASS_VAR_NAMES


class NoDataclassMutableDefaultsRule(Rule):
    """Disallow mutable default values on dataclass fields."""

    name = "anti-slop/no-dataclass-mutable-defaults"
    description = (
        "Disallow mutable default values on dataclass fields; they raise "
        "ValueError at class creation. Use field(default_factory=...) instead."
    )
    messages = {
        "mutableFieldDefault": (
            "Dataclass field `{name}` has a mutable default; it would raise "
            "ValueError at class creation and would otherwise be shared by "
            "every instance. Use `field(default_factory=...)` instead."
        ),
    }

    def check(self, ctx: FileContext):
        for node in ast.walk(ctx.tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if not any(
                _is_dataclass_decorator(d) for d in node.decorator_list
            ):
                continue
            for statement in node.body:
                if not isinstance(statement, ast.AnnAssign):
                    continue
                target = statement.target
                if not (
                    isinstance(target, ast.Name)
                    and statement.value is not None
                    and is_mutable_display(statement.value)
                ):
                    continue
                if _is_class_var(statement.annotation):
                    continue
                yield self.report(
                    ctx, statement, "mutableFieldDefault", name=target.id
                )
