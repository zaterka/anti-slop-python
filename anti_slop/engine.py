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
from .suppressions import parse_suppressions

__all__ = [
    "DEFAULT_IGNORED_DIRS",
    "ActiveRule",
    "LintResult",
    "iter_python_files",
    "lint_file",
    "lint_paths",
    "active_rules",
    "error_count",
    "violation_count",
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
        ".uv-cache",
        ".uv_cache",
        ".pytype",
        ".hypothesis",
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


@dataclass
class ActiveRule:
    """An enabled rule plus the configuration the engine applies to it."""

    rule: Rule
    options: dict
    exclude: list[str] = field(default_factory=list)

    def applies_to(self, relative_path: str) -> bool:
        """False when the rule is scoped off this path by ``exclude``."""
        return not any(
            fnmatch.fnmatch(relative_path, pattern) for pattern in self.exclude
        )


def active_rules(config: Config) -> list[ActiveRule]:
    """The enabled rules, each paired with its merged options and path scope."""
    # Imported here to avoid a circular import at module load time.
    from . import rules as rules_pkg

    result: list[ActiveRule] = []
    for rule in rules_pkg.ALL_RULES:
        if config.is_enabled(rule.name, rule.default_enabled):
            result.append(
                ActiveRule(
                    rule=rule,
                    options={**rule.default_options, **config.options_for(rule.name)},
                    exclude=config.exclude_for(rule.name),
                )
            )
    return result


def relative_to_anchor(path: Path, anchor: Path) -> str:
    """``path`` as a POSIX string relative to ``anchor``, for glob matching.

    A path outside the anchor keeps its own absolute form rather than growing
    a chain of ``..`` segments no pattern would match.
    """
    try:
        return path.resolve().relative_to(anchor).as_posix()
    except ValueError:
        return path.as_posix()


def _is_ignored(path: Path, anchor: Path, ignore: list[str]) -> bool:
    relative = relative_to_anchor(path, anchor)
    if any(part in DEFAULT_IGNORED_DIRS for part in Path(relative).parts):
        return True
    return any(fnmatch.fnmatch(relative, pattern) for pattern in ignore)


def iter_python_files(
    paths: list[Path], ignore: list[str], anchor: Path | None = None
) -> Iterator[Path]:
    """Yield Python files from the given paths (files or directories).

    Explicitly passed files are always yielded; directory walks skip
    :data:`DEFAULT_IGNORED_DIRS` and any configured ``ignore`` patterns.
    ``ignore`` patterns are matched relative to ``anchor`` (the configuration
    file's directory), not to whichever path is being walked, so the same
    pattern holds however the linter is invoked.
    """
    base = (anchor or Path.cwd()).resolve()
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
        for file in sorted(path.resolve().rglob("*.py")):
            if _is_ignored(file, base, ignore):
                continue
            if file in seen:
                continue
            seen.add(file)
            yield file


def lint_file(
    path: Path,
    active: list[ActiveRule],
    anchor: Path | None = None,
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

    relative = relative_to_anchor(path, (anchor or Path.cwd()).resolve())
    suppressions = parse_suppressions(source)

    violations: list[Violation] = []
    errors: list[str] = []
    for entry in active:
        if not entry.applies_to(relative):
            continue
        ctx = FileContext(
            path=str(path), source=source, tree=tree, options=dict(entry.options)
        )
        try:
            found = list(entry.rule.check(ctx))
        except Exception as exc:  # a rule bug must not abort the whole run
            errors.append(f"{entry.rule.name} failed: {exc!r}")
            continue
        violations.extend(
            v for v in found if not suppressions.suppresses(v.rule, v.line)
        )

    violations.sort(key=lambda v: (v.line, v.column, v.rule))
    error = "; ".join(errors) if errors else None
    return LintResult(path=path, violations=violations, error=error)


def lint_paths(paths: list[Path], config: Config) -> list[LintResult]:
    """Lint every Python file under ``paths`` per ``config``."""
    active = active_rules(config)
    anchor = config.anchor().resolve()
    return [
        lint_file(path, active, anchor)
        for path in iter_python_files(paths, config.ignore, anchor)
    ]


def violation_count(results: list[LintResult]) -> int:
    return sum(len(result.violations) for result in results)


def error_count(results: list[LintResult]) -> int:
    """Files that could not be read, parsed, or fully linted.

    Distinct from violations: an error means the linter did not get to form an
    opinion, which must never be reported as a clean run.
    """
    return sum(1 for result in results if result.error is not None)
