"""根据 ``docs/contracts/db.dbml`` 派生的 SQLModel 持久化模型。"""

# SQLModel 关系字段需要直接使用尚未声明的模型类型；运行时由关系配置解析。

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Integer,
    Text,
    func,
    text,
)
from sqlalchemy import Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship
from sqlmodel import Field, Relationship, SQLModel


def new_id() -> str:
    """返回 SQLite 数据库模式使用的字符串 UUID。

    Returns:
        新生成的字符串形式 UUID。
    """

    return str(uuid4())


def timestamp_column() -> Column[datetime]:
    """创建使用 SQLite 约定默认值的时间戳列。

    Returns:
        一个非空的 SQLAlchemy 时间戳列，其默认值为当前时间。
    """

    return Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        onupdate=func.current_timestamp(),
    )


class TransactionType(StrEnum):
    """系统支持的交易类型。"""

    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"
    BALANCE_ADJUSTMENT = "balance_adjustment"


class AccountType(StrEnum):
    """系统支持的账户类型。"""

    DEBIT = "debit"
    CREDIT = "credit"


class BalanceAdjustmentDirection(StrEnum):
    """余额调整的资金方向。"""

    INCREASE = "increase"
    DECREASE = "decrease"


def enum_values(enum_class: type[StrEnum]) -> list[str]:
    """返回枚举实际写入数据库的值。

    Args:
        enum_class: SQLAlchemy 传入的字符串枚举类。

    Returns:
        按枚举声明顺序排列的持久化值。
    """

    return [member.value for member in enum_class]


class Account(SQLModel, table=True):
    """借记账户或信用账户。"""

    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint(
            "type = 'credit' OR amount_minor >= 0",
            name="ck_accounts_debit_amount_nonnegative",
        ),
        CheckConstraint(
            "typeof(amount_minor) = 'integer'",
            name="ck_accounts_amount_minor_integer",
        ),
    )

    id: str = Field(default_factory=new_id,
                    sa_column=Column(Text, primary_key=True))
    type: AccountType = Field(
        sa_column=Column(
            SQLAlchemyEnum(
                AccountType,
                values_callable=enum_values,
                native_enum=False,
                create_constraint=True,
                name="account_type",
            ),
            nullable=False,
        )
    )
    name: str = Field(
        sa_column=Column(Text(collation="NOCASE"), nullable=False, unique=True)
    )
    card_number: str | None = Field(default=None, sa_column=Column(Text))
    description: str | None = Field(default=None, sa_column=Column(Text))
    amount_minor: int = Field(
        default=0,
        sa_column=Column(Integer, nullable=False, server_default=text("0")),
    )
    created_at: datetime = Field(sa_column=timestamp_column())
    updated_at: datetime = Field(sa_column=timestamp_column())

    source_transactions: list[Transaction] = Relationship(
        sa_relationship=relationship(
            "Transaction",
            back_populates="source_account",
            foreign_keys="Transaction.src_account_id",
        ),
    )
    destination_transactions: list[Transaction] = Relationship(
        sa_relationship=relationship(
            "Transaction",
            back_populates="destination_account",
            foreign_keys="Transaction.dest_account_id",
        ),
    )


class Category(SQLModel, table=True):
    """交易分类，可选择嵌套在另一个分类下。"""

    __tablename__ = "categories"

    id: str = Field(default_factory=new_id,
                    sa_column=Column(Text, primary_key=True))
    name: str = Field(
        sa_column=Column(Text(collation="NOCASE"), nullable=False, unique=True)
    )
    description: str | None = Field(default=None, sa_column=Column(Text))
    parent_category_id: str | None = Field(
        default=None,
        foreign_key="categories.id",
        index=True,
    )
    icon_color: str = Field(
        default="#ff0000",
        sa_column=Column(Text, nullable=False,
                         server_default=text("'#ff0000'")),
    )
    icon_name: str = Field(
        default="default_icon",
        sa_column=Column(Text, nullable=False,
                         server_default=text("'default_icon'")),
    )
    created_at: datetime = Field(sa_column=timestamp_column())
    updated_at: datetime = Field(sa_column=timestamp_column())

    parent_category: Category | None = Relationship(
        sa_relationship=relationship(
            "Category",
            back_populates="child_categories",
            remote_side="Category.id",
        ),
    )
    child_categories: list[Category] = Relationship(
        sa_relationship=relationship(
            "Category", back_populates="parent_category")
    )
    transactions: list[Transaction] = Relationship(
        sa_relationship=relationship(
            "Transaction", back_populates="category_record")
    )


