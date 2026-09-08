"""交易查询和统计接口的响应模型。金额字段统一为整数分。"""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from app.schemas.base import ContractModel
from app.schemas.transaction import TransactionRead, TransactionSummary


class TransactionPage(ContractModel):
    items: list[TransactionRead]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)


class RefundSummary(ContractModel):
    original_amount_minor: int = Field(ge=0)
    refunded_amount_minor: int = Field(ge=0)
    remaining_refundable_amount_minor: int = Field(ge=0)
    can_refund: bool
    active_refund_count: int = Field(ge=0)


class ExpenseTransactionItem(ContractModel):
    transaction: TransactionSummary
    original_amount_minor: int = Field(gt=0)
    refunded_amount_minor: int = Field(ge=0)
    net_expense_minor: int


class ExpenseTransactionTotals(ContractModel):
    original_amount_minor: int = Field(ge=0)
    refunded_amount_minor: int = Field(ge=0)
    net_expense_minor: int


class ExpenseTransactionPage(ContractModel):
    items: list[ExpenseTransactionItem]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    totals: ExpenseTransactionTotals


class Period(ContractModel):
    start_date: date
    end_date: date
    timezone: Literal["Asia/Shanghai"] = "Asia/Shanghai"


class PeriodAmount(ContractModel):
    current_amount_minor: int
    previous_amount_minor: int
    change_amount_minor: int
    change_percent: float | None


class OverviewResponse(ContractModel):
    period: Period
    previous_period: Period
    income: PeriodAmount
    net_expense: PeriodAmount
    net_cash_flow: PeriodAmount


class CashFlowBucket(ContractModel):
    start_at: datetime
    end_at: datetime
    income_amount_minor: int
    refund_amount_minor: int
    expense_amount_minor: int
    net_cash_flow_minor: int


class CashFlowResponse(ContractModel):
    period: Period
    granularity: Literal["day", "week", "month"]
    buckets: list[CashFlowBucket]


class ExpenseBucket(ContractModel):
    start_at: datetime
    end_at: datetime
    net_expense_minor: int
    cumulative_net_expense_minor: int


class CategoryBucket(ContractModel):
    start_at: datetime
    end_at: datetime
    amount_minor: int


class ExpensesResponse(ContractModel):
    period: Period
    granularity: Literal["day", "week", "month"]
    buckets: list[ExpenseBucket]
    cumulative_start_minor: int = 0


class CategoryAmount(ContractModel):
    category_id: UUID
    name: str
    purpose: Literal["expense"]
    amount_minor: int
    direct_amount_minor: int
    previous_amount_minor: int
    change_amount_minor: int
    change_contribution_minor: int
    children: list[CategoryAmount] = Field(default_factory=list)
    time_buckets: list[CategoryBucket] = Field(default_factory=list)


class OtherCategory(ContractModel):
    category_ids: list[UUID]
    amounts: list[CategoryAmount]
    amount_minor: int


class CategoriesResponse(ContractModel):
    period: Period
    parent_category_id: UUID | None
    granularity: Literal["day", "week", "month"] = "month"
    items: list[CategoryAmount]
    top_categories: list[CategoryAmount]
    other: OtherCategory
    buckets: list[ExpenseBucket]


class TagAmount(ContractModel):
    tag_id: UUID
    name: str
    color: str
    net_expense_minor: int


class TagsResponse(ContractModel):
    period: Period
    items: list[TagAmount]


class CalendarDay(ContractModel):
    date: date
    income_amount_minor: int
    refund_amount_minor: int
    expense_amount_minor: int
    net_cash_flow_minor: int


class CalendarResponse(ContractModel):
    period: Period
    month: str
    days: list[CalendarDay]


__all__ = (
    "CalendarDay",
    "CalendarResponse",
    "CashFlowBucket",
    "CashFlowResponse",
    "CategoriesResponse",
    "CategoryAmount",
    "CategoryBucket",
    "ExpenseBucket",
    "ExpenseTransactionItem",
    "ExpenseTransactionPage",
    "ExpenseTransactionTotals",
    "ExpensesResponse",
    "OtherCategory",
    "OverviewResponse",
    "Period",
    "PeriodAmount",
    "RefundSummary",
    "TagAmount",
    "TagsResponse",
    "TransactionPage",
)
