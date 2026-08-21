"""从环境变量加载应用配置。"""

from functools import lru_cache
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


@lru_cache
def get_settings() -> Settings:
    """返回进程范围内的配置实例。

    Returns:
        已缓存的应用配置实例。
    """

    return Settings()
