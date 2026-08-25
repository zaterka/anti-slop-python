"""Tests for ``anti-slop/no-utcnow``."""

from anti_slop.rules.no_utcnow import NoUtcnowRule

from tests.harness import RuleTester


def test_no_utcnow() -> None:
    RuleTester(NoUtcnowRule()).run(
        "anti-slop/no-utcnow",
        valid=[
            # The documented replacement.
            "from datetime import datetime, timezone\n"
            "now = datetime.now(timezone.utc)",
            # Local (aware or naive) now() is out of scope.
            "from datetime import datetime\n"
            "now = datetime.now()",
            # A same-named method on another object.
            "my_clock.utcnow()",
            # utcnow as a non-call attribute access.
            "f = datetime.utcnow",
        ],
        invalid=[
            {
                "code": (
                    "from datetime import datetime\n"
                    "now = datetime.utcnow()"
                ),
                "count": 1,
            },
            {
                "code": (
                    "import datetime\n"
                    "now = datetime.datetime.utcnow()"
                ),
                "count": 1,
            },
            {
                "code": (
                    "from datetime import datetime, timezone\n"
                    "stamp = datetime.utcnow()\n"
                    "check = datetime.now(timezone.utc)"
                ),
                "count": 1,
            },
        ],
    )
