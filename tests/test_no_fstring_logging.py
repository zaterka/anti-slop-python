"""Tests for ``anti-slop/no-fstring-logging``."""

from anti_slop.rules.no_fstring_logging import NoFstringLoggingRule

from tests.harness import RuleTester


def test_no_fstring_logging() -> None:
    RuleTester(NoFstringLoggingRule()).run(
        "anti-slop/no-fstring-logging",
        valid=[
            # Lazy % formatting: the documented pattern.
            'logger.info("job %s failed", job_id)',
            # No message argument at all.
            "logger.debug()",
            # A plain (non-f) string is fine.
            'logger.error("failed")',
            # Not a logging method.
            'obj.format(f"{x}")',
            'print(f"{x}")',
            # The f-string is a later argument, not the message.
            'logger.info("failed", extra=f"{x}")',
        ],
        invalid=[
            {"code": 'logger.info(f"job {job_id} failed")', "count": 1},
            {"code": 'logger.debug(f"state: {state}")', "count": 1},
            {"code": 'logger.warning(f"{n} retries left")', "count": 1},
            {"code": 'logger.error(f"{exc}")', "count": 1},
            {"code": 'logger.critical(f"{x}")', "count": 1},
            {"code": 'logger.exception(f"{x}")', "count": 1},
            # Any receiver with a logging-level method is covered.
            {"code": 'self._log.error(f"{x}")', "count": 1},
            {
                "code": 'logger.info(f"{a}")\nlogger.error(f"{b}")',
                "count": 2,
            },
        ],
    )
