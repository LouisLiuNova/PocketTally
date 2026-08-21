"""FastAPI 应用工厂和命令行入口。"""

import uvicorn
from fastapi import FastAPI

from app.api.router import api_router
from app.config import Settings, get_settings
from app.lifespan import lifespan
from app.logging import configure_logging
from app.middleware import register_middleware


def create_app(settings: Settings | None = None) -> FastAPI:
    """构建应用实例，并支持在测试中注入配置。

    Args:
        settings: 可选的应用配置，将注入新建的应用实例。

    Returns:
        已配置的 FastAPI 应用。
    """

    settings = settings or get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )
    application.state.settings = settings
    # 让所有 Settings 依赖都使用构建此应用实例时的配置，尤其适用于测试和嵌入式使用。
    application.dependency_overrides[get_settings] = lambda: settings
    register_middleware(application)
    application.include_router(api_router, prefix=settings.api_prefix)
    return application


app = create_app()


def main() -> None:
    """使用应用配置中的值运行开发服务器。

    Returns:
        无返回值。
    """

    settings = get_settings()
    configure_logging(settings)
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.environment == "local",
        log_config=None,
        access_log=False,
    )


if __name__ == "__main__":
    main()
