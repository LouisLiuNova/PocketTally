"""Application lifecycle and dependency integration tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app


@pytest.mark.asyncio
async def test_health_uses_lifespan_resources_and_dependencies() -> None:
    app = create_app(Settings(environment="test", log_level="WARNING"))

    async with app.router.lifespan_context(app), AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            "/api/v1/health", headers={"X-Request-ID": "test-id"}
        )
        assert app.state.resources.ready is True

    assert app.state.resources.ready is False

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-id"
    body = response.json()
    assert body["status"] == "ok"
    assert body["ready"] is True
    assert body["environment"] == "test"
    assert body["version"] == "0.1.0"
    assert body["request_id"] == "test-id"
    assert body["uptime_seconds"] >= 0


@pytest.mark.asyncio
async def test_openapi_is_available() -> None:
    app = create_app(Settings(environment="test", log_level="WARNING"))

    async with app.router.lifespan_context(app), AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/v1/health" in response.json()["paths"]
