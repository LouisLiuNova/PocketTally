"""从环境变量加载应用配置。"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """从 ``POCKET_TALLY_*`` 环境变量加载运行时配置。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="POCKET_TALLY_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "PocketTally API"
    app_version: str = "0.1.0"
    environment: Literal["local", "test", "staging", "production"] = "local"
    debug: bool = False
    api_prefix: str = "/api/v1"
    host: str = "127.0.0.1"
    port: int = 8000
    log_level: str = "INFO"
    log_json: bool = False
    log_file: str | None = None
    database_path: Path = Path("data/pocket-tally.sqlite3")
    backup_directory: Path = Path("backups")
    auth_database_path: Path | None = None
    public_origin: str | None = None
    auth_enabled: bool | None = None
    trusted_proxy_cidrs: tuple[str, ...] = ()

    def is_auth_enabled(self) -> bool:
        """返回当前运行模式是否启用鉴权。

        旧的业务单元测试使用 ``environment=test`` 且没有认证夹具；测试环境
        默认关闭只是兼容这些纯业务测试，生产和其它运行模式始终开启。
        """

        return self.auth_enabled if self.auth_enabled is not None else self.environment != "test"


@lru_cache
def get_settings() -> Settings:
    """返回进程范围内的配置实例。

    Returns:
        已缓存的应用配置实例。
    """

    return Settings()
