"""Tests for ``anti-slop/no-module-mocking``."""

from anti_slop.rules.no_module_mocking import NoModuleMockingRule

from tests.harness import RuleTester


def test_no_module_mocking() -> None:
    RuleTester(NoModuleMockingRule()).run(
        "anti-slop/no-module-mocking",
        valid=[
            "from unittest.mock import MagicMock\n"
            "m = MagicMock()",
            # Importing patch without calling it is fine.
            "from unittest.mock import patch\n"
            "def test_f(): pass",
            # Locally shadowed patch.
            "patch = my_own_patch\n"
            "patch('x')",
            "import otherlib\n"
            "otherlib.patch('x')",
            "from mypkg import patch\n"
            "patch('x')",
            # monkeypatch environment helpers are not dependency seams.
            "monkeypatch.setenv('FOO', 'bar')",
            "monkeypatch.chdir('/tmp')",
            # Locally shadowed mocker fixture.
            "mocker = my_fake\n"
            "mocker.patch('x')",
        ],
        invalid=[
            {
                "code": 'from unittest.mock import patch\n'
                "patch('pkg.mod.attr')",
                "count": 1,
            },
            {
                "code": 'import unittest.mock\n'
                "unittest.mock.patch('pkg.mod.attr')",
                "count": 1,
            },
            {
                "code": 'from unittest import mock\n'
                "mock.patch('pkg.mod.attr')",
                "count": 1,
            },
            {
                "code": "from unittest.mock import patch\n"
                'patch.object(Owner, "method")',
                "count": 1,
            },
            {
                "code": 'from unittest.mock import patch\n'
                'patch.dict(os.environ, {"A": "B"})',
                "count": 1,
            },
            {
                "code": "mocker.patch('pkg.mod.attr')",
                "count": 1,
            },
            {
                "code": "monkeypatch.setattr(Owner, 'method', fake)",
                "count": 1,
            },
            {
                "code": "monkeypatch.delattr(Owner, 'method')",
                "count": 1,
            },
            {
                "code": 'from unittest.mock import patch\n'
                '@patch("pkg.mod.attr")\n'
                "def f(): pass",
                "count": 1,
            },
            {
                "code": 'from unittest.mock import patch\n'
                "patch('a.b')\n"
                "patch('c.d')",
                "count": 2,
            },
        ],
    )
