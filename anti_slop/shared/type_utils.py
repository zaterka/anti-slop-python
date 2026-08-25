"""Helpers for inspecting Python type annotations in an AST.

Python type hints are just expressions, so these helpers answer the questions
the rules need: *what name does this annotation refer to, does it (through a
local alias) resolve to ``Any`` or ``object``, is it a union, and what is the
value type of a ``dict[...]`` annotation?*

Resolution is deliberately conservative: only module- and class-level aliases
(:mod:`anti_slop.shared.type_utils.build_type_aliases`) are followed, and a
cycle guard stops recursive aliases.
"""

from __future__ import annotations

import ast

__all__ = [
    "BUILTIN_ANY_NAMES",
    "BUILTIN_OBJECT_NAMES",
    "CAST_NAMES",
    "SENSITIVE_SYMBOLS",
    "shadowed_sensitive_symbols",
    "WRAPPER_VALUE_POSITIONS",
    "dotted_name",
    "import_map",
    "assigned_names",
    "is_typing_symbol",
    "build_type_aliases",
    "resolve_alias",
    "annotation_is_any",
    "annotation_is_object",
    "annotation_is_broad",
    "union_members",
    "dict_value_annotation",
    "wrapper_value_args",
    "is_typing_cast",
    "is_known_evidence",
    "is_mutable_display",
]

# Names that refer to typing.Any regardless of how they are qualified.
BUILTIN_ANY_NAMES = {"Any", "typing.Any", "typing_extensions.Any"}
# Names that refer to the built-in object type.
BUILTIN_OBJECT_NAMES = {"object", "builtins.object"}
# Names that refer to typing.cast (the only sanctioned "assertion" in Python).
CAST_NAMES = {"cast", "typing.cast", "typing_extensions.cast"}

# Bare names whose meaning the rules depend on. A module-level definition with
# one of these names shadows the typing/builtins symbol, and rules must not
# treat references to it as the typing symbol.
SENSITIVE_SYMBOLS = frozenset(
    {"Any", "object", "cast", "TypeAlias", "Union", "Optional", "TypeGuard", "TypeIs"}
)

# For typing containers, which type-argument positions carry the *value* type.
# ``Coroutine[X, Y, R]`` uses X (sent-from) and Y (send-type) as conventional
# ``Any`` boilerplate, so only R is the value position. Built-in generics
# (``list``, ``set``, ...) carry their value type at position 0.
WRAPPER_VALUE_POSITIONS: dict[str, tuple[int, ...]] = {
    "Awaitable": (0,),
    "typing.Awaitable": (0,),
    "Coroutine": (2,),
    "typing.Coroutine": (2,),
    "Generator": (0, 2),
    "typing.Generator": (0, 2),
    "AsyncGenerator": (0, 2),
    "typing.AsyncGenerator": (0, 2),
    "AsyncIterator": (0,),
    "typing.AsyncIterator": (0,),
    "AsyncIterable": (0,),
    "typing.AsyncIterable": (0,),
    "Iterable": (0,),
    "typing.Iterable": (0,),
    "Sequence": (0,),
    "typing.Sequence": (0,),
    "Collection": (0,),
    "typing.Collection": (0,),
    "Iterator": (0,),
    "typing.Iterator": (0,),
    "list": (0,),
    "typing.List": (0,),
    "set": (0,),
    "typing.Set": (0,),
    "frozenset": (0,),
    "typing.FrozenSet": (0,),
}

# Containers with non-fixed value positions, handled specially by
# :func:`wrapper_value_args`: every element of ``tuple[X, Y]`` (the trailing
# Ellipsis of ``tuple[X, ...]`` is a repeat marker, not a value) and the last
# argument of ``Callable[..., R]``.
_TUPLE_NAMES = {"tuple", "typing.Tuple"}
_CALLABLE_NAMES = {"Callable", "typing.Callable"}

# Dictionary-family mappings: the dict display plus the stdlib/typing variants
# that carry the same value contract.
_DICT_NAMES = {
    "dict",
    "typing.Dict",
    "defaultdict",
    "collections.defaultdict",
    "OrderedDict",
    "collections.OrderedDict",
    "DefaultDict",
    "typing.DefaultDict",
}
_UNION_NAMES = {"Union", "typing.Union"}
_OPTIONAL_NAMES = {"Optional", "typing.Optional"}


