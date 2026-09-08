"""六类统计和消费下钻 API。"""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.errors import VALIDATION_RESPONSES, ApiError
from app.dependencies import SessionDep
from app.schemas import (
    CalendarResponse,
    CashFlowResponse,
    CategoriesResponse,
    ExpensesResponse,
    ExpenseTransactionPage,
    OverviewResponse,
    TagsResponse,
)
from app.statistics import (
    StatisticsFilters,
    calendar,
    cash_flow,
    categories,
    expense_transaction_page,
    expense_trend,
    overview,
    tags,
)
from app.time_utils import SHANGHAI, date_bounds, month_bounds

router = APIRouter(prefix="/statistics", tags=["statistics"])
Granularity = Literal["day", "week", "month"]


def _month_shift(year: int, month: int, delta: int) -> tuple[int, int]:
    index = year * 12 + month - 1 + delta
    return index // 12, index % 12 + 1


def _resolve_period(
    start_date: date | None,
    end_date: date | None,
    *,
    cash_flow_default: bool = False,
) -> tuple[date, date, object, object]:
    """校验成对日期，并返回日期及 UTC 边界。"""

    if (start_date is None) != (end_date is None):
        raise ApiError(422, "validation_error", "startDate 和 endDate 必须成对提供")
    if start_date is None:
        if cash_flow_default:
            local_now = datetime.now(SHANGHAI)
            end_date = local_now.date().replace(day=1)
            if end_date.month == 12:
                end_date = end_date.replace(year=end_date.year + 1, month=1)
            else:
                end_date = end_date.replace(month=end_date.month + 1)
            year, month = _month_shift(end_date.year, end_date.month, -12)
            start_date = date(year, month, 1)
        else:
            start_at, end_at = month_bounds()
            start_date = start_at.astimezone(SHANGHAI).date()
            end_date = end_at.astimezone(SHANGHAI).date()
    try:
        start_at, end_at = date_bounds(start_date, end_date)
    except ValueError as error:
        raise ApiError(422, "validation_error", str(error)) from error
    return start_date, end_date, start_at, end_at


def _filters(
    account_id: UUID | None,
    category_id: UUID | None,
    include_descendants: bool,
    tag_id: UUID | None,
    q: str | None,
) -> StatisticsFilters:
    return StatisticsFilters(
        account_id=str(account_id) if account_id else None,
        category_id=str(category_id) if category_id else None,
        include_descendants=include_descendants,
        tag_id=str(tag_id) if tag_id else None,
        query=q,
    )


@router.get("/overview", response_model=OverviewResponse, responses=VALIDATION_RESPONSES, operation_id="getStatisticsOverview")
def get_overview(
    session: SessionDep,
    start_date: date | None = Query(None, alias="startDate"),
    end_date: date | None = Query(None, alias="endDate"),
    account_id: UUID | None = Query(None, alias="accountId"),
    category_id: UUID | None = Query(None, alias="categoryId"),
    include_descendants: bool = Query(False, alias="includeDescendants"),
    tag_id: UUID | None = Query(None, alias="tagId"),
    q: str | None = Query(None),
) -> OverviewResponse:
    start_date, end_date, start, end = _resolve_period(start_date, end_date)
    return overview(session, start, end, start_date, end_date, _filters(account_id, category_id, include_descendants, tag_id, q))


@router.get("/cash-flow", response_model=CashFlowResponse, responses=VALIDATION_RESPONSES, operation_id="getStatisticsCashFlow")
def get_cash_flow(
    session: SessionDep,
    start_date: date | None = Query(None, alias="startDate"),
    end_date: date | None = Query(None, alias="endDate"),
    granularity: Granularity = Query("month"),
    account_id: UUID | None = Query(None, alias="accountId"),
    category_id: UUID | None = Query(None, alias="categoryId"),
    include_descendants: bool = Query(False, alias="includeDescendants"),
    tag_id: UUID | None = Query(None, alias="tagId"),
    q: str | None = Query(None),
) -> CashFlowResponse:
    start_date, end_date, start, end = _resolve_period(start_date, end_date, cash_flow_default=True)
    return cash_flow(session, start, end, start_date, end_date, granularity, _filters(account_id, category_id, include_descendants, tag_id, q))


