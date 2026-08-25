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


def _factory_no_swallowed_exceptions() -> "type[Rule]":
    from .no_swallowed_exceptions import NoSwallowedExceptionsRule

    return NoSwallowedExceptionsRule


def _factory_no_debug_prints() -> "type[Rule]":
    from .no_debug_prints import NoDebugPrintsRule

    return NoDebugPrintsRule


def _factory_no_fstring_logging() -> "type[Rule]":
    from .no_fstring_logging import NoFstringLoggingRule

    return NoFstringLoggingRule


def _factory_no_mutable_defaults() -> "type[Rule]":
    from .no_mutable_defaults import NoMutableDefaultsRule

    return NoMutableDefaultsRule


def _factory_no_eval_exec() -> "type[Rule]":
    from .no_eval_exec import NoEvalExecRule

    return NoEvalExecRule


def _factory_no_utcnow() -> "type[Rule]":
    from .no_utcnow import NoUtcnowRule

    return NoUtcnowRule


def _factory_no_trivial_asserts() -> "type[Rule]":
    from .no_trivial_asserts import NoTrivialAssertsRule

    return NoTrivialAssertsRule


def _factory_no_async_without_await() -> "type[Rule]":
    from .no_async_without_await import NoAsyncWithoutAwaitRule

    return NoAsyncWithoutAwaitRule


def _factory_no_blocking_sleep_in_async() -> "type[Rule]":
    from .no_blocking_sleep_in_async import NoBlockingSleepInAsyncRule

    return NoBlockingSleepInAsyncRule


def _factory_no_dataclass_mutable_defaults() -> "type[Rule]":
    from .no_dataclass_mutable_defaults import NoDataclassMutableDefaultsRule

    return NoDataclassMutableDefaultsRule


def _factory_no_numbered_symbol_names() -> "type[Rule]":
    from .no_numbered_symbol_names import NoNumberedSymbolNamesRule

    return NoNumberedSymbolNamesRule


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
    # Python-specific rules (no JS/TS counterpart).
    _factory_no_swallowed_exceptions,
    _factory_no_debug_prints,
    _factory_no_fstring_logging,
    _factory_no_mutable_defaults,
    _factory_no_eval_exec,
    _factory_no_utcnow,
    _factory_no_trivial_asserts,
    _factory_no_async_without_await,
    _factory_no_blocking_sleep_in_async,
    _factory_no_dataclass_mutable_defaults,
    _factory_no_numbered_symbol_names,
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
