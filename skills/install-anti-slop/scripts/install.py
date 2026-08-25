#!/usr/bin/env python3
"""Install the anti-slop package into a target repository.

Usage::

    python install.py [--repo PATH] [--dest RELPATH] [--force] [--no-validate]

Steps:
1. Copy the ``anti_slop`` package next to this skill's repository root into
   ``<repo>/<dest>`` (default ``tools/anti_slop``).
2. Ensure a ``[tool.anti-slop]`` section exists in ``<repo>/pyproject.toml``
   (creates the file if missing; never rewrites an existing section).
3. Validate by linting a deliberately sloppy sample with the vendored CLI.

Exit codes: 0 success, 1 validation failure, 2 usage/setup error.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

# skills/install-anti-slop/scripts/install.py -> repo root is three levels up.
SOURCE_PACKAGE = Path(__file__).resolve().parents[3] / "anti_slop"

_CONFIG_SECTION = """\

[tool.anti-slop]
# Every bundled rule is enabled by default. To disable or tune a rule, add a
# table keyed by its full name, for example:
#
# [tool.anti-slop.rules."anti-slop/no-runtime-isinstance"]
# enabled = false
"""

_SAMPLE = (
    "from typing import Any\n"
    "def f(x: Any) -> None:\n"
    "    pass\n"
)


def _fail(message: str, code: int = 2) -> None:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(code)


def _copy_package(repo: Path, dest: Path, force: bool) -> None:
    if not SOURCE_PACKAGE.is_dir():
        _fail(f"source package not found at {SOURCE_PACKAGE}")
    if dest.exists():
        if not force:
            _fail(
                f"{dest} already exists; pass --force to replace it"
            )
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SOURCE_PACKAGE, dest, ignore=shutil.ignore_patterns(
        "__pycache__", "*.py[cod]",
    ))
    print(f"copied {SOURCE_PACKAGE.name} -> {dest}")


def _merge_config(repo: Path) -> None:
    pyproject = repo / "pyproject.toml"
    if pyproject.is_file():
        try:
            with pyproject.open("rb") as handle:
                data = tomllib.load(handle)
        except tomllib.TOMLDecodeError as exc:
            _fail(f"could not parse {pyproject}: {exc}")
        if "anti-slop" in data.get("tool", {}):
            print(f"kept existing [tool.anti-slop] section in {pyproject}")
            return
        with pyproject.open("a", encoding="utf-8") as handle:
            handle.write(_CONFIG_SECTION)
        print(f"appended [tool.anti-slop] to {pyproject}")
        return
    pyproject.write_text(_CONFIG_SECTION.lstrip("\n"), encoding="utf-8")
    print(f"created {pyproject} with [tool.anti-slop]")


def _validate(repo: Path, dest: Path) -> None:
    dest_parent = str(dest.parent.resolve())
    sample = repo / ".anti-slop-sample.py"
    sample.write_text(_SAMPLE, encoding="utf-8")
    try:
        code = (
            "import sys\n"
            f"sys.path.insert(0, {dest_parent!r})\n"
            "from anti_slop.cli import main\n"
            f"raise SystemExit(main([{str(sample)!r}]))\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
        )
        if proc.stdout:
            print(proc.stdout.rstrip())
        if proc.returncode != 1:
            _fail(
                f"expected the sample file to produce findings "
                f"(exit code 1), got {proc.returncode}: {proc.stderr}",
                code=1,
            )
        print("validation: sample file produced findings as expected")
    finally:
        sample.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        default=".",
        help="target repository root (default: current directory)",
    )
    parser.add_argument(
        "--dest",
        default="tools/anti_slop",
        help="package destination, relative to the repo root "
        "(default: tools/anti_slop)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace an existing destination directory",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="skip the sample-file validation step",
    )
    args = parser.parse_args(argv)

    repo = Path(args.repo).expanduser().resolve()
    if not repo.is_dir():
        _fail(f"repo root not found: {repo}")
    dest = (repo / args.dest).resolve()

    _copy_package(repo, dest, args.force)
    _merge_config(repo)
    if not args.no_validate:
        _validate(repo, dest)
    print("anti-slop installed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
