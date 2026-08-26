# Repository guidance

- `anti_slop/` is the canonical implementation; `tests/` mirrors it one test file per rule.
- Keep rules generic and suitable for reuse across repositories. Do not add application-specific names, paths, or exceptions.
- Use the Python `ast` module; do not add another production parser or any runtime dependency.
- Shared annotation/binding/scope helpers live in `anti_slop/shared/`; rules compose them and keep their own traversal.
- Add focused RuleTester coverage (valid + invalid cases with exact counts) for semantic rule changes.
- `anti_slop/rules/__init__.py` is the canonical rule registry; new rules must be added to `_RULE_FACTORIES` there.
- Rule `name` attributes (`"anti-slop/<rule>"`) and message wording are stable contracts used by configuration; change them deliberately.
- Rules are enabled by default. An opinionated rule that would fight a mainstream Python convention sets `default_enabled = False` (opt-in); the engine honors it via `Config.is_enabled`. Document the rationale in the rule module docstring and add a test asserting `default_enabled is False`.
- A rule that carves out a known false positive documents the carve-out in its module docstring and pins it with a `valid` case. Prefer an exemption over a rule people will switch off.
- Rule options are declared in `default_options` and merged by the engine; read them from `ctx.options`. Test them with `RuleTester(Rule(), options={...})`, not a subclass double.
- Non-rule behavior has its own tests: `test_engine.py` (discovery, ignore/exclude matching, contained rule crashes), `test_cli.py` (exit codes, output formats), `test_suppressions.py`. Exit codes are a CI contract — `0` clean, `1` findings, `2` the run failed — so changes there need a test.
- `action.yml` is the published GitHub Action. Its exit-code handling must treat any status other than `0` and `1` as a failure; a broken run must never report as a passing check.
- Run `.venv/bin/python -m pytest` and `.venv/bin/python -m anti_slop anti_slop tests skills` before committing. The tool passes its own ruleset; keep it that way with `exclude` or an inline `# anti-slop: ignore[...]` carrying a reason, not a blanket `enabled = false`.
