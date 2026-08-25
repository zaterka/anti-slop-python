"""Tests for ``anti-slop/no-debug-prints``."""

from anti_slop.rules.no_debug_prints import NoDebugPrintsRule

from tests.harness import RuleTester


def test_no_debug_prints() -> None:
    RuleTester(NoDebugPrintsRule()).run(
        "anti-slop/no-debug-prints",
        valid=[
            # Inside the __main__ guard: the script's entry point.
            'if __name__ == "__main__":\n    print("done")',
            # __name__ guard written the other way round.
            'if "__main__" == __name__:\n    print("done")',
            # Nested under the guard.
            'if __name__ == "__main__":\n'
            "    for line in lines:\n"
            '        print(line)',
            # A function defined under the guard only runs as a script.
            'if __name__ == "__main__":\n'
            "    def go():\n"
            '        print("go")\n'
            "    go()",
            # Not a print.
            "logger.info('done')",
            "def my_print(x):\n    pass",
            # Shadowed builtin.
            "print = logging.info\nprint('done')",
        ],
        invalid=[
            {"code": 'print("debug")', "count": 1},
            {"code": 'print(f"state={state}")', "count": 1},
            # Module-level function: application code even if the guard calls it.
            {
                "code": (
                    "def main():\n"
                    '    print("starting")\n'
                    'if __name__ == "__main__":\n'
                    "    main()"
                ),
                "count": 1,
            },
            # Guard on a different condition does not exempt.
            {
                "code": 'if __name__ == "cli":\n    print("x")',
                "count": 1,
            },
            {
                "code": 'print(a)\nprint(b)',
                "count": 2,
            },
        ],
    )
