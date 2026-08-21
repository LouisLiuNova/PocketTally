"""FastAPI application factory and command-line entry point."""

import uvicorn
from fastapi import FastAPI

from app.api.router import api_router
from app.config import Settings, get_settings
from app.lifespan import lifespan
from app.logging import configure_logging
from app.middleware import register_middleware


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build an application instance, allowing settings injection in tests."""

    settings = settings or get_settings()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )
    application.state.settings = settings
    # Keep every Settings dependency consistent with the instance used to
    # construct this application (especially for tests and embedded use).
    application.dependency_overrides[get_settings] = lambda: settings
    register_middleware(application)
    application.include_router(api_router, prefix=settings.api_prefix)
    return application


app = create_app()


def main() -> None:
    """Run the development server using values from application settings."""

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
