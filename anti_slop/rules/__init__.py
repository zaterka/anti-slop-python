"""Rules package: one module per anti-slop rule, plus a lazy registry.

``ALL_RULES`` and ``RULES_BY_NAME`` are materialized on first access (PEP 562)
so that importing a single rule module never pulls in its siblings — tests and
vendored copies can load any subset of the rules independently.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from anti_slop.core import Rule

__all__ = ["ALL_RULES", "RULES_BY_NAME"]


# ---------------------------------------------------------------------------
# Lazy factories: one per rule, in canonical order. This order defines the
# ``--list-rules`` output and documentation ordering. Each factory imports its
# rule module on first use, so loading the registry module is cheap.
# ---------------------------------------------------------------------------


def _factory_no_any_parameters() -> "type[Rule]":
    from .no_any_parameters import NoAnyParametersRule

    return NoAnyParametersRule


def _factory_no_any_returns() -> "type[Rule]":
    from .no_any_returns import NoAnyReturnsRule

    return NoAnyReturnsRule


def _factory_no_any_aliases() -> "type[Rule]":
    from .no_any_aliases import NoAnyAliasesRule

    return NoAnyAliasesRule


def _factory_no_object_parameters() -> "type[Rule]":
    from .no_object_parameters import NoObjectParametersRule

    return NoObjectParametersRule


def _factory_no_unsafe_dict_type() -> "type[Rule]":
    from .no_unsafe_dict_type import NoUnsafeDictTypeRule

    return NoUnsafeDictTypeRule


def _factory_no_chained_casts() -> "type[Rule]":
    from .no_chained_casts import NoChainedCastsRule

    return NoChainedCastsRule


def _factory_no_conditional_empty_dict_spread() -> "type[Rule]":
    from .no_conditional_empty_dict_spread import NoConditionalEmptyDictSpreadRule

    return NoConditionalEmptyDictSpreadRule


def _factory_no_module_mocking() -> "type[Rule]":
    from .no_module_mocking import NoModuleMockingRule

    return NoModuleMockingRule


def _factory_no_runtime_isinstance() -> "type[Rule]":
    from .no_runtime_isinstance import NoRuntimeIsinstanceRule

    return NoRuntimeIsinstanceRule


def _factory_no_dynamic_getattr() -> "type[Rule]":
    from .no_dynamic_getattr import NoDynamicGetattrRule

    return NoDynamicGetattrRule


def _factory_no_dynamic_dispatch() -> "type[Rule]":
    from .no_dynamic_dispatch import NoDynamicDispatchRule

    return NoDynamicDispatchRule


def _factory_no_shape_in_symbol_names() -> "type[Rule]":
    from .no_shape_in_symbol_names import NoShapeInSymbolNamesRule

    return NoShapeInSymbolNamesRule


def _factory_no_known_value_widening() -> "type[Rule]":
    from .no_known_value_widening import NoKnownValueWideningRule

    return NoKnownValueWideningRule


def _factory_no_widen_then_assert() -> "type[Rule]":
    from .no_widen_then_assert import NoWidenThenAssertRule

    return NoWidenThenAssertRule


def _factory_require_safety_comment_for_cast() -> "type[Rule]":
    from .require_safety_comment_for_cast import RequireSafetyCommentForCastRule

    return RequireSafetyCommentForCastRule


_RULE_FACTORIES: tuple[Callable[[], "type[Rule]"], ...] = (
    _factory_no_any_parameters,
    _factory_no_any_returns,
    _factory_no_any_aliases,
    _factory_no_object_parameters,
    _factory_no_unsafe_dict_type,
    _factory_no_chained_casts,
    _factory_no_conditional_empty_dict_spread,
    _factory_no_module_mocking,
    _factory_no_runtime_isinstance,
    _factory_no_dynamic_getattr,
    _factory_no_dynamic_dispatch,
    _factory_no_shape_in_symbol_names,
    _factory_no_known_value_widening,
    _factory_no_widen_then_assert,
    _factory_require_safety_comment_for_cast,
)

_CACHE_RULES: list[Rule] | None = None
_CACHE_BY_NAME: dict[str, Rule] | None = None


def _build_registry() -> tuple[list[Rule], dict[str, Rule]]:
    global _CACHE_RULES, _CACHE_BY_NAME
    if _CACHE_RULES is None:
        _CACHE_RULES = [factory()() for factory in _RULE_FACTORIES]
        _CACHE_BY_NAME = {rule.name: rule for rule in _CACHE_RULES}
    assert _CACHE_BY_NAME is not None
    return _CACHE_RULES, _CACHE_BY_NAME


def __getattr__(name: str):
    if name == "ALL_RULES":
        return _build_registry()[0]
    if name == "RULES_BY_NAME":
        return _build_registry()[1]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
