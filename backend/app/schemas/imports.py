"""人工账单导入的公开契约。"""

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, WithJsonSchema, model_validator

from app.import_parser import MAX_MINOR
from app.schemas.base import ContractModel
from app.time_utils import AwareDateTime

UtcTimestamp = Annotated[
    datetime,
    WithJsonSchema({"type": "string", "format": "date-time"}, mode="serialization"),
]

ImportStatus = Literal[
    "ready",
    "needs_account",
    "needs_category",
    "duplicate",
    "skipped",
    "unsupported",
    "refund_pending",
    "imported",
]


class SourceFields(ContractModel):
    source_id: str
    merchant_order_id: str
    counterparty: str
    product: str
    payment_method: str
    platform_category: str
    platform_status: str
    direction: str
    amount: str
    occurred_at: Annotated[str, WithJsonSchema({"type": "string"}, mode="serialization")]
    row_numbers: list[int]



class SourceSummary(ContractModel):
    input_rows: int
    parse_counts: dict[str, int]
    source_amount_minor: dict[str, int]
    start_at: str | None
    end_at: str | None


class ImportSummary(ContractModel):
    input_rows: int
    counts: dict[str, int]
    selected_count: int
    unresolved_count: int
    income_minor: int
    expense_minor: int
    excluded_minor: int
    source: SourceSummary


class ImportRowRead(ContractModel):
    id: UUID
    row_number: int
    source_id: str
    status: ImportStatus
    reason: str | None
    included: bool
    editable: bool
    type: Literal["income", "expense"] | None
    amount_minor: int
    occurred_at: UtcTimestamp | None
    description: str
    payment_key: str
    account_id: UUID | None
    category_id: UUID | None
    transaction_id: UUID | None
    duplicate_batch_id: UUID | None = None
    original: SourceFields
    similar_transaction_ids: list[UUID] = Field(default_factory=list)


class ImportBatchRead(ContractModel):
    id: UUID
    provider: Literal["alipay", "wechat"]
    filename: str
    sha256: str
    parser_version: str
    status: Literal["draft", "committed"]
    version: int
    created_at: UtcTimestamp
    updated_at: UtcTimestamp
    committed_at: UtcTimestamp | None
    summary: ImportSummary
    payment_keys: list[str]
    items: list[ImportRowRead]
    total: int
    page: int
    page_size: int


class ImportHistoryItem(ContractModel):
    id: UUID
    provider: Literal["alipay", "wechat"]
    filename: str
    status: Literal["draft", "committed"]
    version: int
    created_at: UtcTimestamp
    committed_at: UtcTimestamp | None
    input_rows: int


class ImportHistory(ContractModel):
    items: list[ImportHistoryItem]
    total: int
    page: int
    page_size: int


class ImportChange(ContractModel):
    row_ids: list[UUID] = Field(default_factory=list, max_length=10000)
    payment_key: str | None = Field(default=None, max_length=500)
    type: Literal["income", "expense"] | None = None
    account_id: UUID | None = None
    category_id: UUID | None = None
    included: bool | None = None
    amount_minor: int | None = Field(default=None, gt=0, le=MAX_MINOR)
    occurred_at: AwareDateTime | None = None
    description: str | None = Field(default=None, max_length=2000)
    match_type: Literal["income", "expense"] | None = None
    remember_mapping: bool = False

    @model_validator(mode="after")
    def require_selector(self):
        if bool(self.row_ids) == (self.payment_key is not None):
            raise ValueError("请选择行 ID 或支付方式之一")
        if self.match_type is not None and self.payment_key is None:
            raise ValueError("用途过滤仅适用于支付方式选择")
        if self.remember_mapping and (self.payment_key is None or not self.account_id):
            raise ValueError("记住映射必须提供支付方式和账户")
        for key in ("type", "included", "amount_minor", "occurred_at", "description"):
            if key in self.model_fields_set and getattr(self, key) is None:
                raise ValueError(f"{key} 不能为 null")
        return self


class ImportPatch(ContractModel):
    version: int = Field(gt=0)
    changes: list[ImportChange] = Field(min_length=1, max_length=100)


class ImportCommit(ContractModel):
    version: int = Field(gt=0)
