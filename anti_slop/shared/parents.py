"""Parent-link helpers.

Python's :mod:`ast` does not link nodes to their parents, so rules that need to
know the enclosing scope (a function, a statement, a type-parameter scope) build
a parent map once per file and query it.
"""

from __future__ import annotations

import ast
from typing import Iterator

__all__ = [
    "build_parent_map",
    "parent",
    "ancestors",
    "enclosing_function",
    "enclosing_type_params",
    "enclosing_statement",
]

_STATEMENT_TYPES = (
    ast.Expr,
    ast.Assign,
    ast.AnnAssign,
    ast.AugAssign,
    ast.Return,
    ast.Delete,
    ast.Raise,
    ast.Assert,
    ast.Import,
    ast.ImportFrom,
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.If,
    ast.While,
    ast.For,
    ast.AsyncFor,
    ast.With,
    ast.AsyncWith,
    ast.Match,
    ast.Try,
    ast.TryStar,
    ast.Global,
    ast.Nonlocal,
    ast.Break,
    ast.Continue,
    ast.Pass,
    ast.TypeAlias,
)


def build_parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    """Map every child node to the node that contains it."""
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def parent(parents: dict[ast.AST, ast.AST], node: ast.AST) -> ast.AST | None:
    return parents.get(node)


def ancestors(parents: dict[ast.AST, ast.AST], node: ast.AST) -> Iterator[ast.AST]:
    """Yield each ancestor of ``node``, nearest first."""
    current = parents.get(node)
    while current is not None:
        yield current
        current = parents.get(current)


def enclosing_function(parents: dict[ast.AST, ast.AST], node: ast.AST) -> ast.AST | None:
    """The nearest enclosing function, or ``None`` at module level."""
    for ancestor in ancestors(parents, node):
        if isinstance(ancestor, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return ancestor
    return None


def enclosing_type_params(parents: dict[ast.AST, ast.AST], node: ast.AST) -> set[str]:
    """Names of PEP 695 type parameters in scope at ``node``.

    A type parameter shadows a module-level alias or typing symbol, so
    ``def f[T](x: T)`` must not be treated as an annotation of ``object``/``Any``
    just because a module alias happens to be named ``T``.
    """
    names: set[str] = set()
    for ancestor in ancestors(parents, node):
        if isinstance(ancestor, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.update(tp.name for tp in getattr(ancestor, "type_params", []))
    return names


def _in_body_list(parent: ast.AST, node: ast.AST) -> bool:
    for field in ast.iter_fields(parent):
        value = getattr(parent, field[0])
        if isinstance(value, list) and node in value:
            return True
    return False


def enclosing_statement(parents: dict[ast.AST, ast.AST], node: ast.AST) -> ast.AST | None:
    """The nearest statement that directly contains ``node``.

    A node counts as the containing statement when it is a statement itself and
    appears in one of its parent's body-like lists. Returns ``None`` when the
    node is not inside a statement (it always is for parsed modules, but this
    keeps the helper total).
    """
    for ancestor in ancestors(parents, node):
        if isinstance(ancestor, _STATEMENT_TYPES) and _in_body_list(
            parents.get(ancestor, ast.Module(body=[], type_ignores=[])), ancestor
        ):
            return ancestor
    return None
