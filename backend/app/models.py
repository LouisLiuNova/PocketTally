"""SQLModel persistence models derived from ``docs/contracts/db.dbml``."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Column, DateTime, Text, text
from sqlmodel import Field, Relationship, SQLModel

def new_id() -> str:
    """Return the string UUID representation used by the SQLite schema."""

    return str(uuid4())


def timestamp_column() -> Column[datetime]:
    """Create a timestamp column with SQLite's contract-defined default."""

    return Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class Account(SQLModel, table=True):
    """A debit card, credit card, cash account, or other money account."""

    __tablename__ = "accounts"

    id: str = Field(default_factory=new_id, sa_column=Column(Text, primary_key=True))
    type: str = Field(nullable=False)
    name: str = Field(nullable=False)
    card_number: str | None = Field(default=None)
    description: str | None = Field(default=None)
    amount: float = Field(default=0.0, nullable=False)
    created_at: datetime = Field(sa_column=timestamp_column())
    updated_at: datetime = Field(sa_column=timestamp_column())

    source_transactions: list["Transaction"] = Relationship(
        back_populates="source_account",
        sa_relationship_kwargs={"foreign_keys": "Transaction.src_account_id"},
    )
    destination_transactions: list["Transaction"] = Relationship(
        back_populates="destination_account",
        sa_relationship_kwargs={"foreign_keys": "Transaction.dest_account_id"},
    )


class Category(SQLModel, table=True):
    """A transaction category, optionally nested below another category."""

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

    parent_category: Optional["Category"] = Relationship(
        back_populates="child_categories",
        sa_relationship_kwargs={"remote_side": "Category.id"},
    )
    child_categories: list["Category"] = Relationship(back_populates="parent_category")
    transactions: list["Transaction"] = Relationship(back_populates="category_record")


class Tag(SQLModel, table=True):
    """A reusable transaction label."""

    __tablename__ = "tags"

    id: str = Field(default_factory=new_id, sa_column=Column(Text, primary_key=True))
    name: str = Field(nullable=False)
    description: str | None = Field(default=None)
    color: str = Field(default="#ff0000", nullable=False)
    created_at: datetime = Field(sa_column=timestamp_column())
    updated_at: datetime = Field(sa_column=timestamp_column())


class Transaction(SQLModel, table=True):
    """A single income, expense, or transfer transaction."""

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

    source_account: "Account" = Relationship(
        back_populates="source_transactions",
        sa_relationship_kwargs={"foreign_keys": "Transaction.src_account_id"},
    )
    destination_account: Optional["Account"] = Relationship(
        back_populates="destination_transactions",
        sa_relationship_kwargs={"foreign_keys": "Transaction.dest_account_id"},
    )
    category_record: "Category" = Relationship(back_populates="transactions")
    related_transaction: Optional["Transaction"] = Relationship(
        back_populates="refund_transactions",
        sa_relationship_kwargs={"remote_side": "Transaction.id"},
    )
    refund_transactions: list["Transaction"] = Relationship(
        back_populates="related_transaction"
    )


__all__ = ("Account", "Category", "Tag", "Transaction", "new_id")
