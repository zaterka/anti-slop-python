"""Project configuration for anti-slop.

Configuration lives in a project's ``pyproject.toml`` under the
``[tool.anti-slop]`` table (or a standalone ``anti-slop.toml``). The schema is
intentionally small::

    [tool.anti-slop]
    ignore = ["vendor/**", "generated/**"]

    [tool.anti-slop.rules."anti-slop/no-runtime-isinstance"]
    enabled = true
    allow_in_type_guards = true

Every rule is enabled by default; configuration only disables rules or sets
per-rule options. Option keys other than ``enabled`` are passed straight through
to the rule in :attr:`FileContext.options`.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["Config", "find_config", "parse_config_file"]

_CONFIG_KEY = "anti-slop"
_STANDALONE_NAMES = ("anti-slop.toml", ".anti-slop.toml")


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

    def is_enabled(self, rule_name: str) -> bool:
        opts = self.rules.get(rule_name)
        if opts is None:
            return True
        return bool(opts.get("enabled", True))

    def options_for(self, rule_name: str) -> dict:
        opts = self.rules.get(rule_name)
        if opts is None:
            return {}
        return {k: v for k, v in opts.items() if k != "enabled"}


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

    return Config(ignore=ignore, rules=rules, source=path)


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
