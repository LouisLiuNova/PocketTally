"""交易 HTTP 请求与响应模型。"""

import json
from collections.abc import Sequence
from datetime import datetime
from typing import Any, Self
from uuid import UUID

from pydantic import Field, field_validator

from app.models import Tag, Transaction, TransactionType
from app.schemas.account import AccountSummary
from app.schemas.base import ContractModel, UpdateModel
from app.schemas.category import CategorySummary
from app.schemas.tag import TagSummary


def _uuid_to_string(value: UUID | None) -> str | None:
    """将 Pydantic UUID 转换为 SQLite 使用的字符串 UUID。"""

    return str(value) if value is not None else None


def _encode_tag_ids(tag_ids: Sequence[UUID] | None) -> str | None:
    """将标签 UUID 列表编码为数据库中的 JSON 数组字符串。"""

    if tag_ids is None:
        return None
    return json.dumps([str(tag_id) for tag_id in tag_ids], separators=(",", ":"))


def _decode_tag_ids(raw_tags: str | None) -> list[str]:
    """解析数据库中的标签 JSON，并验证其为字符串 ID 数组。

    Args:
        raw_tags: ``transactions.tags`` 的原始数据库值。

    Returns:
        标签 ID 列表；空值表示没有标签。

    Raises:
        ValueError: JSON 不是字符串数组，或包含重复标签 ID。
    """

    if raw_tags is None:
        return []
    try:
        decoded = json.loads(raw_tags)
    except json.JSONDecodeError as error:
        raise ValueError("transactions.tags 不是有效的 JSON") from error
    if not isinstance(decoded, list) or not all(
        isinstance(tag_id, str) for tag_id in decoded
    ):
        raise ValueError("transactions.tags 必须是字符串 ID 数组")
    if len(decoded) != len(set(decoded)):
        raise ValueError("transactions.tags 中的 ID 必须唯一")
    return decoded


def _require_non_zero_amount(value: float) -> float:
    """拒绝金额为零的交易。

    Args:
        value: 待校验的交易金额。

    Returns:
        非零交易金额。

    Raises:
        ValueError: 交易金额为零时抛出。
    """

    if value == 0:
        raise ValueError("交易金额不能为 0")
    return value


class TransactionCreate(ContractModel):
    """创建交易的请求模型。"""

    type: TransactionType
    source_account_id: UUID
    destination_account_id: UUID | None = None
    amount: float = Field(json_schema_extra={"not": {"const": 0}})
    description: str | None = None
    category_id: UUID
    tag_ids: list[UUID] = Field(
        default_factory=list,
        json_schema_extra={"uniqueItems": True},
    )
    is_refund: bool = False
    related_transaction_id: UUID | None = None
    occurred_at: datetime

    @field_validator("amount")
    @classmethod
    def require_non_zero_amount(cls, value: float) -> float:
        """确保新建交易的金额不为零。"""

        return _require_non_zero_amount(value)

    @field_validator("tag_ids")
    @classmethod
    def require_unique_tag_ids(cls, value: list[UUID]) -> list[UUID]:
        """确保交易标签 ID 不重复。

        Args:
            value: 已解析的标签 ID 列表。

        Returns:
            保持客户端顺序的唯一标签 ID 列表。

        Raises:
            ValueError: 列表包含重复 ID 时抛出。
        """

        if len(value) != len(set(value)):
            raise ValueError("tagIds 中的 UUID 必须唯一")
        return value

    def to_orm_kwargs(self) -> dict[str, Any]:
        """转换为 ``Transaction`` 构造函数可接受的数据库字段。

        Returns:
            使用数据库列名、字符串 UUID 和 JSON 标签数组的字典。
        """

        return {
            "type": self.type,
            "src_account_id": str(self.source_account_id),
            "dest_account_id": _uuid_to_string(self.destination_account_id),
            "amount": self.amount,
            "description": self.description,
            "category": str(self.category_id),
            "tags": _encode_tag_ids(self.tag_ids),
            "is_refund": self.is_refund,
            "related_transaction_id": _uuid_to_string(self.related_transaction_id),
            "occurred_at": self.occurred_at,
        }


