"""Tests for ``anti-slop/no-swallowed-exceptions``."""

from anti_slop.rules.no_swallowed_exceptions import NoSwallowedExceptionsRule

from tests.harness import RuleTester


def test_no_swallowed_exceptions() -> None:
    RuleTester(NoSwallowedExceptionsRule()).run(
        "anti-slop/no-swallowed-exceptions",
        valid=[
            # Specific exception treated as "not an error": a decision.
            "try:\n"
            "    row = parse(line)\n"
            "except ValueError:\n"
            "    pass",
            # Broad handler that does something with the failure.
            "try:\n"
            "    f()\n"
            "except Exception as exc:\n"
            "    log.exception(exc)",
            # Re-raising is not swallowing.
            "try:\n"
            "    f()\n"
            "except Exception:\n"
            "    raise",
            "try:\n"
            "    f()\n"
            "except Exception as exc:\n"
            "    raise SystemExit(1) from exc",
            # Handler with a real body.
            "try:\n"
            "    f()\n"
            "except Exception:\n"
            "    fallback()\n"
            "    cleanup()",
        ],
        invalid=[
            {
                "code": "try:\n    f()\nexcept Exception:\n    pass",
                "count": 1,
            },
            {
                "code": "try:\n    f()\nexcept:\n    pass",
                "count": 1,
            },
            {
                "code": "try:\n    f()\nexcept BaseException:\n    pass",
                "count": 1,
            },
            {
                # continue is still doing nothing with the failure.
                "code": "for x in items:\n    try:\n        f(x)\n"
                "    except Exception:\n        continue",
                "count": 1,
            },
            {
                # A tuple containing a broad type is broad.
                "code": "try:\n    f()\nexcept (ValueError, Exception):\n    pass",
                "count": 1,
            },
            {
                "code": (
                    "try:\n"
                    "    f()\n"
                    "except Exception:\n"
                    "    pass\n"
                    "try:\n"
                    "    g()\n"
                    "except Exception:\n"
                    "    pass"
                ),
                "count": 2,
            },
        ],
    )
