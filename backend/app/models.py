"""根据 ``docs/contracts/db.dbml`` 派生的 SQLModel 持久化模型。"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Column, DateTime, Text, text
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
    )


class Account(SQLModel, table=True):
    """借记卡、信用卡、现金账户或其他资金账户。"""

    __tablename__ = "accounts"

    id: str = Field(default_factory=new_id, sa_column=Column(Text, primary_key=True))
    type: str = Field(nullable=False)
    name: str = Field(nullable=False)
    card_number: str | None = Field(default=None)
    description: str | None = Field(default=None)
    amount: float = Field(default=0.0, nullable=False)
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
    name: str = Field(nullable=False)
    description: str | None = Field(default=None)
    parent_category_id: str | None = Field(
        default=None,
        foreign_key="categories.id",
        index=True,
    )
    icon_color: str = Field(default="#ff0000", nullable=False)
    icon_name: str = Field(default="default_icon", nullable=False)
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


class Tag(SQLModel, table=True):
    """可复用的交易标签。"""

    __tablename__ = "tags"

    id: str = Field(default_factory=new_id, sa_column=Column(Text, primary_key=True))
    name: str = Field(nullable=False)
    description: str | None = Field(default=None)
    color: str = Field(default="#ff0000", nullable=False)
    created_at: datetime = Field(sa_column=timestamp_column())
    updated_at: datetime = Field(sa_column=timestamp_column())


class Transaction(SQLModel, table=True):
    """一笔收入、支出或转账交易。"""

    __tablename__ = "transactions"

    id: str = Field(default_factory=new_id, sa_column=Column(Text, primary_key=True))
    type: str = Field(nullable=False)
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
    amount: float = Field(nullable=False)
    description: str | None = Field(default=None)
    category: str = Field(
        foreign_key="categories.id",
        index=True,
        nullable=False,
    )
    tags: str | None = Field(default=None)
    is_refund: bool = Field(default=False, nullable=False)
    related_transaction_id: str | None = Field(
        default=None,
        foreign_key="transactions.id",
        index=True,
    )
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


__all__ = ("Account", "Category", "Tag", "Transaction", "new_id")
