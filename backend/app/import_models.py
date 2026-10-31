"""账单导入草稿、来源占用与账户映射。"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlmodel import Field, SQLModel

from app.models import new_id, timestamp_column


class ImportBatch(SQLModel, table=True):
    __tablename__ = "import_batches"
    __table_args__ = (
        CheckConstraint(
            "provider IN ('alipay', 'wechat')", name="ck_import_batch_provider"
        ),
        CheckConstraint(
            "status IN ('draft', 'committed')", name="ck_import_batch_status"
        ),
        CheckConstraint("version > 0", name="ck_import_batch_version"),
    )
    id: str = Field(default_factory=new_id, primary_key=True)
    provider: str
    filename: str
    sha256: str
    parser_version: str = "1"
    status: str = "draft"
    version: int = Field(default=1, sa_column=Column(Integer, nullable=False))
    summary: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSON, nullable=False)
    )
    created_at: datetime = Field(sa_column=timestamp_column())
    updated_at: datetime = Field(sa_column=timestamp_column(update_on_change=True))
    committed_at: datetime | None = Field(default=None, sa_column=Column(DateTime))


class ImportRow(SQLModel, table=True):
    __tablename__ = "import_rows"
    __table_args__ = (
        UniqueConstraint("batch_id", "row_number", name="uq_import_row_number"),
        CheckConstraint("amount_minor >= 0", name="ck_import_row_amount"),
    )
    id: str = Field(default_factory=new_id, primary_key=True)
    batch_id: str = Field(foreign_key="import_batches.id", index=True)
    row_number: int
    source_id: str = Field(index=True)
    original: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False))
    state: str
    reason: str | None = None
    included: bool = True
    transaction_type: str | None = None
    amount_minor: int
    occurred_at: datetime | None = Field(default=None, sa_column=Column(DateTime))
    description: str = Field(default="", sa_column=Column(Text, nullable=False))
    payment_key: str
    account_id: str | None = Field(
        default=None, foreign_key="accounts.id", ondelete="SET NULL"
    )
    category_id: str | None = Field(
        default=None, foreign_key="categories.id", ondelete="SET NULL"
    )
    transaction_id: str | None = Field(default=None, foreign_key="transactions.id")


class ImportSource(SQLModel, table=True):
    """仅提交成功的来源占用唯一键；不同草稿可以引用同一来源。"""

    __tablename__ = "import_sources"
    __table_args__ = (
        UniqueConstraint("provider", "source_id", name="uq_import_source"),
    )
    id: str = Field(default_factory=new_id, primary_key=True)
    provider: str
    source_id: str
    batch_id: str = Field(foreign_key="import_batches.id")
    row_id: str = Field(foreign_key="import_rows.id", unique=True)
    transaction_id: str = Field(foreign_key="transactions.id", unique=True)


class ImportAccountMapping(SQLModel, table=True):
    __tablename__ = "import_account_mappings"
    __table_args__ = (
        UniqueConstraint("provider", "payment_key", name="uq_import_mapping"),
    )
    id: str = Field(default_factory=new_id, primary_key=True)
    provider: str
    payment_key: str
    # 未被交易引用的账户删除后，映射自动失效。
    account_id: str = Field(foreign_key="accounts.id", ondelete="CASCADE")
