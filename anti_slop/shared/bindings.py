"""Lightweight binding tracking for flow-sensitive rules.

Python's AST has no scope tree, so these helpers approximate one: they collect
the simple-name assignments made in a statement list (a function body or the
module body) and record, per name, the initializing assignment and any later
writes. A name with exactly one write (the init) is the Python analogue of a
``const`` binding.

This is deliberately conservative — the flow rules that use it
(``no-known-value-widening``, ``no-widen-then-assert``) only report on
bindings they can prove stable, so an imprecise approximation costs false
negatives, not false positives.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Iterable

__all__ = [
    "Binding",
    "collect_bindings",
    "is_stable",
    "scope_bodies",
    "iter_scope_statements",
    "iter_scope_nodes",
]


@dataclass
class Binding:
    """A simple-name binding in one scope."""

    name: str
    init: ast.AST | None  # first assignment node (Assign or AnnAssign)
    init_value: ast.AST | None  # the value expression of the init (may be None)
    annotation: ast.AST | None  # annotation on the init AnnAssign, if any
    writes: list[ast.AST] = field(default_factory=list)  # all assignment nodes, init first

    @property
    def value(self) -> ast.AST | None:
        return self.init_value


def _target_is_simple_name(target: ast.AST) -> bool:
    return isinstance(target, ast.Name)


def collect_bindings(statements: Iterable[ast.stmt]) -> dict[str, Binding]:
    """Collect simple-name bindings across all statements (and nested blocks).

    Parameters of the enclosing function are not included here; callers that
    need them (the flow rules) treat parameters separately, since a parameter
    is a binding whose "init" is the caller's argument.
    """
    bindings: dict[str, Binding] = {}

    def record(target: ast.AST, statement: ast.AST, value: ast.AST | None, annotation: ast.AST | None) -> None:
        if not _target_is_simple_name(target):
            return
        name = target.id  # type: ignore[union-attr]
        binding = bindings.get(name)
        if binding is None:
            binding = Binding(name=name, init=statement, init_value=value, annotation=annotation)
            bindings[name] = binding
        binding.writes.append(statement)

    def walk(statements: list[ast.stmt]) -> None:
        for node in statements:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    record(target, node, node.value, None)
            elif isinstance(node, ast.AnnAssign):
                record(node.target, node, node.value, node.annotation)
            elif isinstance(node, ast.AugAssign):
                # Augmented assignment is a write; the init (if any) is recorded
                # by the original Assign/AnnAssign.
                if _target_is_simple_name(node.target):
                    name = node.target.id  # type: ignore[union-attr]
                    if name in bindings:
                        bindings[name].writes.append(node)
            elif isinstance(node, (ast.For, ast.AsyncFor)):
                record(node.target, node, None, None)
                walk(node.body)
                walk(node.orelse)
            elif isinstance(node, ast.With) or isinstance(node, ast.AsyncWith):
                for item in node.items:
                    if item.optional_vars is not None:
                        record(item.optional_vars, node, None, None)
                walk(node.body)
            elif isinstance(node, ast.ExceptHandler):
                if node.name is not None:
                    target = ast.Name(id=node.name, ctx=ast.Store())
                    record(target, node, None, None)
                walk(node.body)
            elif isinstance(node, (ast.If, ast.While)):
                walk(node.body)
                walk(node.orelse)
            elif isinstance(node, ast.Try):
                walk(node.body)
                for handler in node.handlers:
                    walk(handler.body)
                walk(node.orelse)
                walk(node.finalbody)
            elif isinstance(node, ast.TryStar):
                walk(node.body)
                for handler in node.handlers:
                    walk(handler.body)
                walk(node.finalbody)
            elif isinstance(node, ast.Match):
                for case in node.cases:
                    walk(case.body)
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                # Nested scopes are separate; do not leak their bindings outward.
                continue

    for statement in statements:
        walk([statement])

    return bindings


def is_stable(binding: Binding) -> bool:
    """True when the binding was written exactly once (its init) — a ``const``."""
    return binding.init is not None and len(binding.writes) == 1


def scope_bodies(tree: ast.Module) -> Iterable[tuple[ast.AST | None, list[ast.stmt]]]:
    """Yield ``(owner, body)`` for every scope in the module.

    The module scope has ``owner=None``; each ``FunctionDef``/
    ``AsyncFunctionDef``/``ClassDef`` contributes its body with itself as the
    owner. Nested scopes are yielded independently (a function inside a class
    is its own scope).
    """
    yield (None, list(tree.body))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            yield (node, list(node.body))


def iter_scope_statements(statements: Iterable[ast.stmt]) -> Iterable[ast.stmt]:
    """Yield every statement in a scope, without crossing scope boundaries.

    Descends into compound statements (if/for/while/with/try/match) but stops
    at nested ``FunctionDef``/``AsyncFunctionDef``/``ClassDef`` — their bodies
    are separate scopes with their own bindings.
    """
    for node in statements:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        yield node
        if isinstance(node, (ast.If, ast.While)):
            yield from iter_scope_statements(node.body)
            yield from iter_scope_statements(node.orelse)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            yield from iter_scope_statements(node.body)
            yield from iter_scope_statements(node.orelse)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            yield from iter_scope_statements(node.body)
        elif isinstance(node, ast.Try):
            yield from iter_scope_statements(node.body)
            for handler in node.handlers:
                yield from iter_scope_statements(handler.body)
            yield from iter_scope_statements(node.orelse)
            yield from iter_scope_statements(node.finalbody)
        elif isinstance(node, ast.TryStar):
            yield from iter_scope_statements(node.body)
            for handler in node.handlers:
                yield from iter_scope_statements(handler.body)
            yield from iter_scope_statements(node.finalbody)
        elif isinstance(node, ast.Match):
            for case in node.cases:
                yield from iter_scope_statements(case.body)


def iter_scope_nodes(statements: Iterable[ast.stmt]) -> Iterable[ast.AST]:
    """Yield every AST node in a scope, without crossing scope boundaries.

    Unlike :func:`iter_scope_statements`, this walks into expressions as well
    (so call nodes inside assignments, returns, and subscripts are found),
    while still stopping at nested function/class bodies. Each node is yielded
    exactly once: the walk starts at each top-level statement of the body.
    """
    for statement in statements:
        yield from _walk_nodes(statement)


def _walk_nodes(node: ast.AST) -> Iterable[ast.AST]:
    yield node
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue  # nested scope
        yield from _walk_nodes(child)
