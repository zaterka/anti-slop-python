"""Tests for configuration and rule enablement.

Pins the opt-in mechanism: rules with ``default_enabled = False`` are
inactive unless the configuration explicitly enables them, and
``Config.is_enabled`` falls back to the caller-supplied default when the
rule is not mentioned.
"""

from anti_slop.config import Config
from anti_slop.engine import active_rules
from anti_slop.rules import ALL_RULES, RULES_BY_NAME


def _rule(name: str):
    return RULES_BY_NAME[name]


def test_is_enabled_defaults_to_true() -> None:
    config = Config()
    assert config.is_enabled("anti-slop/no-any-returns") is True


def test_is_enabled_respects_explicit_enabled() -> None:
    config = Config(rules={"anti-slop/no-any-returns": {"enabled": False}})
    assert config.is_enabled("anti-slop/no-any-returns") is False


def test_parse_config_file_normalizes_bool_entries(tmp_path) -> None:
    # ``[tool.anti-slop.rules."<name>"] enabled = false`` arrives as a bool
    # in the raw TOML and is normalized to the option-dict form.
    from anti_slop.config import parse_config_file

    toml = (
        "[tool.anti-slop]\n"
        "[tool.anti-slop.rules.\"anti-slop/no-any-returns\"]\n"
        "enabled = false\n"
    )
    path = tmp_path / "pyproject.toml"
    path.write_text(toml, encoding="utf-8")
    config = parse_config_file(path)
    assert config.is_enabled("anti-slop/no-any-returns") is False


def test_is_enabled_honors_default_for_unmentioned_rules() -> None:
    config = Config()
    assert config.is_enabled("anti-slop/no-shape-in-symbol-names", False) is False


def test_explicit_enable_overrides_opt_in_default() -> None:
    config = Config(
        rules={"anti-slop/no-shape-in-symbol-names": {"enabled": True}}
    )
    assert config.is_enabled("anti-slop/no-shape-in-symbol-names", False) is True


def test_opt_in_rules_are_off_by_default() -> None:
    config = Config()
    active = {rule.name for rule, _ in active_rules(config)}
    for rule in ALL_RULES:
        if rule.default_enabled:
            assert rule.name in active
        else:
            assert rule.name not in active


def test_opt_in_rule_can_be_turned_on() -> None:
    config = Config(
        rules={"anti-slop/no-numbered-symbol-names": {"enabled": True}}
    )
    active = {rule.name for rule, _ in active_rules(config)}
    assert "anti-slop/no-numbered-symbol-names" in active


def test_all_rules_have_unique_names_and_documentation() -> None:
    names = [rule.name for rule in ALL_RULES]
    assert len(names) == len(set(names))
    for rule in ALL_RULES:
        assert rule.name.startswith("anti-slop/")
        assert rule.description
        assert rule.messages
