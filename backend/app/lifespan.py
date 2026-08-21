"""应用启动和关闭生命周期。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import FastAPI
from loguru import logger

from app.config import Settings
from app.logging import configure_logging


@dataclass(slots=True)
class AppResources:
    """创建一次并由请求依赖共享的资源。"""

    started_at: datetime
    ready: bool = False


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """初始化并释放所有进程范围内的应用资源。

    Args:
        app: 接收这些资源并保存到状态中的 FastAPI 应用。

    Yields:
        启动完成后将控制权交给正在运行的应用。
    """

    settings: Settings = app.state.settings
    # 测试运行器负责临时输出流，避免替换其日志接收器。
    if settings.environment != "test":
        configure_logging(settings)
    resources = AppResources(started_at=datetime.now(UTC))
    app.state.resources = resources

    logger.info("Application startup begins")
    try:
        # 在此初始化数据库连接池、客户端和缓存。
        resources.ready = True
        logger.info("Application startup complete")
        yield
    finally:
        resources.ready = False
        logger.info("Application shutdown begins")
        # 在此按初始化的逆序关闭资源。
        logger.info("Application shutdown complete")
