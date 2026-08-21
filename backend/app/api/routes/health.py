"""服务健康检查端点。"""

from datetime import UTC, datetime

from fastapi import APIRouter

from app.dependencies import RequestContextDep

router = APIRouter()


@router.get("/health", summary="Service liveness and readiness")
async def health(context: RequestContextDep) -> dict[str, str | float | bool]:
    """返回服务存活状态、就绪状态、版本和运行时间信息。

    Args:
        context: 请求范围内的配置、资源和请求标识。

    Returns:
        可兼容 JSON 的健康状态数据。
    """

    uptime = (datetime.now(UTC) - context.resources.started_at).total_seconds()
    return {
        "status": "ok",
        "ready": context.resources.ready,
        "environment": context.settings.environment,
        "version": context.settings.app_version,
        "uptime_seconds": round(uptime, 3),
        "request_id": context.request_id,
    }
