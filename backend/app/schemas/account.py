"""账户 HTTP 请求与响应模型。"""

from datetime import datetime
from typing import Any, Self
from uuid import UUID

from pydantic import Field

from app.models import Account
from app.schemas.base import ContractModel, UpdateModel


class AccountCreate(ContractModel):
    """创建账户的请求模型。"""

    type: str = Field(min_length=1)
    name: str = Field(min_length=1)
    card_number: str | None = None
    description: str | None = None
    amount: float = 0.0

    def to_orm_kwargs(self) -> dict[str, Any]:
        """转换为 ``Account`` 构造函数可接受的字段。

        Returns:
            使用数据库列名且不包含服务器维护字段的字典。
        """

        return self.model_dump(exclude_unset=False, by_alias=False)


class AccountUpdate(UpdateModel):
    """部分更新账户的请求模型。"""

    type: str = Field(default=None, min_length=1)
    name: str = Field(default=None, min_length=1)
    card_number: str | None = None
    description: str | None = None

    def to_orm_kwargs(self) -> dict[str, Any]:
        """将已提交字段转换为 ``Account`` 的更新字段。

        Returns:
            仅包含请求中出现字段的数据库列名字典；显式 null 会被保留。
        """

        return self.model_dump(exclude_unset=True, by_alias=False)


class AccountRead(ContractModel):
    """账户响应模型。"""

    id: UUID
    type: str = Field(min_length=1)
    name: str = Field(min_length=1)
    card_number: str | None
    description: str | None
    amount: float
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm_model(cls, account: Account) -> Self:
        """从账户 ORM 实例生成响应模型。

        Args:
            account: 已加载的账户 ORM 实例。

        Returns:
            账户响应模型。
        """

        return cls.model_validate(account)


class AccountSummary(ContractModel):
    """事务中嵌入的账户有界摘要。"""

    id: UUID
    type: str = Field(min_length=1)
    name: str = Field(min_length=1)

    @classmethod
    def from_orm_model(cls, account: Account) -> Self:
        """从账户 ORM 实例生成摘要。

        Args:
            account: 已加载的账户 ORM 实例。

        Returns:
            账户摘要模型。
        """

        return cls.model_validate(account)


__all__ = ("AccountCreate", "AccountRead", "AccountSummary", "AccountUpdate")
