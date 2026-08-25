"""Tests for ``anti-slop/no-eval-exec``."""

from anti_slop.rules.no_eval_exec import NoEvalExecRule

from tests.harness import RuleTester


def test_no_eval_exec() -> None:
    RuleTester(NoEvalExecRule()).run(
        "anti-slop/no-eval-exec",
        valid=[
            # The documented fix: parse, don't execute.
            "import json\n"
            "data = json.loads(raw)",
            "import ast\n"
            "value = ast.literal_eval(raw)",
            # Dotted access is not the builtin.
            "obj.eval('x')",
            # Shadowed builtin.
            "eval = safe_eval\n"
            "value = eval(raw)",
            "from tools import exec\n"
            "exec(block)",
        ],
        invalid=[
            {"code": "value = eval(expr)", "count": 1},
            {"code": "exec(code)", "count": 1},
            {"code": "x = eval(expr)\nexec(code)", "count": 2},
        ],
    )
