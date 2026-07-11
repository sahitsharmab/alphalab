"""Structured logging configuration (see ARCHITECTURE.md, Observability).

Console-friendly output in development, JSON in production. All application
code should obtain loggers via ``structlog.get_logger(__name__)``.
"""

import logging
import sys

import structlog
from structlog.typing import Processor


def configure_logging(level: str = "INFO", json_output: bool = False) -> None:
    """Configure structlog and the stdlib root logger for the whole process."""
    numeric_level = logging.getLevelNamesMapping()[level.upper()]

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]

    renderer: Processor
    if json_output:
        shared_processors.append(structlog.processors.format_exc_info)
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(level=numeric_level, stream=sys.stdout, format="%(message)s")
