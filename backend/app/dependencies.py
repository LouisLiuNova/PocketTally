"""Reusable FastAPI dependencies and their type aliases."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from app.config import Settings, get_settings
from app.lifespan import AppResources


def get_resources(request: Request) -> AppResources:
    """Expose lifespan-managed resources to a request."""

    resources: AppResources | None = getattr(request.app.state, "resources", None)
    if resources is None or not resources.ready:
        raise RuntimeError("Application resources are not ready")
    return resources


SettingsDep = Annotated[Settings, Depends(get_settings)]
ResourcesDep = Annotated[AppResources, Depends(get_resources)]


@dataclass(frozen=True, slots=True)
class RequestContext:
    """Common request-scoped values for services and route handlers."""

    request_id: str
    settings: Settings
    resources: AppResources


def get_request_context(
    request: Request,
    settings: SettingsDep,
    resources: ResourcesDep,
) -> RequestContext:
    return RequestContext(
        request_id=request.state.request_id,
        settings=settings,
        resources=resources,
    )


RequestContextDep = Annotated[RequestContext, Depends(get_request_context)]
