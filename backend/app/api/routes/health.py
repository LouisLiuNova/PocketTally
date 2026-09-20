"""服务健康检查端点。"""

from fastapi import APIRouter

from app.dependencies import RequestContextDep

router = APIRouter()


@router.get("/health", summary="Service liveness and readiness")
async def health(context: RequestContextDep) -> dict[str, str | bool]:
    """返回不包含敏感运行细节的存活和就绪状态。

    Args:
        context: 请求范围内的配置、资源和请求标识。

    Returns:
        可兼容 JSON 的最小健康状态数据。
    """

    return {
        "status": "ok",
        "ready": context.resources.ready,
    }
