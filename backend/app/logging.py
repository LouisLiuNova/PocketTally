"""Loguru 配置和标准库日志拦截。"""

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
    """将日志消息写入当前标准错误流。

    Args:
        message: 要写入的日志消息。

    Returns:
        无返回值。
    """

    sys.stderr.write(str(message))


class InterceptHandler(logging.Handler):
    """将标准库和 Uvicorn 日志记录转发到 Loguru。"""

    def emit(self, record: logging.LogRecord) -> None:
        """将一条标准库日志记录转发到 Loguru。

        Args:
            record: 要转发的标准库日志记录。

        Returns:
            无返回值。
        """

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
    """配置控制台和文件接收器，并将标准库日志转发到 Loguru。

    Args:
        settings: 控制日志级别和输出目标的应用配置。

    Returns:
        无返回值。
    """

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
    # Pytest 在捕获输出时负责日志处理器，测试环境保留这些处理器；生产和开发环境
    # 仍将标准库及 Uvicorn 日志记录转发到 Loguru。
    if settings.environment != "test" and not _stdlib_configured:
        root_logger = logging.getLogger()
        root_logger.handlers = [InterceptHandler()]
        root_logger.setLevel(0)
        for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
            stdlib_logger = logging.getLogger(logger_name)
            stdlib_logger.handlers = [InterceptHandler()]
            stdlib_logger.propagate = False
        _stdlib_configured = True
