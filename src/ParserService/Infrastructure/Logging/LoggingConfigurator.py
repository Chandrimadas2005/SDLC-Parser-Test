import logging
import sys

import structlog


class LoggingConfigurator:
    """Sets up structlog to emit one JSON line per event, with request context merged in."""

    def configure(self, level: str) -> None:
        """Configure structlog and the standard library root logger.

        Args:
            level: A standard logging level name such as ``INFO`` or ``DEBUG``.
        """
        numeric_level = logging.getLevelNamesMapping().get(level.upper(), logging.INFO)
        logging.basicConfig(format="%(message)s", stream=sys.stdout, level=numeric_level)
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso", utc=True),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
            logger_factory=structlog.PrintLoggerFactory(sys.stdout),
            cache_logger_on_first_use=False,
        )
