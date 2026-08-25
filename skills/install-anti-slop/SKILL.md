---
name: install-anti-slop
description: Install anti-slop-python into the current repository. Copies the anti_slop package into tools/anti_slop/, merges a [tool.anti-slop] configuration section into pyproject.toml, and validates the result by linting a sample file. Use when the user asks to install, set up, or configure anti-slop for a Python project.
---

# Install anti-slop

anti-slop is a zero-dependency, AST-based linter for Python that enforces
concrete typing contracts. It is **vendored**: the package is copied into the
target repository, after which the vendored files belong to that repository
(adjust or extend the rules freely).

## Run the installer

```bash
python skills/install-anti-slop/scripts/install.py --repo <target-repo-root>
```

Omit `--repo` to install into the current working directory. The script:

1. Copies `anti_slop/` to `tools/anti_slop/` in the target repository
   (refuses to overwrite an existing destination without `--force`).
2. Merges a `[tool.anti-slop]` section into the target's `pyproject.toml`
   (creates the file if missing; leaves an existing section untouched).
3. Validates the result by running the vendored CLI against a deliberately
   sloppy sample file and confirming findings are reported.

To replace an existing vendored copy: `--force`. To install the package
somewhere other than `tools/anti_slop`: `--dest <path>`.

## After installation

The vendored CLI is not installed as a console script. Run it with the
package directory on the Python path, for example:

```bash
PYTHONPATH=tools python -m anti_slop .
```

or add it to the repository's tooling (Makefile, justfile, package script):

```
lint-slop:
    PYTHONPATH=tools python -m anti_slop .
```

The exit code is `1` when any rule reports a finding, so the command plugs
directly into CI.

## Configuring rules

Configuration lives under `[tool.anti-slop]` in `pyproject.toml` (or in a
standalone `anti-slop.toml` in the repository root). Every rule is enabled by
default; disable or tune one by name:

```toml
[tool.anti-slop]
ignore = ["tests/fixtures/**"]

[tool.anti-slop.rules."anti-slop/no-runtime-isinstance"]
enabled = false
```

List the bundled rules with `PYTHONPATH=tools python -m anti_slop --list-rules`.
