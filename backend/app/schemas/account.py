"""账户 HTTP 请求与响应模型。"""

from datetime import datetime
from typing import Any, Self
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator, model_validator

from app.models import Account, AccountType
from app.schemas.base import ContractModel, UpdateModel


class AccountCreate(ContractModel):
    """创建账户的请求模型。"""

    model_config = ConfigDict(
        json_schema_extra={
            "allOf": [
                {
                    "if": {"properties": {"type": {"const": "debit"}}},
                    "then": {"properties": {"amount": {"minimum": 0}}},
                }
            ]
        }
    )

    type: AccountType
    name: str = Field(min_length=1)
    card_number: str | None = None
    description: str | None = None
    amount: float = 0.0

    @field_validator("type", mode="before")
    @classmethod
    def strip_type(cls, value: object) -> object:
        """保留账户类型字符串的契约级去空白行为。"""

        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_debit_amount(self) -> Self:
        """拒绝借记账户的负余额。"""

        if self.type is AccountType.DEBIT and self.amount < 0:
            raise ValueError("debit 账户余额不能小于 0")
        return self

    def to_orm_kwargs(self) -> dict[str, Any]:
        """转换为 ``Account`` 构造函数可接受的字段。

        Returns:
            使用数据库列名且不包含服务器维护字段的字典。
        """

        return self.model_dump(exclude_unset=False, by_alias=False)


class AccountUpdate(UpdateModel):
    """部分更新账户的请求模型。"""

    type: AccountType = None
    name: str = Field(default=None, min_length=1)
    card_number: str | None = None
    description: str | None = None

    @field_validator("type", mode="before")
    @classmethod
    def strip_type(cls, value: object) -> object:
        """保留账户类型字符串的契约级去空白行为。"""

        return value.strip() if isinstance(value, str) else value

    def to_orm_kwargs(self) -> dict[str, Any]:
        """将已提交字段转换为 ``Account`` 的更新字段。

        Returns:
            仅包含请求中出现字段的数据库列名字典；显式 null 会被保留。
        """

        return self.model_dump(exclude_unset=True, by_alias=False)


class AccountRead(ContractModel):
    """账户响应模型。"""

    id: UUID
    model_config = ConfigDict(
        json_schema_extra={
            "allOf": [
                {
                    "if": {"properties": {"type": {"const": "debit"}}},
                    "then": {"properties": {"amount": {"minimum": 0}}},
                }
            ]
        }
    )

    type: AccountType
    name: str = Field(min_length=1)
    card_number: str | None
    description: str | None
    amount: float
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def validate_debit_amount(self) -> Self:
        """拒绝不符合规则的借记账户响应。"""

        if self.type is AccountType.DEBIT and self.amount < 0:
            raise ValueError("debit 账户余额不能小于 0")
        return self

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
    type: AccountType
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
