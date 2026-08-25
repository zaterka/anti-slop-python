"""Tests for ``anti-slop/no-blocking-sleep-in-async``."""

from anti_slop.rules.no_blocking_sleep_in_async import (
    NoBlockingSleepInAsyncRule,
)

from tests.harness import RuleTester


def test_no_blocking_sleep_in_async() -> None:
    RuleTester(NoBlockingSleepInAsyncRule()).run(
        "anti-slop/no-blocking-sleep-in-async",
        valid=[
            # Synchronous function: blocking is fine.
            "import time\n"
            "def f():\n"
            "    time.sleep(1)",
            # asyncio.sleep is the fix.
            "import asyncio\n"
            "async def f():\n"
            "    await asyncio.sleep(1)",
            # A .sleep method on something else is out of scope.
            "async def f():\n"
            "    await player.sleep()",
            # time module shadowed at module level.
            "time = my_clock\n"
            "async def f():\n"
            "    time.sleep(1)",
        ],
        invalid=[
            {
                "code": (
                    "import time\n"
                    "async def f():\n"
                    "    time.sleep(1)"
                ),
                "count": 1,
            },
            {
                # Aliased import.
                "code": (
                    "import time as t\n"
                    "async def f():\n"
                    "    t.sleep(1)"
                ),
                "count": 1,
            },
            {
                # Nested under a compound statement.
                "code": (
                    "import time\n"
                    "async def f():\n"
                    "    if busy:\n"
                    "        time.sleep(1)"
                ),
                "count": 1,
            },
            {
                # A synchronous sleep inside an async function is still a
                # blocking call even if another await exists.
                "code": (
                    "import time, asyncio\n"
                    "async def f():\n"
                    "    time.sleep(1)\n"
                    "    await asyncio.sleep(1)"
                ),
                "count": 1,
            },
        ],
    )
