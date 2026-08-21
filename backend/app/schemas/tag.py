"""标签 HTTP 请求与响应模型。"""

from datetime import datetime
from typing import Any, Self
from uuid import UUID

from pydantic import Field

from app.models import Tag
from app.schemas.base import ContractModel, HexColor, UpdateModel


class TagSummary(ContractModel):
    """交易中嵌入的标签有界摘要。"""

    id: UUID
    name: str = Field(min_length=1)
    color: HexColor

    @classmethod
    def from_orm_model(cls, tag: Tag) -> Self:
        """从标签 ORM 实例生成摘要。

        Args:
            tag: 已加载的标签 ORM 实例。

        Returns:
            标签摘要模型。
        """

        return cls.model_validate(tag)


class TagCreate(ContractModel):
    """创建标签的请求模型。"""

    name: str = Field(min_length=1)
    description: str | None = None
    color: HexColor = "#ff0000"

    def to_orm_kwargs(self) -> dict[str, Any]:
        """转换为 ``Tag`` 构造函数可接受的字段。

        Returns:
            使用数据库列名的字典。
        """

        return self.model_dump(exclude_unset=False, by_alias=False)


class TagUpdate(UpdateModel):
    """部分更新标签的请求模型。"""

    name: str = Field(default=None, min_length=1)
    description: str | None = None
    color: HexColor = None

    def to_orm_kwargs(self) -> dict[str, Any]:
        """将已提交字段转换为 ``Tag`` 的更新字段。

        Returns:
            仅包含已提交字段的数据库列名字典；显式 null 会被保留。
        """

        return self.model_dump(exclude_unset=True, by_alias=False)


class TagRead(ContractModel):
    """标签响应模型。"""

    id: UUID
    name: str = Field(min_length=1)
    description: str | None
    color: HexColor
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm_model(cls, tag: Tag) -> Self:
        """从标签 ORM 实例生成响应模型。

        Args:
            tag: 已加载的标签 ORM 实例。

        Returns:
            标签响应模型。
        """

        return cls.model_validate(tag)


__all__ = ("TagCreate", "TagRead", "TagSummary", "TagUpdate")
