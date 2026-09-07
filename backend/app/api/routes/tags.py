"""标签基础维护路由。"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Response, status
from sqlmodel import select

from app.api.errors import (
    CONFLICT_RESPONSES,
    NOT_FOUND_CONFLICT_RESPONSES,
    NOT_FOUND_RESPONSES,
    VALIDATION_RESPONSES,
    ApiError,
)
from app.api.routes.common import map_resource_error
from app.dependencies import SessionDep
from app.models import Tag
from app.resources import ResourceError, create_tag, delete_tag, update_tag
from app.schemas import TagCreate, TagRead, TagUpdate

router = APIRouter(prefix="/tags", tags=["tags"])
TagId = Annotated[UUID, Path(alias="tagId", description="标签 UUID。")]


def require_tag(session: SessionDep, tag_id: UUID) -> Tag:
    """读取标签，不存在时返回稳定错误。"""

    tag = session.get(Tag, str(tag_id))
    if tag is None:
        raise ApiError(404, "tag_not_found", "标签不存在")
    return tag


@router.get(
    "",
    response_model=list[TagRead],
    responses=VALIDATION_RESPONSES,
    operation_id="listTags",
)
def list_tags(session: SessionDep) -> list[TagRead]:
    """按创建时间和 ID 返回全部标签。"""

    tags = session.exec(select(Tag).order_by(Tag.created_at, Tag.id)).all()
    return [TagRead.from_orm_model(tag) for tag in tags]


@router.post(
    "",
    response_model=TagRead,
    status_code=status.HTTP_201_CREATED,
    responses=CONFLICT_RESPONSES,
    operation_id="createTag",
)
def create_tag_route(
    payload: TagCreate,
    response: Response,
    session: SessionDep,
) -> TagRead:
    """创建标签。"""

    try:
        tag = create_tag(session, Tag(**payload.to_orm_kwargs()))
    except ResourceError as error:
        raise map_resource_error(error) from error
    response.headers["Location"] = f"/api/v1/tags/{tag.id}"
    return TagRead.from_orm_model(tag)


@router.get(
    "/{tagId}",
    response_model=TagRead,
    responses=NOT_FOUND_RESPONSES,
    operation_id="getTag",
)
def get_tag(tag_id: TagId, session: SessionDep) -> TagRead:
    """返回一个标签。"""

    return TagRead.from_orm_model(require_tag(session, tag_id))


@router.patch(
    "/{tagId}",
    response_model=TagRead,
    responses=NOT_FOUND_CONFLICT_RESPONSES,
    operation_id="updateTag",
)
def patch_tag(
    tag_id: TagId,
    payload: TagUpdate,
    session: SessionDep,
) -> TagRead:
    """部分更新标签。"""

    tag = require_tag(session, tag_id)
    try:
        update_tag(session, tag, **payload.to_orm_kwargs())
    except ResourceError as error:
        raise map_resource_error(error) from error
    return TagRead.from_orm_model(tag)


@router.delete(
    "/{tagId}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=NOT_FOUND_CONFLICT_RESPONSES,
    operation_id="deleteTag",
)
def remove_tag(tag_id: TagId, session: SessionDep) -> None:
    """删除未被历史交易引用的标签。"""

    tag = require_tag(session, tag_id)
    try:
        delete_tag(session, tag)
    except ResourceError as error:
        raise map_resource_error(error) from error
