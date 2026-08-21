"""分类 HTTP 请求与响应模型。"""

from datetime import datetime
from typing import Any, Self
from uuid import UUID

from pydantic import Field

from app.models import Category
from app.schemas.base import ContractModel, HexColor, UpdateModel


def _uuid_to_string(value: UUID | None) -> str | None:
    """将 Pydantic UUID 转换为 SQLite 使用的字符串 UUID。"""

    return str(value) if value is not None else None


class CategoryCreate(ContractModel):
    """创建分类的请求模型。"""

    name: str = Field(min_length=1)
    description: str | None = None
    parent_category_id: UUID | None = None
    icon_color: HexColor = "#ff0000"
    icon_name: str = Field(default="default_icon", min_length=1)

    def to_orm_kwargs(self) -> dict[str, Any]:
        """转换为 ``Category`` 构造函数可接受的字段。

        Returns:
            使用数据库列名和字符串 UUID 的字典。
        """

        return {
            "name": self.name,
            "description": self.description,
            "parent_category_id": _uuid_to_string(self.parent_category_id),
            "icon_color": self.icon_color,
            "icon_name": self.icon_name,
        }


class CategoryUpdate(UpdateModel):
    """部分更新分类的请求模型。"""

    name: str = Field(default=None, min_length=1)
    description: str | None = None
    parent_category_id: UUID | None = None
    icon_color: HexColor = None
    icon_name: str = Field(default=None, min_length=1)

    def to_orm_kwargs(self) -> dict[str, Any]:
        """将已提交字段转换为 ``Category`` 的更新字段。

        Returns:
            仅包含已提交字段的数据库列名字典；显式 null 会被保留。
        """

        values = self.model_dump(exclude_unset=True, by_alias=False)
        if "parent_category_id" in values:
            values["parent_category_id"] = _uuid_to_string(values["parent_category_id"])
        return values


class CategorySummary(ContractModel):
    """事务或分类关系中嵌入的分类有界摘要。"""

    id: UUID
    name: str = Field(min_length=1)
    icon_color: HexColor
    icon_name: str = Field(min_length=1)

    @classmethod
    def from_orm_model(cls, category: Category) -> Self:
        """从分类 ORM 实例生成摘要。

        Args:
            category: 已加载的分类 ORM 实例。

        Returns:
            分类摘要模型。
        """

        return cls.model_validate(category)


class CategoryRead(ContractModel):
    """分类响应模型，父分类仅嵌入一层摘要。"""

    id: UUID
    name: str = Field(min_length=1)
    description: str | None
    parent_category: CategorySummary | None
    icon_color: HexColor
    icon_name: str = Field(min_length=1)
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm_model(cls, category: Category) -> Self:
        """从分类 ORM 实例生成响应模型。

        Args:
            category: 已加载父分类关系的分类 ORM 实例。

        Returns:
            分类响应模型。
        """

        return cls.model_validate(category)


__all__ = (
    "CategoryCreate",
    "CategoryRead",
    "CategorySummary",
    "CategoryUpdate",
)
