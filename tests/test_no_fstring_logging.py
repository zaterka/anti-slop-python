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
            # Not a logger. `.error` is argparse's abort-with-message; eager
            # formatting there is correct.
            'parser.error(f"bad value: {value}")',
            'response.error(f"{x}")',
            'self.report.warning(f"{x}")',
            'result.critical(f"{x}")',
        ],
        invalid=[
            {"code": 'logger.info(f"job {job_id} failed")', "count": 1},
            {"code": 'logger.debug(f"state: {state}")', "count": 1},
            {"code": 'logger.warning(f"{n} retries left")', "count": 1},
            {"code": 'logger.error(f"{exc}")', "count": 1},
            {"code": 'logger.critical(f"{x}")', "count": 1},
            {"code": 'logger.exception(f"{x}")', "count": 1},
            # Any logger-shaped receiver is covered.
            {"code": 'self._log.error(f"{x}")', "count": 1},
            {"code": 'self.logger.info(f"{x}")', "count": 1},
            {"code": 'app.state.log.warning(f"{x}")', "count": 1},
            {"code": 'logging.info(f"{x}")', "count": 1},
            {"code": 'LOGGER.error(f"{x}")', "count": 1},
            # Constructed inline, never bound to a name.
            {"code": 'logging.getLogger(__name__).info(f"{x}")', "count": 1},
            {
                "code": 'logger.info(f"{a}")\nlogger.error(f"{b}")',
                "count": 2,
            },
        ],
    )


def test_no_fstring_logging_extra_receivers() -> None:
    RuleTester(NoFstringLoggingRule(), options={"receivers": ["audit"]}).run(
        "anti-slop/no-fstring-logging (receivers)",
        valid=[
            # Still not a logger, even with the list extended.
            'parser.error(f"bad value: {value}")',
        ],
        invalid=[
            {"code": 'audit.info(f"{a}")', "count": 1},
            # The built-in names stay recognized alongside the configured ones.
            {"code": 'logger.info(f"{a}")', "count": 1},
        ],
    )
