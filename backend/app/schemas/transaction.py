"""交易 HTTP 请求与响应模型。"""

from datetime import datetime
from typing import Any, Self
from uuid import UUID

from pydantic import Field, field_validator

from app.models import Transaction, TransactionType
from app.schemas.account import AccountSummary
from app.schemas.base import ContractModel, UpdateModel
from app.schemas.category import CategorySummary
from app.schemas.tag import TagSummary


def _uuid_to_string(value: UUID | None) -> str | None:
    """将 Pydantic UUID 转换为 SQLite 使用的字符串 UUID。"""

    return str(value) if value is not None else None


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
            使用数据库列名和字符串 UUID 的字典；标签关系由服务层写入
            ``transaction_tags`` 关联表。
        """

        return {
            "type": self.type,
            "src_account_id": str(self.source_account_id),
            "dest_account_id": _uuid_to_string(self.destination_account_id),
            "amount": self.amount,
            "description": self.description,
            "category": str(self.category_id),
            "is_refund": self.is_refund,
            "related_transaction_id": _uuid_to_string(self.related_transaction_id),
            "occurred_at": self.occurred_at,
        }

    def tag_ids_for_relation(self) -> list[str]:
        """返回用于创建 ``transaction_tags`` 关联记录的字符串 UUID 列表。

        Returns:
            保持客户端顺序的标签字符串 UUID 列表。
        """

        return [str(tag_id) for tag_id in self.tag_ids]


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
            仅包含已提交的交易表字段；标签关系由服务层单独替换。
        """

        values = self.model_dump(exclude_unset=True, by_alias=False)
        mapping = {
            "source_account_id": "src_account_id",
            "destination_account_id": "dest_account_id",
            "category_id": "category",
            "related_transaction_id": "related_transaction_id",
        }
        result: dict[str, Any] = {}
        for field_name, value in values.items():
            if field_name == "tag_ids":
                continue
            orm_name = mapping.get(field_name, field_name)
            if field_name.endswith("_id"):
                result[orm_name] = _uuid_to_string(value)
            else:
                result[orm_name] = value
        return result

    def tag_ids_for_relation(self) -> list[str] | None:
        """返回标签替换请求，未提交标签字段时返回 ``None``。

        Returns:
            显式提交时的标签字符串 UUID 列表；未提交时为 ``None``。
        """

        if "tag_ids" not in self.model_fields_set:
            return None
        return [str(tag_id) for tag_id in self.tag_ids]


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
    ) -> Self:
        """从交易 ORM 实例生成响应模型。

        调用方应预加载 ``tags`` 关系，以避免列表接口产生 N+1 查询。

        Args:
            transaction: 已加载账户、分类、标签和关联交易关系的交易 ORM 实例。

        Returns:
            交易响应模型。

        """

        return cls.model_validate(
            {
                "id": transaction.id,
                "type": transaction.type,
                "source_account": transaction.source_account,
                "destination_account": transaction.destination_account,
                "amount": transaction.amount,
                "description": transaction.description,
                "category": transaction.category_record,
                "tags": transaction.tags,
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
