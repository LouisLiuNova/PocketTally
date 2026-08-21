"""Application startup and shutdown lifecycle."""

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
    """Resources created once and shared by request dependencies."""

    started_at: datetime
    ready: bool = False


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and tear down all process-scoped application resources."""

    settings: Settings = app.state.settings
    # Test runners own temporary output streams; avoid replacing their sinks.
    if settings.environment != "test":
        configure_logging(settings)
    resources = AppResources(started_at=datetime.now(UTC))
    app.state.resources = resources

    logger.info("Application startup begins")
    try:
        # Initialize database pools, clients, and caches here.
        resources.ready = True
        logger.info("Application startup complete")
        yield
    finally:
        resources.ready = False
        logger.info("Application shutdown begins")
        # Close resources here in reverse initialization order.
        logger.info("Application shutdown complete")
