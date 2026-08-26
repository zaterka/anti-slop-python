"""Tests for ``anti-slop/no-async-without-await``."""

from anti_slop.rules.no_async_without_await import NoAsyncWithoutAwaitRule

from tests.harness import RuleTester


def test_no_async_without_await() -> None:
    RuleTester(NoAsyncWithoutAwaitRule()).run(
        "anti-slop/no-async-without-await",
        valid=[
            # Actually awaits.
            "async def f():\n    return await g()",
            "async def f():\n    for x in await fetch():\n        yield x",
            # Await nested in an expression.
            "async def f():\n    return [await fetch(x) for x in xs]",
            # Async generator: no await, but it yields to the loop.
            "async def f():\n    for x in stream:\n        yield x",
            # `async with` / `async for` are async work with no Await node.
            "async def f(session):\n"
            "    async with session.get(url) as resp:\n"
            "        return resp",
            "async def f(stream):\n"
            "    out = []\n"
            "    async for chunk in stream:\n"
            "        out.append(chunk)\n"
            "    return out",
            "async def f():\n"
            "    async with TaskGroup() as tg:\n"
            "        tg.create_task(work())",
            # Async comprehension: suspends without an Await node either.
            "async def f(stream):\n    return [x async for x in stream]",
            # Synchronous functions are out of scope.
            "def f():\n    return 1",
        ],
        invalid=[
            {"code": "async def f():\n    return 1", "count": 1},
            {"code": "async def f():\n    pass", "count": 1},
            {
                # Computed synchronously; the coroutine never yields.
                "code": (
                    "async def f():\n"
                    "    total = 0\n"
                    "    for x in xs:\n"
                    "        total += x\n"
                    "    return total"
                ),
                "count": 1,
            },
            {
                # A nested function's await does not count for this one.
                "code": (
                    "async def f():\n"
                    "    def inner():\n"
                    "        return 1\n"
                    "    return inner()"
                ),
                "count": 1,
            },
            {
                "code": (
                    "async def f():\n    return 1\n"
                    "async def g():\n    return 2"
                ),
                "count": 2,
            },
        ],
    )
