"""Locate ``@typing.overload`` implementation functions.

An overload set states its real contract in the stubs; the implementation that
follows them is required to accept and return the *union* of every stub, which
in practice is spelled ``Any``::

    @overload
    def parse(raw: str) -> Document: ...
    @overload
    def parse(raw: bytes) -> Document: ...
    def parse(raw: Any) -> Any:      # the implementation
        ...

Flagging that implementation is a false positive: the stubs above it already
carry the evidence, and no narrower annotation is available. The ``Any`` rules
use :func:`overload_implementations` to skip it.
"""

from __future__ import annotations

import ast

from .type_utils import dotted_name

__all__ = ["overload_implementations"]

_OVERLOAD_NAMES = frozenset({"overload", "typing.overload", "typing_extensions.overload"})

_SCOPED_BODIES = (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)

type _FunctionDef = ast.FunctionDef | ast.AsyncFunctionDef


def _is_overload_decorator(decorator: ast.expr) -> bool:
    return dotted_name(decorator) in _OVERLOAD_NAMES


def _is_overload_stub(node: _FunctionDef) -> bool:
    return any(_is_overload_decorator(d) for d in node.decorator_list)


def overload_implementations(tree: ast.Module) -> set[ast.AST]:
    """The function nodes that implement an ``@overload`` set.

    A function is an implementation when it is *not* decorated with
    ``@overload`` but a sibling in the same body — same scope, same name — is.
    Scoping matters: an unrelated module-level ``def parse`` is not the
    implementation of a class's overloaded ``parse``.
    """
    implementations: set[ast.AST] = set()
    for scope in ast.walk(tree):
        if not isinstance(scope, _SCOPED_BODIES):
            continue
        overloaded: set[str] = set()
        candidates: list[_FunctionDef] = []
        for statement in scope.body:
            if not isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if _is_overload_stub(statement):
                overloaded.add(statement.name)
            else:
                candidates.append(statement)
        implementations.update(
            node for node in candidates if node.name in overloaded
        )
    return implementations
