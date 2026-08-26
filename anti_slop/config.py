"""Project configuration for anti-slop.

Configuration lives in a project's ``pyproject.toml`` under the
``[tool.anti-slop]`` table (or a standalone ``anti-slop.toml``). The schema is
intentionally small::

    [tool.anti-slop]
    ignore = ["vendor/**", "generated/**"]

    [tool.anti-slop.rules."anti-slop/no-runtime-isinstance"]
    enabled = true
    allow_in_type_guards = true
    exclude = ["tests/**"]

Rules are enabled by default; opt-in rules (``Rule.default_enabled = False``)
are the exception and must be explicitly enabled. Configuration disables rules,
enables opt-in rules, scopes a rule off certain paths (``exclude``), or sets
per-rule options. Option keys other than ``enabled`` and ``exclude`` are passed
straight through to the rule in :attr:`FileContext.options`.

``ignore`` and ``exclude`` globs are relative to the configuration file's own
directory, so a pattern means the same thing whether you run ``anti-slop .`` or
``anti-slop src/``.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["Config", "find_config", "parse_config_file"]

_CONFIG_KEY = "anti-slop"
_STANDALONE_NAMES = ("anti-slop.toml", ".anti-slop.toml")

# Keys in a rule's table that configure the *engine*, not the rule itself, and
# so are not forwarded to ``FileContext.options``.
_RESERVED_RULE_KEYS = frozenset({"enabled", "exclude"})


@dataclass
class Config:
    """Parsed anti-slop configuration.

    ``rules`` maps a rule name (e.g. ``"anti-slop/no-any-returns"``) to an option
    dict. The dict may contain an ``enabled`` boolean; any other key is a
    per-rule option.
    """

    ignore: list[str] = field(default_factory=list)
    rules: dict[str, dict] = field(default_factory=dict)
    source: Path | None = None
    root: Path | None = None

    def is_enabled(self, rule_name: str, default: bool = True) -> bool:
        """Whether a rule is active in this configuration.

        ``default`` applies when the configuration does not mention the rule
        (the engine passes each rule's ``Rule.default_enabled``; opt-in rules
        are therefore inactive unless explicitly enabled).
        """
        opts = self.rules.get(rule_name)
        if opts is None:
            return default
        return bool(opts.get("enabled", default))

    def options_for(self, rule_name: str) -> dict:
        opts = self.rules.get(rule_name)
        if opts is None:
            return {}
        return {k: v for k, v in opts.items() if k not in _RESERVED_RULE_KEYS}

    def exclude_for(self, rule_name: str) -> list[str]:
        """Path globs on which this specific rule is off.

        Lets a project keep a rule everywhere except where it fights the
        codebase — ``no-debug-prints`` off in ``cli.py``, say — without
        disabling it outright.
        """
        opts = self.rules.get(rule_name)
        if opts is None:
            return []
        return [str(pattern) for pattern in opts.get("exclude", [])]

    def anchor(self) -> Path:
        """The directory ``ignore``/``exclude`` globs are relative to.

        The configuration file's own directory, so a pattern means the same
        thing no matter which path you point the linter at. Falls back to the
        current directory when no configuration file was found.
        """
        if self.root is not None:
            return self.root
        if self.source is not None:
            return self.source.parent
        return Path.cwd()


def _read_toml(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def parse_config_file(path: Path) -> Config:
    """Parse an explicit configuration file (``pyproject.toml`` or ``anti-slop.toml``)."""
    data = _read_toml(path)
    if path.name == "pyproject.toml":
        table = data.get("tool", {}).get(_CONFIG_KEY, {})
    else:
        table = data

    ignore = list(table.get("ignore", []))
    rules: dict[str, dict] = {}
    raw_rules = table.get("rules", {})
    for name, opts in raw_rules.items():
        if isinstance(opts, bool):
            rules[name] = {"enabled": opts}
        elif isinstance(opts, dict):
            rules[name] = dict(opts)

    return Config(
        ignore=ignore,
        rules=rules,
        source=path,
        root=path.resolve().parent,
    )


def find_config(start: Path | None = None) -> Config:
    """Search upward from ``start`` for anti-slop configuration.

    Looks for a standalone ``anti-slop.toml`` / ``.anti-slop.toml`` and a
    ``pyproject.toml`` containing ``[tool.anti-slop]``. The nearest match wins.
    Returns an empty :class:`Config` when nothing is found.
    """
    directory = (start or Path.cwd()).resolve()
    for candidate in [directory, *directory.parents]:
        for name in _STANDALONE_NAMES:
            standalone = candidate / name
            if standalone.is_file():
                return parse_config_file(standalone)

        pyproject = candidate / "pyproject.toml"
        if pyproject.is_file():
            try:
                data = _read_toml(pyproject)
            except (OSError, tomllib.TOMLDecodeError):
                continue
            if "anti-slop" in data.get("tool", {}):
                return parse_config_file(pyproject)

    return Config()