@router.get("/expenses", response_model=ExpensesResponse, responses=VALIDATION_RESPONSES, operation_id="getStatisticsExpenses")
def get_expenses(
    session: SessionDep,
    start_date: date | None = Query(None, alias="startDate"),
    end_date: date | None = Query(None, alias="endDate"),
    granularity: Granularity = Query("day"),
    account_id: UUID | None = Query(None, alias="accountId"),
    category_id: UUID | None = Query(None, alias="categoryId"),
    include_descendants: bool = Query(False, alias="includeDescendants"),
    tag_id: UUID | None = Query(None, alias="tagId"),
    q: str | None = Query(None),
) -> ExpensesResponse:
    start_date, end_date, start, end = _resolve_period(start_date, end_date)
    return expense_trend(session, start, end, start_date, end_date, granularity, _filters(account_id, category_id, include_descendants, tag_id, q))


@router.get("/categories", response_model=CategoriesResponse, responses=VALIDATION_RESPONSES, operation_id="getStatisticsCategories")
def get_categories(
    session: SessionDep,
    start_date: date | None = Query(None, alias="startDate"),
    end_date: date | None = Query(None, alias="endDate"),
    granularity: Granularity = Query("month"),
    parent_category_id: UUID | None = Query(None, alias="parentCategoryId"),
    account_id: UUID | None = Query(None, alias="accountId"),
    category_id: UUID | None = Query(None, alias="categoryId"),
    include_descendants: bool = Query(False, alias="includeDescendants"),
    tag_id: UUID | None = Query(None, alias="tagId"),
    q: str | None = Query(None),
) -> CategoriesResponse:
    start_date, end_date, start, end = _resolve_period(start_date, end_date)
    return categories(
        session,
        start,
        end,
        start_date,
        end_date,
        _filters(account_id, category_id, include_descendants, tag_id, q),
        str(parent_category_id) if parent_category_id else None,
        granularity,
    )


@router.get("/tags", response_model=TagsResponse, responses=VALIDATION_RESPONSES, operation_id="getStatisticsTags")
def get_tags(
    session: SessionDep,
    start_date: date | None = Query(None, alias="startDate"),
    end_date: date | None = Query(None, alias="endDate"),
    account_id: UUID | None = Query(None, alias="accountId"),
    category_id: UUID | None = Query(None, alias="categoryId"),
    include_descendants: bool = Query(False, alias="includeDescendants"),
    tag_id: UUID | None = Query(None, alias="tagId"),
    q: str | None = Query(None),
) -> TagsResponse:
    start_date, end_date, start, end = _resolve_period(start_date, end_date)
    return tags(session, start, end, start_date, end_date, _filters(account_id, category_id, include_descendants, tag_id, q))


@router.get("/calendar", response_model=CalendarResponse, responses=VALIDATION_RESPONSES, operation_id="getStatisticsCalendar")
def get_calendar(
    session: SessionDep,
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    account_id: UUID | None = Query(None, alias="accountId"),
    category_id: UUID | None = Query(None, alias="categoryId"),
    include_descendants: bool = Query(False, alias="includeDescendants"),
    tag_id: UUID | None = Query(None, alias="tagId"),
    q: str | None = Query(None),
) -> CalendarResponse:
    try:
        month_date = date.fromisoformat(f"{month}-01")
        year, next_month = _month_shift(month_date.year, month_date.month, 1)
        end_date = date(year, next_month, 1)
        start_date, end_date, start, end = _resolve_period(month_date, end_date)
    except ValueError as error:
        raise ApiError(422, "validation_error", "month 必须是有效的 YYYY-MM") from error
    return calendar(session, start, end, start_date, end_date, _filters(account_id, category_id, include_descendants, tag_id, q), month)


@router.get("/expense-transactions", response_model=ExpenseTransactionPage, responses=VALIDATION_RESPONSES, operation_id="listExpenseTransactions")
def list_expense_transactions(
    session: SessionDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    start_date: date | None = Query(None, alias="startDate"),
    end_date: date | None = Query(None, alias="endDate"),
    account_id: UUID | None = Query(None, alias="accountId"),
    category_id: UUID | None = Query(None, alias="categoryId"),
    include_descendants: bool = Query(False, alias="includeDescendants"),
    tag_id: UUID | None = Query(None, alias="tagId"),
    q: str | None = Query(None),
) -> ExpenseTransactionPage:
    start_date, end_date, start, end = _resolve_period(start_date, end_date)
    return expense_transaction_page(session, start, end, page, page_size, _filters(account_id, category_id, include_descendants, tag_id, q))


__all__ = ("router",)
