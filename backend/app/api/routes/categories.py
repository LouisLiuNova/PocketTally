"""树状分类基础维护路由。"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Response, status
from sqlalchemy.orm import joinedload
from sqlmodel import select

from app.api.errors import (
    NOT_FOUND_CONFLICT_RESPONSES,
    NOT_FOUND_RESPONSES,
    VALIDATION_RESPONSES,
    ApiError,
)
from app.api.routes.common import map_category_error, map_resource_error
from app.categories import CategoryHierarchyError
from app.dependencies import SessionDep
from app.models import Category
from app.resources import (
    ResourceError,
    create_validated_category,
    delete_category,
    update_validated_category,
)
from app.schemas import CategoryCreate, CategoryRead, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])
CategoryId = Annotated[UUID, Path(alias="categoryId", description="分类 UUID。")]


def require_category(session: SessionDep, category_id: UUID) -> Category:
    """读取分类，不存在时返回稳定错误。"""

    category = session.get(Category, str(category_id))
    if category is None:
        raise ApiError(404, "category_not_found", "分类不存在")
    return category


def category_read(session: SessionDep, category_id: str) -> CategoryRead:
    """重新加载分类及其一层父分类摘要。"""

    statement = (
        select(Category)
        .where(Category.id == category_id)
        .options(joinedload(Category.parent_category))
    )
    category = session.exec(statement).one()
    return CategoryRead.from_orm_model(category)


@router.get(
    "",
    response_model=list[CategoryRead],
    responses=VALIDATION_RESPONSES,
    operation_id="listCategories",
)
def list_categories(session: SessionDep) -> list[CategoryRead]:
    """返回全部分类及其一层父分类摘要。"""

    statement = (
        select(Category)
        .options(joinedload(Category.parent_category))
        .order_by(Category.created_at, Category.id)
    )
    return [CategoryRead.from_orm_model(item) for item in session.exec(statement)]


@router.post(
    "",
    response_model=CategoryRead,
    status_code=status.HTTP_201_CREATED,
    responses=NOT_FOUND_CONFLICT_RESPONSES,
    operation_id="createCategory",
)
def create_category_route(
    payload: CategoryCreate,
    response: Response,
    session: SessionDep,
) -> CategoryRead:
    """创建符合树和用途规则的分类。"""

    category = Category(**payload.to_orm_kwargs())
    try:
        create_validated_category(session, category)
    except CategoryHierarchyError as error:
        raise map_category_error(error) from error
    except ResourceError as error:
        raise map_resource_error(error) from error
    response.headers["Location"] = f"/api/v1/categories/{category.id}"
    return category_read(session, category.id)


@router.get(
    "/{categoryId}",
    response_model=CategoryRead,
    responses=NOT_FOUND_RESPONSES,
    operation_id="getCategory",
)
def get_category(category_id: CategoryId, session: SessionDep) -> CategoryRead:
    """返回一个分类及其一层父分类摘要。"""

    category = require_category(session, category_id)
    return category_read(session, category.id)


@router.patch(
    "/{categoryId}",
    response_model=CategoryRead,
    responses=NOT_FOUND_CONFLICT_RESPONSES,
    operation_id="updateCategory",
)
def patch_category(
    category_id: CategoryId,
    payload: CategoryUpdate,
    session: SessionDep,
) -> CategoryRead:
    """部分更新分类并复用树和用途校验。"""

    category = require_category(session, category_id)
    try:
        update_validated_category(session, category, **payload.to_orm_kwargs())
    except CategoryHierarchyError as error:
        raise map_category_error(error) from error
    except ResourceError as error:
        raise map_resource_error(error) from error
    return category_read(session, category.id)


@router.delete(
    "/{categoryId}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=NOT_FOUND_CONFLICT_RESPONSES,
    operation_id="deleteCategory",
)
def remove_category(category_id: CategoryId, session: SessionDep) -> None:
    """删除没有子分类且未被历史交易引用的分类。"""

    category = require_category(session, category_id)
    try:
        delete_category(session, category)
    except ResourceError as error:
        raise map_resource_error(error) from error
