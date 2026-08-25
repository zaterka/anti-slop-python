"""Rules package: one module per anti-slop rule, plus a lazy registry.

``ALL_RULES`` and ``RULES_BY_NAME`` are materialized on first access (PEP 562)
so that importing a single rule module never pulls in its siblings — tests and
vendored copies can load any subset of the rules independently.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from anti_slop.core import Rule

__all__ = ["ALL_RULES", "RULES_BY_NAME"]

# (module name, class name) in canonical order. This order defines the
# ``--list-rules`` output and documentation ordering.
_RULE_FACTORIES: tuple[tuple[str, str], ...] = (
    ("no_any_parameters", "NoAnyParametersRule"),
    ("no_any_returns", "NoAnyReturnsRule"),
    ("no_any_aliases", "NoAnyAliasesRule"),
    ("no_object_parameters", "NoObjectParametersRule"),
    ("no_unsafe_dict_type", "NoUnsafeDictTypeRule"),
    ("no_chained_casts", "NoChainedCastsRule"),
    ("no_conditional_empty_dict_spread", "NoConditionalEmptyDictSpreadRule"),
    ("no_module_mocking", "NoModuleMockingRule"),
    ("no_runtime_isinstance", "NoRuntimeIsinstanceRule"),
    ("no_dynamic_getattr", "NoDynamicGetattrRule"),
    ("no_dynamic_dispatch", "NoDynamicDispatchRule"),
    ("no_shape_in_symbol_names", "NoShapeInSymbolNamesRule"),
    ("no_known_value_widening", "NoKnownValueWideningRule"),
    ("no_widen_then_assert", "NoWidenThenAssertRule"),
    ("require_safety_comment_for_cast", "RequireSafetyCommentForCastRule"),
)

_CACHE: dict[str, object] = {}


def _build_registry() -> dict[str, object]:
    if "ALL_RULES" not in _CACHE:
        rules: list[Rule] = []
        for module_name, class_name in _RULE_FACTORIES:
            module = importlib.import_module(f".{module_name}", __name__)
            rules.append(getattr(module, class_name)())
        _CACHE["ALL_RULES"] = rules
        _CACHE["RULES_BY_NAME"] = {rule.name: rule for rule in rules}
    return _CACHE


def __getattr__(name: str):
    if name in ("ALL_RULES", "RULES_BY_NAME"):
        return _build_registry()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return __all__
