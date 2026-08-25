# Repository guidance

- `anti_slop/` is the canonical implementation; `tests/` mirrors it one test file per rule.
- Keep rules generic and suitable for reuse across repositories. Do not add application-specific names, paths, or exceptions.
- Use the Python `ast` module; do not add another production parser or any runtime dependency.
- Shared annotation/binding/scope helpers live in `anti_slop/shared/`; rules compose them and keep their own traversal.
- Add focused RuleTester coverage (valid + invalid cases with exact counts) for semantic rule changes.
- `anti_slop/rules/__init__.py` is the canonical rule registry; new rules must be added to `_RULE_FACTORIES` there.
- Rule `name` attributes (`"anti-slop/<rule>"`) and message wording are stable contracts used by configuration; change them deliberately.
- Rules are enabled by default. An opinionated rule that would fight a mainstream Python convention sets `default_enabled = False` (opt-in); the engine honors it via `Config.is_enabled`. Document the rationale in the rule module docstring and add a test asserting `default_enabled is False`.
- Run `.venv/bin/python -m pytest` before committing.
