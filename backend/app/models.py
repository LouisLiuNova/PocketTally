"""根据 ``docs/contracts/db.dbml`` 派生的 SQLModel 持久化模型。"""

from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import REAL, Boolean, Column, DateTime, Text, func, text
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


def transaction_type_values(enum_class: type[TransactionType]) -> list[str]:
    """返回交易类型实际写入数据库的英文枚举值。

    Args:
        enum_class: SQLAlchemy 传入的交易类型枚举类。

    Returns:
        按枚举声明顺序排列的持久化值。
    """

    return [member.value for member in enum_class]


class Account(SQLModel, table=True):
    """借记卡、信用卡、现金账户或其他资金账户。"""

    __tablename__ = "accounts"

    id: str = Field(default_factory=new_id, sa_column=Column(Text, primary_key=True))
    type: str = Field(sa_column=Column(Text, nullable=False))
    name: str = Field(
        sa_column=Column(Text(collation="NOCASE"), nullable=False, unique=True)
    )
    card_number: str | None = Field(default=None, sa_column=Column(Text))
    description: str | None = Field(default=None, sa_column=Column(Text))
    amount: float = Field(
        default=0.0,
        sa_column=Column(REAL, nullable=False, server_default=text("0.0")),
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

    id: str = Field(default_factory=new_id, sa_column=Column(Text, primary_key=True))
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
        sa_column=Column(Text, nullable=False, server_default=text("'#ff0000'")),
    )
    icon_name: str = Field(
        default="default_icon",
        sa_column=Column(Text, nullable=False, server_default=text("'default_icon'")),
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
        sa_relationship=relationship("Category", back_populates="parent_category")
    )
    transactions: list[Transaction] = Relationship(
        sa_relationship=relationship("Transaction", back_populates="category_record")
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

    id: str = Field(default_factory=new_id, sa_column=Column(Text, primary_key=True))
    name: str = Field(
        sa_column=Column(Text(collation="NOCASE"), nullable=False, unique=True)
    )
    description: str | None = Field(default=None, sa_column=Column(Text))
    color: str = Field(
        default="#ff0000",
        sa_column=Column(Text, nullable=False, server_default=text("'#ff0000'")),
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

    id: str = Field(default_factory=new_id, sa_column=Column(Text, primary_key=True))
    type: TransactionType = Field(
        sa_column=Column(
            SQLAlchemyEnum(
                TransactionType,
                values_callable=transaction_type_values,
                native_enum=False,
                create_constraint=True,
                name="transaction_type",
            ),
            nullable=False,
        )
    )
    src_account_id: str = Field(
        foreign_key="accounts.id",
        index=True,
        nullable=False,
    )
    dest_account_id: str | None = Field(
        default=None,
        foreign_key="accounts.id",
        index=True,
    )
    amount: float = Field(sa_column=Column(REAL, nullable=False))
    description: str | None = Field(default=None, sa_column=Column(Text))
    category: str = Field(
        foreign_key="categories.id",
        index=True,
        nullable=False,
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
    occurred_at: datetime = Field(sa_column=Column(DateTime, nullable=False))
    created_at: datetime = Field(sa_column=timestamp_column())
    updated_at: datetime = Field(sa_column=timestamp_column())

    source_account: Account = Relationship(
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
    category_record: Category = Relationship(
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
    "Category",
    "Tag",
    "Transaction",
    "TransactionTag",
    "TransactionType",
    "new_id",
    "transaction_type_values",
)
