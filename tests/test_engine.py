"""Tests for the engine: file discovery, ignore matching, and error handling.

These cover the parts of a lint run that are not any single rule's behavior —
which files get looked at, which rules apply to them, and what happens when a
file cannot be read at all.
"""

from __future__ import annotations

from pathlib import Path

from anti_slop.config import Config
from anti_slop.engine import (
    active_rules,
    error_count,
    iter_python_files,
    lint_file,
    lint_paths,
    violation_count,
)

SLOPPY = "from typing import Any\ndef f(x: Any) -> None:\n    pass\n"


def _write(root: Path, relative: str, text: str = SLOPPY) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_discovery_skips_caches_and_vcs_directories(tmp_path: Path) -> None:
    _write(tmp_path, "src/app.py")
    _write(tmp_path, "__pycache__/app.py")
    _write(tmp_path, ".venv/lib/app.py")
    _write(tmp_path, "node_modules/app.py")

    found = {p.name for p in iter_python_files([tmp_path], [], tmp_path)}
    assert found == {"app.py"}
    assert len(list(iter_python_files([tmp_path], [], tmp_path))) == 1


def test_discovery_ignores_non_python_and_deduplicates(tmp_path: Path) -> None:
    app = _write(tmp_path, "src/app.py")
    _write(tmp_path, "src/notes.txt", "not python")

    found = list(iter_python_files([app, tmp_path, app], [], tmp_path))
    assert found == [app] or found == [app.resolve()]
    assert len(found) == 1


def test_ignore_globs_anchor_to_the_config_directory(tmp_path: Path) -> None:
    """The same pattern must hold however the linter is pointed at the tree.

    Anchoring to the walked path instead would make `anti-slop generated/`
    quietly lint what `anti-slop .` ignores.
    """
    _write(tmp_path, "generated/models.py")
    _write(tmp_path, "src/app.py")
    ignore = ["generated/**"]

    from_root = {p.name for p in iter_python_files([tmp_path], ignore, tmp_path)}
    assert from_root == {"app.py"}

    from_subdir = list(
        iter_python_files([tmp_path / "generated"], ignore, tmp_path)
    )
    assert from_subdir == []


def test_explicit_file_arguments_bypass_ignore_globs(tmp_path: Path) -> None:
    generated = _write(tmp_path, "generated/models.py")
    found = list(iter_python_files([generated], ["generated/**"], tmp_path))
    assert found == [generated]


def test_unreadable_file_is_an_error_not_a_pass(tmp_path: Path) -> None:
    path = tmp_path / "binary.py"
    path.write_bytes(b"\xff\xfe\x00")
    result = lint_file(path, active_rules(Config()), tmp_path)
    assert result.error is not None
    assert not result.ok
    assert result.violations == []


def test_syntax_error_is_an_error_not_a_pass(tmp_path: Path) -> None:
    path = _write(tmp_path, "broken.py", "def broken(\n")
    result = lint_file(path, active_rules(Config()), tmp_path)
    assert result.error is not None
    assert "syntax error" in result.error
    assert not result.ok


def test_error_count_separates_failures_from_findings(tmp_path: Path) -> None:
    _write(tmp_path, "broken.py", "def broken(\n")
    _write(tmp_path, "sloppy.py")
    results = lint_paths([tmp_path], Config(root=tmp_path))

    assert error_count(results) == 1
    assert violation_count(results) == 1


def test_per_rule_exclude_scopes_a_rule_off_a_path(tmp_path: Path) -> None:
    _write(tmp_path, "src/app.py")
    _write(tmp_path, "tests/test_app.py")
    config = Config(
        rules={"anti-slop/no-any-parameters": {"exclude": ["tests/**"]}},
        root=tmp_path,
    )

    results = lint_paths([tmp_path], config)
    flagged = {
        Path(r.path).name for r in results if r.violations
    }
    assert flagged == {"app.py"}


def test_exclude_is_not_forwarded_to_the_rule_as_an_option() -> None:
    config = Config(
        rules={"anti-slop/no-any-parameters": {"exclude": ["tests/**"]}}
    )
    assert "exclude" not in config.options_for("anti-slop/no-any-parameters")
    assert config.exclude_for("anti-slop/no-any-parameters") == ["tests/**"]


def test_rule_defaults_are_merged_into_the_context_options() -> None:
    entries = {entry.rule.name: entry for entry in active_rules(Config())}
    entry = entries["anti-slop/no-any-parameters"]
    assert entry.options["allow_varargs"] is True


def test_a_crashing_rule_is_contained_and_reported(tmp_path: Path) -> None:
    from anti_slop.core import Rule
    from anti_slop.engine import ActiveRule

    class Exploding(Rule):
        name = "anti-slop/exploding"
        description = "test double"

        def check(self, ctx):
            raise RuntimeError("boom")
            yield  # pragma: no cover - unreachable, makes this a generator

    path = _write(tmp_path, "app.py")
    result = lint_file(path, [ActiveRule(rule=Exploding(), options={})], tmp_path)

    assert result.error is not None
    assert "exploding" in result.error


def test_tooling_caches_are_never_walked(tmp_path: Path) -> None:
    """A vendored copy inside a tool cache is not the project's code."""
    _write(tmp_path, "app.py", "def f(x: str) -> None:\n    pass\n")
    for cache in (".uv-cache", ".uv_cache", ".tox", ".hypothesis", ".pytype"):
        _write(tmp_path, f"{cache}/vendored/mod.py")

    found = [p.name for p in iter_python_files([tmp_path], [], tmp_path)]
    assert found == ["app.py"]
