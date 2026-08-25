"""Engine: walk Python files, run the active rules, collect results.

The engine is deliberately simple. It parses each file once, hands every active
rule a :class:`~anti_slop.core.FileContext`, and gathers the violations. A rule
that raises is contained (reported as a result error) so one buggy rule cannot
take down a lint run.
"""

from __future__ import annotations

import ast
import fnmatch
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

from .config import Config
from .core import FileContext, Rule, Violation

__all__ = [
    "DEFAULT_IGNORED_DIRS",
    "LintResult",
    "iter_python_files",
    "lint_file",
    "lint_paths",
    "active_rules",
]

# Directories never worth linting, regardless of configuration.
DEFAULT_IGNORED_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        "__pycache__",
        ".venv",
        "venv",
        "env",
        ".env",
        "node_modules",
        ".tox",
        ".nox",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".eggs",
        "site-packages",
        "dist",
        "build",
    }
)


@dataclass
class LintResult:
    """The outcome of linting a single file."""

    path: Path
    violations: list[Violation] = field(default_factory=list)
    error: str | None = None  # set when the file could not be parsed/read

    @property
    def ok(self) -> bool:
        return not self.violations and self.error is None


def active_rules(config: Config) -> list[tuple[Rule, dict]]:
    """The enabled rules, each paired with its merged option dict."""
    # Imported here to avoid a circular import at module load time.
    from . import rules as rules_pkg

    result: list[tuple[Rule, dict]] = []
    for rule in rules_pkg.ALL_RULES:
        if config.is_enabled(rule.name):
            result.append((rule, config.options_for(rule.name)))
    return result


def _is_ignored(path: Path, root: Path, ignore: list[str]) -> bool:
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path
    if any(part in DEFAULT_IGNORED_DIRS for part in rel.parts):
        return True
    rel_str = rel.as_posix()
    return any(fnmatch.fnmatch(rel_str, pattern) for pattern in ignore)


def iter_python_files(paths: list[Path], ignore: list[str]) -> Iterator[Path]:
    """Yield Python files from the given paths (files or directories).

    Explicitly passed files are always yielded; directory walks skip
    :data:`DEFAULT_IGNORED_DIRS` and any configured ``ignore`` patterns.
    """
    seen: set[Path] = set()
    for raw in paths:
        path = raw
        if path.is_file():
            if path.suffix == ".py":
                resolved = path.resolve()
                if resolved not in seen:
                    seen.add(resolved)
                    yield path
            continue
        if not path.is_dir():
            continue
        root = path.resolve()
        for file in sorted(root.rglob("*.py")):
            if _is_ignored(file, root, ignore):
                continue
            if file in seen:
                continue
            seen.add(file)
            yield file


def lint_file(
    path: Path,
    active: list[tuple[Rule, dict]],
) -> LintResult:
    """Lint a single file with the active rules."""
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return LintResult(path=path, error=f"could not read file: {exc}")

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        line = exc.lineno or 0
        return LintResult(path=path, error=f"syntax error at line {line}: {exc.msg}")
    except (ValueError, RecursionError) as exc:
        return LintResult(path=path, error=f"could not parse file: {exc}")

    violations: list[Violation] = []
    errors: list[str] = []
    for rule, options in active:
        ctx = FileContext(path=str(path), source=source, tree=tree, options=options)
        try:
            violations.extend(rule.check(ctx))
        except Exception as exc:  # a rule bug must not abort the whole run
            errors.append(f"{rule.name} failed: {exc!r}")

    violations.sort(key=lambda v: (v.line, v.column, v.rule))
    error = "; ".join(errors) if errors else None
    return LintResult(path=path, violations=violations, error=error)


def lint_paths(paths: list[Path], config: Config) -> list[LintResult]:
    """Lint every Python file under ``paths`` per ``config``."""
    active = active_rules(config)
    results: list[LintResult] = []
    for path in iter_python_files(paths, config.ignore):
        results.append(lint_file(path, active))
    return results
