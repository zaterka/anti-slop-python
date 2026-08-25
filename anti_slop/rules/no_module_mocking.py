"""``no-module-mocking``: ban test-framework module/attribute mocking.

Port of ``anti-slop/no-module-mocking``. ``mock.patch`` (and friends) and
``monkeypatch.setattr`` replace real dependencies with fakes behind the
system's back; tests should replace dependencies through real interfaces —
dependency injection, a service layer, or a faithful test implementation.
"""

from __future__ import annotations

import ast

from anti_slop.core import FileContext, Rule

from ..shared.type_utils import assigned_names, dotted_name, import_map

__all__ = ["NoModuleMockingRule"]

_PATCH_METHODS = {"patch", "patch.object", "patch.dict", "patch.multiple"}


class NoModuleMockingRule(Rule):
    """Disallow test framework module and attribute mocking."""

    name = "anti-slop/no-module-mocking"
    description = (
        "Disallow test framework module and attribute mocking; tests must "
        "replace dependencies through real interfaces."
    )
    messages = {
        "moduleMock": (
            "Replace module mocking with dependency injection through a real "
            "interface, service layer, or faithful test implementation."
        ),
    }

    def check(self, ctx: FileContext):
        tree = ctx.tree
        imports = import_map(tree)
        assigned = assigned_names(tree)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = dotted_name(node.func)
            if name is None:
                continue
            if self._is_mocking_call(name, imports, assigned):
                yield self.report(ctx, node, "moduleMock")

    @staticmethod
    def _is_mocking_call(
        name: str,
        imports: dict[str, str],
        assigned: set[str],
    ) -> bool:
        # Bare `patch` / `patch.object` / `patch.dict` / `patch.multiple`:
        # only the bare name can be imported directly
        # (`from unittest.mock import patch`); a local `patch` def shadows.
        if name in _PATCH_METHODS and name.split(".")[0] == "patch":
            return imports.get("patch") == "unittest.mock" and "patch" not in assigned
        if name.startswith("unittest.mock.") and name[len("unittest.mock.") :] in _PATCH_METHODS:
            # `import unittest` / `import unittest.mock`
            return imports.get("unittest") in {"unittest", "unittest.mock"}
        if name.startswith("mock.") and name[len("mock.") :] in _PATCH_METHODS:
            # `from unittest import mock` (a local `mock` def shadows)
            return (
                imports.get("mock") in {"unittest", "unittest.mock"}
                and "mock" not in assigned
            )
        # pytest-mock fixture: mocker.patch / .object / .dict / .multiple
        if name.startswith("mocker.") and name[len("mocker.") :] in _PATCH_METHODS:
            return "mocker" not in assigned
        # pytest monkeypatch fixture: attribute/dict-item replacement
        # (setenv/chdir are environment helpers, not dependency seams)
        if name in {
            "monkeypatch.setattr",
            "monkeypatch.delattr",
            "monkeypatch.setitem",
            "monkeypatch.delitem",
        }:
            return "monkeypatch" not in assigned
        return False
