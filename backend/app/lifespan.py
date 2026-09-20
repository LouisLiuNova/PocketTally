"""应用启动和关闭生命周期。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlsplit

from fastapi import FastAPI
from loguru import logger
from sqlalchemy import Engine

from app.auth_database import (
    create_auth_database_engine,
    initialize_auth_database,
    resolve_auth_database_path,
)
from app.config import Settings
from app.database import (
    create_database_engine,
    database_process_lock,
    initialize_database,
)
from app.logging import configure_logging


@dataclass(slots=True)
class AppResources:
    """创建一次并由请求依赖共享的资源。"""

    started_at: datetime
    engine: Engine
    auth_engine: Engine | None = None
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
    auth_path = resolve_auth_database_path(settings.database_path, settings.auth_database_path)
    if auth_path == settings.database_path.resolve():
        raise RuntimeError("鉴权数据库必须与账本数据库分离")
    if (
        settings.is_auth_enabled()
        and settings.environment == "production"
        and (
            not settings.public_origin
            or (parsed_origin := urlsplit(settings.public_origin.rstrip("/"))).scheme != "https"
            or not parsed_origin.netloc
            or parsed_origin.path not in {"", "/"}
            or parsed_origin.query
            or parsed_origin.fragment
        )
    ):
        raise RuntimeError("生产环境启用鉴权时必须配置不含路径的 HTTPS POCKET_TALLY_PUBLIC_ORIGIN")
    with database_process_lock(settings.database_path), database_process_lock(auth_path):
        engine = create_database_engine(settings.database_path)
        auth_engine = create_auth_database_engine(auth_path) if settings.is_auth_enabled() else None
        resources = AppResources(started_at=datetime.now(UTC), engine=engine, auth_engine=auth_engine)
        app.state.resources = resources

        logger.info("Application startup begins")
        try:
            initialize_database(engine)
            if auth_engine is not None:
                initialize_auth_database(auth_engine)
            resources.ready = True
            logger.info("Application startup complete")
            yield
        finally:
            resources.ready = False
            logger.info("Application shutdown begins")
            engine.dispose()
            if auth_engine is not None:
                auth_engine.dispose()
            logger.info("Application shutdown complete")