class TransactionUpdate(UpdateModel):
    """部分更新交易的请求模型。"""

    type: TransactionType = None
    source_account_id: UUID = None
    destination_account_id: UUID | None = None
    amount: float = Field(default=None, json_schema_extra={"not": {"const": 0}})
    description: str | None = None
    category_id: UUID = None
    tag_ids: list[UUID] = Field(
        default=None,
        json_schema_extra={"uniqueItems": True},
    )
    is_refund: bool = None
    related_transaction_id: UUID | None = None
    occurred_at: datetime = None

    @field_validator("amount")
    @classmethod
    def require_non_zero_amount(cls, value: float) -> float:
        """确保更新后的交易金额不为零。"""

        return _require_non_zero_amount(value)

    @field_validator("tag_ids")
    @classmethod
    def require_unique_tag_ids(cls, value: list[UUID]) -> list[UUID]:
        """确保部分更新中的标签 ID 不重复。

        Args:
            value: 已解析的标签 ID 列表。

        Returns:
            校验后的标签 ID 列表。

        Raises:
            ValueError: 列表包含重复 ID 时抛出。
        """

        if len(value) != len(set(value)):
            raise ValueError("tagIds 中的 UUID 必须唯一")
        return value

    def to_orm_kwargs(self) -> dict[str, Any]:
        """将已提交字段转换为 ``Transaction`` 的更新字段。

        Returns:
            仅包含已提交字段的数据库列名字典；显式 null 会被保留。
        """

        values = self.model_dump(exclude_unset=True, by_alias=False)
        mapping = {
            "source_account_id": "src_account_id",
            "destination_account_id": "dest_account_id",
            "category_id": "category",
            "tag_ids": "tags",
            "related_transaction_id": "related_transaction_id",
        }
        result: dict[str, Any] = {}
        for field_name, value in values.items():
            orm_name = mapping.get(field_name, field_name)
            if field_name.endswith("_id"):
                result[orm_name] = _uuid_to_string(value)
            elif field_name == "tag_ids":
                result[orm_name] = _encode_tag_ids(value)
            else:
                result[orm_name] = value
        return result


class TransactionSummary(ContractModel):
    """退款关联交易中嵌入的有界摘要。"""

    id: UUID
    type: TransactionType
    amount: float = Field(json_schema_extra={"not": {"const": 0}})
    description: str | None
    occurred_at: datetime
    created_at: datetime

    @classmethod
    def from_orm_model(cls, transaction: Transaction) -> Self:
        """从交易 ORM 实例生成摘要，不读取任何关系字段。

        Args:
            transaction: 交易 ORM 实例。

        Returns:
            交易摘要模型。
        """

        return cls.model_validate(transaction)


class TransactionRead(ContractModel):
    """交易响应模型，关系以有界摘要嵌入。"""

    id: UUID
    type: TransactionType
    source_account: AccountSummary
    destination_account: AccountSummary | None
    amount: float = Field(json_schema_extra={"not": {"const": 0}})
    description: str | None
    category: CategorySummary
    tags: list[TagSummary] = Field(json_schema_extra={"uniqueItems": True})
    is_refund: bool
    related_transaction: TransactionSummary | None
    occurred_at: datetime
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm_model(
        cls,
        transaction: Transaction,
        *,
        tag_records: Sequence[Tag] = (),
    ) -> Self:
        """从交易 ORM 实例生成响应模型。

        ``transactions.tags`` 在数据库中是标签 ID 的 JSON 字符串，而不是
        SQLAlchemy 关系。调用方必须传入对应的标签 ORM 实例，才能生成契约
        要求的标签摘要；这样可以把标签查询和 N+1 查询控制留在服务层。

        Args:
            transaction: 已加载账户、分类和关联交易关系的交易 ORM 实例。
            tag_records: 与交易标签 ID 对应的标签 ORM 实例集合。

        Returns:
            交易响应模型。

        Raises:
            ValueError: 数据库中的标签 JSON 无效，或缺少对应标签 ORM 实例。
        """

        tag_ids = _decode_tag_ids(transaction.tags)
        tags_by_id = {tag.id: tag for tag in tag_records}
        missing_tag_ids = [tag_id for tag_id in tag_ids if tag_id not in tags_by_id]
        if missing_tag_ids:
            missing = ", ".join(missing_tag_ids)
            raise ValueError(f"交易引用了未加载的标签: {missing}")

        return cls.model_validate(
            {
                "id": transaction.id,
                "type": transaction.type,
                "source_account": transaction.source_account,
                "destination_account": transaction.destination_account,
                "amount": transaction.amount,
                "description": transaction.description,
                "category": transaction.category_record,
                "tags": [tags_by_id[tag_id] for tag_id in tag_ids],
                "is_refund": transaction.is_refund,
                "related_transaction": transaction.related_transaction,
                "occurred_at": transaction.occurred_at,
                "created_at": transaction.created_at,
                "updated_at": transaction.updated_at,
            }
        )


__all__ = (
    "TransactionCreate",
    "TransactionRead",
    "TransactionSummary",
    "TransactionUpdate",
)
