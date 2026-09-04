"""可复用的 FastAPI 依赖及其类型别名。"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from sqlmodel import Session

from app.config import Settings, get_settings
from app.lifespan import AppResources


def get_resources(request: Request) -> AppResources:
    """向请求提供由生命周期管理的资源。

    Args:
        request: 包含应用状态的当前 HTTP 请求。

    Returns:
        已初始化的应用资源。

    Raises:
        RuntimeError: 应用资源缺失或尚未就绪时抛出。
    """

    resources: AppResources | None = getattr(request.app.state, "resources", None)
    if resources is None or not resources.ready:
        raise RuntimeError("Application resources are not ready")
    return resources


SettingsDep = Annotated[Settings, Depends(get_settings)]
ResourcesDep = Annotated[AppResources, Depends(get_resources)]


def get_session(resources: ResourcesDep) -> Iterator[Session]:
    """提供提交或回滚由请求结果决定的数据库会话。

    Args:
        resources: 包含共享数据库 Engine 的应用资源。

    Yields:
        当前请求独占的数据库 Session。
    """

    with (
        Session(resources.engine, expire_on_commit=False) as session,
        session.begin(),
    ):
        yield session


SessionDep = Annotated[Session, Depends(get_session, scope="function")]


@dataclass(frozen=True, slots=True)
class RequestContext:
    """服务和路由处理器共用的请求范围值。"""

    request_id: str
    settings: Settings
    resources: AppResources


def get_request_context(
    request: Request,
    settings: SettingsDep,
    resources: ResourcesDep,
) -> RequestContext:
    """构建路由处理器使用的请求上下文。

    Args:
        request: 当前 HTTP 请求。
        settings: 进程范围内的应用配置。
        resources: 已初始化的应用资源。

    Returns:
        包含请求标识和共享状态的请求上下文。
    """

    return RequestContext(
        request_id=request.state.request_id,
        settings=settings,
        resources=resources,
    )


RequestContextDep = Annotated[RequestContext, Depends(get_request_context)]
