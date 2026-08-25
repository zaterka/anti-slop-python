"""Iterate the *declared* symbol names of a module.

The reference implementation flags every identifier reference, which is
reasonable in TypeScript but noisy in Python (every attribute lookup and
variable read is an identifier). The Python rule therefore reports
declarations only: the one place a name is *chosen*.
"""

from __future__ import annotations

import ast
from typing import Iterator

__all__ = ["iter_symbol_names"]


def _target_names(target: ast.AST) -> Iterator[ast.AST]:
    """Yield the name nodes an assignment target binds."""
    if isinstance(target, ast.Name):
        yield target
    elif isinstance(target, (ast.Tuple, ast.List)):
        for element in target.elts:
            yield from _target_names(element)
    elif isinstance(target, ast.Starred):
        yield from _target_names(target.value)
    elif isinstance(target, ast.Attribute):
        # ``self.user_shape = ...`` chooses the attribute name.
        yield target


def _pattern_names(pattern: ast.pattern) -> Iterator[tuple[ast.AST, str]]:
    """Yield captured names from match patterns (3.10+)."""
    if isinstance(pattern, ast.MatchAs):
        if pattern.name is not None:
            yield (pattern, pattern.name)
        if pattern.pattern is not None:
            yield from _pattern_names(pattern.pattern)
    elif isinstance(pattern, ast.MatchStar):
        if pattern.name is not None:
            yield (pattern, pattern.name)
    elif isinstance(pattern, ast.MatchMapping):
        if pattern.rest is not None:
            yield (pattern, pattern.rest)
    elif isinstance(pattern, ast.MatchClass):
        for attr in pattern.kwd_attrs:
            yield (pattern, attr)
        for element in pattern.patterns:
            yield from _pattern_names(element)
    elif isinstance(pattern, ast.MatchSequence):
        for element in pattern.patterns:
            yield from _pattern_names(element)
    elif isinstance(pattern, ast.MatchOr):
        for element in pattern.patterns:
            yield from _pattern_names(element)
    elif isinstance(pattern, ast.MatchValue):
        pass  # no capture


_TYPEVAR_CALL_NAMES = {"TypeVar", "ParamSpec", "TypeVarTuple", "NewType"}


def iter_symbol_names(tree: ast.Module) -> Iterator[tuple[ast.AST, str]]:
    """Yield ``(node, name)`` for every declared symbol in the module.

    Covers function/class/method names, parameters (including ``*args`` and
    ``**kwargs``), assignment targets (including tuple unpacking, starred
    targets, and attribute assignments), imports, ``with``/``except``/
    comprehension targets, walrus targets, ``global``/``nonlocal`` names,
    match-pattern captures, and PEP 695 type parameters.
    """
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield (node, node.name)
            for type_param in getattr(node, "type_params", []):
                yield (node, type_param.name)
        elif isinstance(node, ast.ClassDef):
            yield (node, node.name)
            for type_param in getattr(node, "type_params", []):
                yield (node, type_param.name)
        elif isinstance(node, ast.arg):
            yield (node, node.arg)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                for name_node in _target_names(target):
                    if isinstance(name_node, ast.Name):
                        yield (name_node, name_node.id)
                    elif isinstance(name_node, ast.Attribute):
                        yield (name_node, name_node.attr)
        elif isinstance(node, ast.AnnAssign):
            for name_node in _target_names(node.target):
                if isinstance(name_node, ast.Name):
                    yield (name_node, name_node.id)
                elif isinstance(name_node, ast.Attribute):
                    yield (name_node, name_node.attr)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                yield (alias, local)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    continue
                local = alias.asname or alias.name
                yield (alias, local)
        elif isinstance(node, ast.With):
            for item in node.items:
                if item.optional_vars is not None:
                    for name_node in _target_names(item.optional_vars):
                        if isinstance(name_node, ast.Name):
                            yield (name_node, name_node.id)
        elif isinstance(node, ast.ExceptHandler):
            if node.name is not None:
                yield (node, node.name)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            for name_node in _target_names(node.target):
                if isinstance(name_node, ast.Name):
                    yield (name_node, name_node.id)
        elif isinstance(node, ast.comprehension):
            for name_node in _target_names(node.target):
                if isinstance(name_node, ast.Name):
                    yield (name_node, name_node.id)
        elif isinstance(node, ast.NamedExpr):
            yield (node.target, node.target.id)
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            for name in node.names:
                yield (node, name)
        elif isinstance(node, ast.Match):
            for case in node.cases:
                for pattern_node, name in _pattern_names(case.pattern):
                    yield (pattern_node, name)
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in _TYPEVAR_CALL_NAMES
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            # The real name of TypeVar("T") / NewType("T", ...) lives in the
            # first argument, not in the assignment target.
            yield (node, node.args[0].value)