class TransactionTag(SQLModel, table=True):
    """交易与标签之间的多对多关联记录。"""

    __tablename__ = "transaction_tags"

    transaction_id: str = Field(
        foreign_key="transactions.id",
        primary_key=True,
    )
    tag_id: str = Field(
        foreign_key="tags.id",
        primary_key=True,
        index=True,
    )


class Tag(SQLModel, table=True):
    """可复用的交易标签。"""

    __tablename__ = "tags"

    id: str = Field(default_factory=new_id,
                    sa_column=Column(Text, primary_key=True))
    name: str = Field(
        sa_column=Column(Text(collation="NOCASE"), nullable=False, unique=True)
    )
    description: str | None = Field(default=None, sa_column=Column(Text))
    color: str = Field(
        default="#ff0000",
        sa_column=Column(Text, nullable=False,
                         server_default=text("'#ff0000'")),
    )
    created_at: datetime = Field(sa_column=timestamp_column())
    updated_at: datetime = Field(sa_column=timestamp_column())
    transactions: list[Transaction] = Relationship(
        back_populates="tags",
        link_model=TransactionTag,
    )


class Transaction(SQLModel, table=True):
    """一笔收入、支出、转账或余额调整交易。"""

    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint(
            "amount_minor > 0",
            name="ck_transactions_amount_positive",
        ),
        CheckConstraint(
            "typeof(amount_minor) = 'integer'",
            name="ck_transactions_amount_minor_integer",
        ),
        CheckConstraint(
            "(type = 'balance_adjustment' AND "
            "balance_adjustment_direction IS NOT NULL AND "
            "balance_adjustment_direction IN ('increase', 'decrease')) OR "
            "(type <> 'balance_adjustment' AND "
            "balance_adjustment_direction IS NULL)",
            name="ck_transactions_balance_adjustment_direction",
        ),
    )

    id: str = Field(default_factory=new_id,
                    sa_column=Column(Text, primary_key=True))
    type: TransactionType = Field(
        sa_column=Column(
            SQLAlchemyEnum(
                TransactionType,
                values_callable=enum_values,
                native_enum=False,
                create_constraint=True,
                name="transaction_type",
            ),
            nullable=False,
        )
    )
    src_account_id: str | None = Field(
        foreign_key="accounts.id",
        index=True,
    )
    dest_account_id: str | None = Field(
        default=None,
        foreign_key="accounts.id",
        index=True,
    )
    amount_minor: int = Field(sa_column=Column(Integer, nullable=False))
    description: str | None = Field(default=None, sa_column=Column(Text))
    category: str | None = Field(
        foreign_key="categories.id",
        index=True,
    )
    is_refund: bool = Field(
        default=False,
        sa_column=Column(Boolean, nullable=False, server_default=text("0")),
    )
    related_transaction_id: str | None = Field(
        default=None,
        foreign_key="transactions.id",
        index=True,
    )
    balance_adjustment_direction: BalanceAdjustmentDirection | None = Field(
        default=None,
        sa_column=Column(
            SQLAlchemyEnum(
                BalanceAdjustmentDirection,
                values_callable=enum_values,
                native_enum=False,
                create_constraint=True,
                name="balance_adjustment_direction",
            )
        ),
    )
    voided_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime),
    )
    occurred_at: datetime = Field(sa_column=Column(DateTime, nullable=False))
    created_at: datetime = Field(sa_column=timestamp_column())
    updated_at: datetime = Field(sa_column=timestamp_column())

    source_account: Account | None = Relationship(
        sa_relationship=relationship(
            "Account",
            back_populates="source_transactions",
            foreign_keys="Transaction.src_account_id",
        ),
    )
    destination_account: Account | None = Relationship(
        sa_relationship=relationship(
            "Account",
            back_populates="destination_transactions",
            foreign_keys="Transaction.dest_account_id",
        ),
    )
    category_record: Category | None = Relationship(
        sa_relationship=relationship("Category", back_populates="transactions")
    )
    related_transaction: Transaction | None = Relationship(
        sa_relationship=relationship(
            "Transaction",
            back_populates="refund_transactions",
            remote_side="Transaction.id",
        ),
    )
    refund_transactions: list[Transaction] = Relationship(
        sa_relationship=relationship(
            "Transaction", back_populates="related_transaction"
        )
    )
    tags: list[Tag] = Relationship(
        back_populates="transactions",
        link_model=TransactionTag,
    )


__all__ = (
    "Account",
    "AccountType",
    "BalanceAdjustmentDirection",
    "Category",
    "Tag",
    "Transaction",
    "TransactionTag",
    "TransactionType",
    "enum_values",
    "new_id",
)
