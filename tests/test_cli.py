"""Tests for the command-line interface: exit codes and output formats.

The exit code is the contract CI depends on, so each one is pinned here:
``0`` clean, ``1`` findings, ``2`` the run itself failed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from anti_slop.cli import EXIT_ERROR, EXIT_FINDINGS, EXIT_OK, main

SLOPPY = "from typing import Any\ndef f(x: Any) -> None:\n    pass\n"
CLEAN = "def f(x: str) -> None:\n    pass\n"


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A project directory with an empty anti-slop config, as the cwd."""
    (tmp_path / "anti-slop.toml").write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _write(root: Path, relative: str, text: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_clean_run_exits_zero(project: Path) -> None:
    _write(project, "app.py", CLEAN)
    assert main([str(project)]) == EXIT_OK


def test_findings_exit_one(project: Path) -> None:
    _write(project, "app.py", SLOPPY)
    assert main([str(project)]) == EXIT_FINDINGS


def test_syntax_error_exits_two_not_zero(project: Path) -> None:
    """A file the linter could not parse is not a file that passed."""
    _write(project, "broken.py", "def broken(\n")
    assert main([str(project)]) == EXIT_ERROR


def test_unreadable_file_exits_two(project: Path) -> None:
    (project / "binary.py").write_bytes(b"\xff\xfe\x00")
    assert main([str(project)]) == EXIT_ERROR


def test_errors_outrank_findings_in_the_exit_code(project: Path) -> None:
    _write(project, "app.py", SLOPPY)
    _write(project, "broken.py", "def broken(\n")
    assert main([str(project)]) == EXIT_ERROR


def test_missing_config_exits_two(project: Path) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--config", str(project / "nope.toml"), str(project)])
    assert excinfo.value.code == EXIT_ERROR


def test_unknown_rule_flag_exits_two(project: Path) -> None:
    _write(project, "app.py", CLEAN)
    assert main(["--select", "no-such-rule", str(project)]) == EXIT_ERROR


def test_list_rules_exits_zero_and_prints_every_rule(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from anti_slop.rules import ALL_RULES

    assert main(["--list-rules"]) == EXIT_OK
    out = capsys.readouterr().out
    for rule in ALL_RULES:
        assert rule.name in out


def test_select_runs_only_the_named_rule(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(project, "app.py", SLOPPY + "import datetime\nd = datetime.datetime.utcnow()\n")

    assert main(["--select", "no-utcnow", str(project)]) == EXIT_FINDINGS
    out = capsys.readouterr().out
    assert "no-utcnow" in out
    assert "no-any-parameters" not in out


def test_ignore_rule_disables_it(project: Path) -> None:
    _write(project, "app.py", SLOPPY)
    assert main(["--ignore-rule", "no-any-parameters", str(project)]) == EXIT_OK


def test_inline_suppression_clears_the_finding(project: Path) -> None:
    _write(
        project,
        "app.py",
        "from typing import Any\n"
        "def f(x: Any) -> None:  # anti-slop: ignore[no-any-parameters]\n"
        "    pass\n",
    )
    assert main([str(project)]) == EXIT_OK


def test_json_output_reports_violations_and_errors(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(project, "app.py", SLOPPY)
    _write(project, "broken.py", "def broken(\n")

    assert main(["--format", "json", str(project)]) == EXIT_ERROR
    payload = json.loads(capsys.readouterr().out)

    assert len(payload["violations"]) == 1
    assert payload["violations"][0]["rule"] == "anti-slop/no-any-parameters"
    assert payload["violations"][0]["column"] == 10  # 1-based for humans
    assert len(payload["errors"]) == 1
    assert "broken.py" in payload["errors"][0]["file"]


def test_json_flag_is_an_alias_for_the_format(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(project, "app.py", SLOPPY)
    assert main(["--json", str(project)]) == EXIT_FINDINGS
    assert "violations" in json.loads(capsys.readouterr().out)


def test_github_format_emits_workspace_relative_annotations(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """GitHub drops annotations whose path it cannot place in the workspace."""
    _write(project, "src/app.py", SLOPPY)

    assert main(["--format", "github", "src"]) == EXIT_FINDINGS
    out = capsys.readouterr().out.strip()

    assert out.startswith("::error ")
    assert "file=src/app.py" in out
    assert "line=2" in out
    assert "title=anti-slop/no-any-parameters" in out
    assert not Path(out.split("file=")[1].split(",")[0]).is_absolute()


def test_github_format_annotates_unparseable_files(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(project, "broken.py", "def broken(\n")

    assert main(["--format", "github", "."]) == EXIT_ERROR
    assert "::error file=broken.py,title=anti-slop::" in capsys.readouterr().out


def test_github_annotation_escapes_newlines(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A raw newline would terminate the workflow command early."""
    from anti_slop.cli import _escape_annotation

    assert _escape_annotation("a\nb") == "a%0Ab"
    assert _escape_annotation("100%") == "100%25"


def test_quiet_suppresses_the_summary_but_not_the_findings(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(project, "app.py", SLOPPY)

    assert main(["--quiet", str(project)]) == EXIT_FINDINGS
    out = capsys.readouterr().out
    assert "no-any-parameters" in out
    assert "problem(s)" not in out
