"""Loguru configuration and standard-library logging interception."""

import logging
import sys
from pathlib import Path

from loguru import logger

from app.config import Settings

LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "request_id={extra[request_id]} | <level>{message}</level>"
)
_stdlib_configured = False


def _write_to_stderr(message: object) -> None:
    """Resolve stderr at write time so redirected test streams are not retained."""

    sys.stderr.write(str(message))


class InterceptHandler(logging.Handler):
    """Forward stdlib and Uvicorn log records to Loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame = logging.currentframe()
        depth = 2
        while frame is not None and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def configure_logging(settings: Settings) -> None:
    """Configure console/file sinks and route stdlib logs through Loguru."""

    logger.remove()
    logger.configure(extra={"request_id": "-"})
    logger.add(
        _write_to_stderr,
        level=settings.log_level.upper(),
        format=LOG_FORMAT,
        colorize=not settings.log_json,
        serialize=settings.log_json,
        backtrace=settings.debug,
        diagnose=settings.debug,
        enqueue=False,
    )

    if settings.log_file:
        log_path = Path(settings.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_path,
            level=settings.log_level.upper(),
            format=LOG_FORMAT,
            serialize=settings.log_json,
            rotation="10 MB",
            retention="14 days",
            compression="gz",
            enqueue=True,
        )

    global _stdlib_configured
    # Pytest owns logging handlers while capturing output. Leave those handlers
    # intact in the test environment; production and development still route
    # stdlib/Uvicorn records through Loguru.
    if settings.environment != "test" and not _stdlib_configured:
        root_logger = logging.getLogger()
        root_logger.handlers = [InterceptHandler()]
        root_logger.setLevel(0)
        for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
            stdlib_logger = logging.getLogger(logger_name)
            stdlib_logger.handlers = [InterceptHandler()]
            stdlib_logger.propagate = False
        _stdlib_configured = True
