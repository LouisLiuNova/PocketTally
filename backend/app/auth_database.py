"""鉴权 SQLite Engine、锁和初始化。"""

from pathlib import Path

from sqlalchemy import URL, Engine, create_engine, text

from app.auth_models import AuthBase
from app.database import database_process_lock, resolve_database_path


def resolve_auth_database_path(database_path: Path, auth_database_path: Path | None) -> Path:
    """解析鉴权库路径，默认与当前账本文件同目录但使用独立文件名。"""

    if auth_database_path is not None:
        return resolve_database_path(auth_database_path)
    return resolve_database_path(database_path.with_name(f"{database_path.stem}.auth.sqlite3"))


def create_auth_database_engine(database_path: Path) -> Engine:
    """创建鉴权库同步 Engine。"""

    path = resolve_database_path(database_path)
    return create_engine(
        URL.create("sqlite", database=str(path)),
        connect_args={"check_same_thread": False},
    )


def initialize_auth_database(engine: Engine) -> None:
    """创建鉴权库初始表结构。

    鉴权库是独立的初始基线；未来结构变化必须增加显式版本迁移，不能静默
    删除或重建所有者凭据。
    """

    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys = ON")
        version = connection.execute(text("PRAGMA user_version")).scalar_one()
        if version not in (0, 1):
            raise RuntimeError(f"不支持的鉴权数据库版本：{version}")
        AuthBase.metadata.create_all(connection)
        if version == 0:
            connection.exec_driver_sql("PRAGMA user_version = 1")


__all__ = (
    "create_auth_database_engine",
    "database_process_lock",
    "initialize_auth_database",
    "resolve_auth_database_path",
)
