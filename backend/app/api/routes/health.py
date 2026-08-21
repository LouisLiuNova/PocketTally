"""Service health endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter

from app.dependencies import RequestContextDep

router = APIRouter()


@router.get("/health", summary="Service liveness and readiness")
async def health(context: RequestContextDep) -> dict[str, str | float | bool]:
    uptime = (datetime.now(UTC) - context.resources.started_at).total_seconds()
    return {
        "status": "ok",
        "ready": context.resources.ready,
        "environment": context.settings.environment,
        "version": context.settings.app_version,
        "uptime_seconds": round(uptime, 3),
        "request_id": context.request_id,
    }
