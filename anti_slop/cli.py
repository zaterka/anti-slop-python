"""Command-line interface for anti-slop.

Usage::

    anti-slop [paths...]            # lint files or directories (default: .)
    anti-slop --list-rules          # show every rule and its description
    anti-slop --format github       # GitHub Actions annotations
    anti-slop --config FILE         # use an explicit config file
    anti-slop --select no-eval-exec # run only the named rules
    anti-slop --ignore-rule no-debug-prints

Exit codes: ``0`` clean, ``1`` findings, ``2`` the run itself failed (bad
usage, unreadable configuration, or a file that could not be parsed). ``2``
matters in CI: a file the linter could not read is not a file that passed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import Config, find_config, parse_config_file
from .engine import LintResult, error_count, lint_paths, violation_count
from .rules import ALL_RULES, RULES_BY_NAME

__all__ = ["main", "build_parser"]

EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_ERROR = 2

_RULE_PREFIX = "anti-slop/"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="anti-slop",
        description=(
            "Opinionated AST rules that reject low-evidence and low-signal "
            "Python patterns."
        ),
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["."],
        help="Python files or directories to lint (default: current directory)",
    )
    parser.add_argument(
        "--config",
        metavar="FILE",
        help="path to a pyproject.toml or anti-slop.toml (default: search upward)",
    )
    parser.add_argument(
        "--list-rules",
        action="store_true",
        help="list every rule and its description, then exit",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json", "github"),
        default="text",
        help=(
            "output format: text (default), json, or github (workflow "
            "annotations that appear inline on a pull request)"
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="alias for --format json",
    )
    parser.add_argument(
        "--select",
        metavar="RULE",
        action="append",
        default=[],
        help=(
            "run only this rule (repeatable); overrides the configuration. "
            "Accepts a bare or fully qualified rule name."
        ),
    )
    parser.add_argument(
        "--ignore-rule",
        metavar="RULE",
        action="append",
        default=[],
        help="disable this rule for the run (repeatable)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress the summary line",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"anti-slop {__version__}",
    )
    return parser


def _normalize_rule(name: str) -> str:
    name = name.strip()
    return name if name.startswith(_RULE_PREFIX) else _RULE_PREFIX + name


def _load_config(explicit: str | None) -> Config:
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            print(f"error: config file not found: {path}", file=sys.stderr)
            raise SystemExit(EXIT_ERROR)
        return parse_config_file(path)
    return find_config(Path.cwd())


def _apply_rule_flags(config: Config, select: list[str], ignore: list[str]) -> Config:
    """Layer ``--select`` / ``--ignore-rule`` over the file configuration.

    ``--select`` is exclusive: naming any rule turns every other rule off, so a
    one-off run can target a single rule without editing configuration.
    """
    for name in map(_normalize_rule, ignore):
        config.rules.setdefault(name, {})["enabled"] = False
    if select:
        selected = {_normalize_rule(name) for name in select}
        for rule_name in RULES_BY_NAME:
            config.rules.setdefault(rule_name, {})["enabled"] = rule_name in selected
    return config


def _unknown_rules(names: list[str]) -> list[str]:
    return [name for name in names if _normalize_rule(name) not in RULES_BY_NAME]


def _report_errors(results: list[LintResult]) -> None:
    for result in results:
        if result.error:
            print(f"{result.path}: {result.error}", file=sys.stderr)


def _print_text(results: list[LintResult], quiet: bool) -> None:
    files_with_findings = 0
    for result in results:
        if not result.violations:
            continue
        files_with_findings += 1
        for violation in result.violations:
            print(
                f"{result.path}:{violation.location()}: {violation.rule} "
                f"{violation.message}"
            )
    if quiet:
        return

    total = violation_count(results)
    errors = error_count(results)
    if total:
        print(f"\n{total} problem(s) in {files_with_findings} file(s).")
    elif not errors:
        print("\nNo problems found.")
    if errors:
        print(f"{errors} file(s) could not be linted.", file=sys.stderr)


def _print_json(results: list[LintResult]) -> None:
    payload = {
        "violations": [
            {
                "file": str(result.path),
                "line": violation.line,
                "column": violation.column + 1,
                "end_line": violation.end_line,
                "end_column": (
                    violation.end_column + 1
                    if violation.end_column is not None
                    else None
                ),
                "rule": violation.rule,
                "message": violation.message,
            }
            for result in results
            for violation in result.violations
        ],
        "errors": [
            {"file": str(result.path), "error": result.error}
            for result in results
            if result.error is not None
        ],
    }
    print(json.dumps(payload, indent=2))


def _escape_annotation(value: str) -> str:
    """Escape a value for a GitHub workflow command.

    ``::`` delimits the command, and a literal newline would end it, so both
    are percent-encoded per the workflow-command specification.
    """
    return (
        value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    )


def _workspace_path(path: Path) -> str:
    """``path`` relative to the working directory.

    GitHub resolves annotation paths against the workspace root and silently
    drops an annotation whose file it cannot place, so an absolute path would
    never appear on the diff.
    """
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _print_github(results: list[LintResult]) -> None:
    """Emit workflow commands that GitHub renders inline on the pull request."""
    for result in results:
        file = _workspace_path(result.path)
        for violation in result.violations:
            location = (
                f"file={file},line={violation.line},col={violation.column + 1}"
            )
            if violation.end_line is not None:
                location += f",endLine={violation.end_line}"
            print(
                f"::error {location},title={_escape_annotation(violation.rule)}"
                f"::{_escape_annotation(violation.message)}"
            )
        if result.error is not None:
            print(
                f"::error file={file},title=anti-slop"
                f"::{_escape_annotation(result.error)}"
            )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_rules:
        for rule in ALL_RULES:
            print(f"{rule.name}")
            print(f"    {rule.description}")
        return EXIT_OK

    unknown_flags = _unknown_rules(args.select + args.ignore_rule)
    if unknown_flags:
        for name in unknown_flags:
            print(f"error: unknown rule: {name}", file=sys.stderr)
        return EXIT_ERROR

    config = _load_config(args.config)
    for name in config.rules:
        if name not in RULES_BY_NAME:
            print(f"warning: unknown rule in config: {name}", file=sys.stderr)
    config = _apply_rule_flags(config, args.select, args.ignore_rule)

    results = lint_paths([Path(p) for p in args.paths], config)

    output = "json" if args.json else args.format
    if output == "json":
        _report_errors(results)
        _print_json(results)
    elif output == "github":
        _print_github(results)
    else:
        _report_errors(results)
        _print_text(results, args.quiet)

    if error_count(results):
        return EXIT_ERROR
    return EXIT_FINDINGS if violation_count(results) else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