def dotted_name(node: ast.AST) -> str | None:
    """Return the dotted name for a ``Name``/``Attribute`` chain, else ``None``.

    ``foo.Bar.baz`` -> ``"foo.Bar.baz"``; ``foo.bar`` -> ``"foo.bar"``;
    ``Bar`` -> ``"Bar"``. A quoted forward reference is its own string:
    ``"User"`` -> ``"User"`` — so rules that resolve names also resolve
    string annotations instead of silently skipping them. Subscripts and
    other expressions return ``None``.
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = dotted_name(node.value)
        if base is None:
            return None
        return f"{base}.{node.attr}"
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def import_map(tree: ast.Module) -> dict[str, str]:
    """Map each module-level imported local name to its source module.

    ``from typing import Any`` -> ``{"Any": "typing"}``;
    ``import foo.bar`` -> ``{"foo": "foo.bar"}``;
    ``from x import y as z`` -> ``{"z": "x"}``.
    """
    out: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                out[local] = alias.name
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                if alias.name == "*":
                    continue
                local = alias.asname or alias.name
                out[local] = module
    return out


def assigned_names(tree: ast.Module) -> set[str]:
    """Module-level and class-level simple names that are *defined*, not imported.

    Used to detect shadowing of typing symbols (``class Any: ...`` or
    ``cast = my_cast``) so rules do not misfire on a local that merely shares
    a name with a typing builtin. Function bodies are not included: a method
    named ``Any`` does not shadow the module-level ``Any``.
    """
    out: set[str] = set()

    def add_scope(statements: list[ast.stmt]) -> None:
        for node in statements:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out.add(node.name)
            elif isinstance(node, ast.ClassDef):
                out.add(node.name)
                add_scope(node.body)
            elif isinstance(node, ast.TypeAlias):
                name = dotted_name(node.name)
                if name is not None and "." not in name:
                    out.add(name)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        out.add(target.id)
            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name):
                    out.add(node.target.id)

    add_scope(tree.body)
    return out


def shadowed_sensitive_symbols(tree: ast.Module) -> frozenset[str]:
    """Sensitive bare names shadowed by module-/class-level definitions.

    Pass the result to :func:`annotation_is_any` / :func:`annotation_is_object`
    as ``shadowed`` so a local ``class Any`` or ``object = ...`` is not treated
    as the typing/builtins symbol.
    """
    return frozenset(assigned_names(tree) & SENSITIVE_SYMBOLS)


def is_typing_symbol(name: str, imports: dict[str, str]) -> bool:
    """True when a local name refers to a ``typing``/``typing_extensions`` symbol.

    ``typing.Any`` and ``typing_extensions.Any`` qualify. A bare name is a
    typing symbol when it is imported from typing (or not imported at all, in
    which case the conventional assumption is that it is the typing symbol — an
    unimported ``Any`` is a NameError at runtime). A module import that
    shadows ``typing`` (``from foo import typing``) breaks the reference.
    """
    base = name.split(".")[0]
    if base in ("typing", "typing_extensions", "builtins"):
        if base in imports:
            return imports[base] == base
        return True
    if name in imports:
        return imports[name] in ("typing", "typing_extensions")
    return True


def build_type_aliases(tree: ast.Module) -> dict[str, ast.AST]:
    """Collect module- and class-level type aliases: name -> right-hand node.

    Recognized forms (mirroring how Python declares aliases):

    * ``type Alias = RHS`` (PEP 695, 3.12+; ``ast.TypeAlias``)
    * ``Alias: TypeAlias = RHS``
    * ``Alias = RHS`` where ``RHS`` is type-like (a name, dotted name,
      subscripted generic, ``|`` union, or call such as ``Optional[str]``).

    The first declaration of a name wins; later redefinitions are ignored
    (matching the reference implementation's handling of duplicate aliases).
    """
    aliases: dict[str, ast.AST] = {}
    for node in _module_and_class_level_statements(tree):
        if isinstance(node, ast.TypeAlias):
            name = dotted_name(node.name)
            if name is not None and "." not in name:
                aliases.setdefault(name, node.value)
        elif isinstance(node, ast.AnnAssign):
            if (
                isinstance(node.target, ast.Name)
                and node.value is not None
                and _is_type_alias_annotation(node.annotation)
            ):
                aliases.setdefault(node.target.id, node.value)
        elif isinstance(node, ast.Assign):
            if (
                len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and _looks_like_type(node.value)
            ):
                aliases.setdefault(node.targets[0].id, node.value)
    return aliases


def _module_and_class_level_statements(tree: ast.Module) -> list[ast.stmt]:
    statements: list[ast.stmt] = []
    for node in tree.body:
        statements.append(node)
        if isinstance(node, ast.ClassDef):
            statements.extend(node.body)
    return statements


def _is_type_alias_annotation(node: ast.AST) -> bool:
    return dotted_name(node) in {"TypeAlias", "typing.TypeAlias"}


def _looks_like_type(node: ast.AST) -> bool:
    """Heuristic: does this expression read as a type, not a value?"""
    if isinstance(node, (ast.Name, ast.Attribute, ast.Subscript, ast.BinOp, ast.Call)):
        return True
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Invert):
        return False
    return False


def resolve_alias(
    node: ast.AST,
    aliases: dict[str, ast.AST],
    visited: frozenset[str] = frozenset(),
) -> ast.AST:
    """Follow a chain of local aliases to the node they ultimately name.

    ``A = Any; B = A; C = B`` -> resolving ``C`` yields the ``Any`` node. A
    cycle guard (``visited``) makes recursive aliases terminate.
    """
    if isinstance(node, ast.Name) and node.id in aliases and node.id not in visited:
        return resolve_alias(aliases[node.id], aliases, visited | {node.id})
    return node


def annotation_is_any(
    node: ast.AST,
    aliases: dict[str, ast.AST],
    imports: dict[str, str],
    shadowed: frozenset[str] = frozenset(),
    _visited: frozenset[str] = frozenset(),
) -> bool:
    """True when the annotation is (or resolves through local aliases to) ``Any``.

    Follows local aliases one step at a time; the ``_visited`` set makes
    recursive aliases terminate. ``shadowed`` names a bare local definition
    (e.g. ``class Any``) that would hijack the reference; a bare name in
    ``shadowed`` is not the typing symbol.
    """
    if isinstance(node, ast.Name):
        if node.id in shadowed:
            return False
        if node.id in aliases and node.id not in _visited:
            return annotation_is_any(
                aliases[node.id], aliases, imports, shadowed, _visited | {node.id}
            )
    name = dotted_name(node)
    if name is None:
        return False
    if name not in BUILTIN_ANY_NAMES:
        return False
    return is_typing_symbol(name, imports)


def annotation_is_object(
    node: ast.AST,
    aliases: dict[str, ast.AST],
    imports: dict[str, str],
    shadowed: frozenset[str] = frozenset(),
    _visited: frozenset[str] = frozenset(),
) -> bool:
    """True when the annotation is (or resolves through local aliases to) ``object``."""
    if isinstance(node, ast.Name):
        if node.id in shadowed:
            return False
        if node.id in aliases and node.id not in _visited:
            return annotation_is_object(
                aliases[node.id], aliases, imports, shadowed, _visited | {node.id}
            )
    name = dotted_name(node)
    if name is None:
        return False
    if name not in BUILTIN_OBJECT_NAMES:
        return False
    return is_typing_symbol(name, imports)


def annotation_is_broad(
    node: ast.AST,
    aliases: dict[str, ast.AST],
    imports: dict[str, str],
    shadowed: frozenset[str] = frozenset(),
) -> str | None:
    """Classify a bare (non-union) annotation: ``"any"``, ``"object"``, or ``None``."""
    if annotation_is_any(node, aliases, imports, shadowed):
        return "any"
    if annotation_is_object(node, aliases, imports, shadowed):
        return "object"
    return None


def union_members(node: ast.AST) -> list[ast.AST] | None:
    """The members of a union annotation, or ``None`` when it is not a union.

    Handles ``A | B | C`` (flattened), ``Union[A, B]``, and ``Optional[X]``
    (returned as ``[X]`` — the implicit ``None`` member is omitted because no
    rule treats ``None`` as broad).
    """
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        left = union_members(node.left)
        right = union_members(node.right)
        if left is not None and right is not None:
            return left + right
        if left is not None:
            return left + [node.right]
        if right is not None:
            return [node.left] + right
        return [node.left, node.right]

    if isinstance(node, ast.Subscript):
        name = dotted_name(node.value)
        if name in _UNION_NAMES:
            slice_ = node.slice
            if isinstance(slice_, ast.Tuple):
                return list(slice_.elts)
            return [slice_]
        if name in _OPTIONAL_NAMES:
            return [node.slice]

    return None


def dict_value_annotation(node: ast.AST) -> ast.AST | None:
    """The value type of a two-parameter ``dict[K, V]``/``Dict[K, V]`` annotation.

    Returns ``None`` for non-dict annotations, bare ``dict``, and
    single-parameter subscripts.
    """
    if not isinstance(node, ast.Subscript):
        return None
    name = dotted_name(node.value)
    if name not in _DICT_NAMES:
        return None
    slice_ = node.slice
    if isinstance(slice_, ast.Tuple) and len(slice_.elts) == 2:
        return slice_.elts[1]
    return None


def _slice_elements(node: ast.Subscript) -> list[ast.AST]:
    """The type-argument nodes of a subscript (``X[a, b]`` -> ``[a, b]``)."""
    slice_ = node.slice
    if isinstance(slice_, ast.Tuple):
        return list(slice_.elts)
    return [slice_]


def wrapper_value_args(node: ast.AST) -> list[ast.AST] | None:
    """The *value-position* type arguments of a value-carrying container.

    ``Awaitable[Any]`` -> ``[Any]``; ``Coroutine[Any, None, User]`` ->
    ``[User]``; ``list[Any]`` / ``set[Any]`` / ``tuple[Any, ...]`` -> the
    element types; ``Callable[[], Any]`` -> ``[Any]``; ``dict[str, Any]`` ->
    ``None`` (use :func:`dict_value_annotation`). Returns ``None`` when the
    annotation is not a known value-carrying container.
    """
    if not isinstance(node, ast.Subscript):
        return None
    name = dotted_name(node.value)
    if name is None:
        return None
    elts = _slice_elements(node)
    if name in _TUPLE_NAMES:
        return [
            elt
            for elt in elts
            if not (isinstance(elt, ast.Constant) and elt.value is Ellipsis)
        ]
    if name in _CALLABLE_NAMES:
        return [elts[-1]] if elts else None
    if name not in WRAPPER_VALUE_POSITIONS:
        return None
    positions = WRAPPER_VALUE_POSITIONS[name]
    return [elts[i] for i in positions if i < len(elts)]


def is_typing_cast(
    node: ast.AST,
    imports: dict[str, str],
    assigned: set[str],
) -> bool:
    """True when ``node`` is a call to ``typing.cast``/``typing_extensions.cast``.

    A module-level ``def cast`` or non-typing import shadows the typing
    symbol; dotted forms (``typing.cast``) follow the import shadowing rules
    of :func:`is_typing_symbol`.
    """
    if not isinstance(node, ast.Call) or len(node.args) < 2:
        return False
    name = dotted_name(node.func)
    if name is None or name not in CAST_NAMES:
        return False
    if name == "cast" and "cast" in assigned:
        return False
    return is_typing_symbol(name, imports)


def is_known_evidence(node: ast.AST) -> bool:
    """Syntactic evidence that a value carries a more specific type than ``object``.

    Mirrors the reference implementation's ``isKnownEvidenceExpression``:
    literals, container displays, strings/f-strings, unary constants, and
    function/class definitions. A bare name or call is *not* evidence because
    its type cannot be established from syntax alone. ``None`` is not evidence:
    ``x: Any = None`` is the idiomatic optional placeholder, not a widened value.
    """
    if isinstance(node, ast.Constant):
        return node.value is not None
    return isinstance(
        node,
        (
            ast.List,
            ast.Tuple,
            ast.Set,
            ast.Dict,
            ast.JoinedStr,
            ast.Lambda,
            ast.FunctionDef,
            ast.AsyncFunctionDef,
            ast.ClassDef,
            ast.UnaryOp,
        ),
    )


def is_mutable_display(node: ast.AST) -> bool:
    """A value that creates a mutable object shared across its uses.

    A list/dict/set display, or a no-argument ``list()``/``dict()``/``set()``
    call. Used by the mutable-default rules: such a value as a parameter or
    dataclass field default is evaluated once and shared by every call/instance.
    """
    if isinstance(node, (ast.List, ast.Dict, ast.Set)):
        return True
    return (
        isinstance(node, ast.Call)
        and not node.args
        and not node.keywords
        and isinstance(node.func, ast.Name)
        and node.func.id in {"list", "dict", "set"}
    )
