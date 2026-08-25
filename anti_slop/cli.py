"""Command-line interface for anti-slop.

Usage::

    anti-slop [paths...]            # lint files or directories (default: .)
    anti-slop --list-rules          # show every rule and its description
    anti-slop --json                # machine-readable output
    anti-slop --config FILE         # use an explicit config file
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .config import Config, find_config, parse_config_file
from .engine import LintResult, lint_paths
from .rules import ALL_RULES, RULES_BY_NAME

__all__ = ["main", "build_parser"]


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
        "--json",
        action="store_true",
        help="print results as a JSON array instead of text",
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


def _load_config(explicit: str | None) -> Config:
    if explicit:
        path = Path(explicit)
        if not path.is_file():
            print(f"error: config file not found: {path}", file=sys.stderr)
            raise SystemExit(2)
        return parse_config_file(path)
    return find_config(Path.cwd())


def _validate_selected(config: Config) -> list[str]:
    """Return unknown rule names referenced by the configuration."""
    return [name for name in config.rules if name not in RULES_BY_NAME]


def _print_text(results: list[LintResult], quiet: bool) -> int:
    total = 0
    files_with_findings = 0
    for result in results:
        if result.error:
            print(f"{result.path}: {result.error}", file=sys.stderr)
        if not result.violations:
            continue
        files_with_findings += 1
        for violation in result.violations:
            print(
                f"{result.path}:{violation.location()}: {violation.rule} "
                f"{violation.message}"
            )
            total += 1
    if not quiet:
        if total:
            print(f"\n{total} problem(s) in {files_with_findings} file(s).")
        else:
            print("\nNo problems found.")
    return 1 if total else 0


def _print_json(results: list[LintResult]) -> int:
    payload = []
    for result in results:
        if result.error:
            print(f"{result.path}: {result.error}", file=sys.stderr)
        for violation in result.violations:
            payload.append(
                {
                    "file": str(result.path),
                    "line": violation.line,
                    "column": violation.column + 1,
                    "rule": violation.rule,
                    "message": violation.message,
                }
            )
    print(json.dumps(payload, indent=2))
    return 1 if payload else 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_rules:
        for rule in ALL_RULES:
            print(f"{rule.name}")
            print(f"    {rule.description}")
        return 0

    config = _load_config(args.config)
    unknown = _validate_selected(config)
    if unknown:
        for name in unknown:
            print(
                f"warning: unknown rule in config: {name}",
                file=sys.stderr,
            )

    results = lint_paths([Path(p) for p in args.paths], config)
    if args.json:
        return _print_json(results)
    return _print_text(results, args.quiet)


if __name__ == "__main__":
    sys.exit(main())
