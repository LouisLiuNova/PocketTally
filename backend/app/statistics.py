"""服务端统计查询：所有金额均以整数分计算。"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from sqlalchemy import func
from sqlalchemy.orm import aliased, joinedload, selectinload
from sqlmodel import Session, select

from app.models import (
    Category,
    CategoryPurpose,
    Tag,
    Transaction,
    TransactionTag,
    TransactionType,
)
from app.resources import category_descendant_ids, transaction_statement
from app.schemas.statistics import (
    CalendarDay,
    CalendarResponse,
    CashFlowBucket,
    CashFlowResponse,
    CategoriesResponse,
    CategoryAmount,
    CategoryBucket,
    ExpenseBucket,
    ExpensesResponse,
    ExpenseTransactionItem,
    ExpenseTransactionPage,
    ExpenseTransactionTotals,
    OverviewResponse,
    Period,
    PeriodAmount,
    TagAmount,
    TagsResponse,
)
from app.schemas.transaction import TransactionSummary
from app.time_utils import (
    SHANGHAI,
    add_bucket,
    bucket_start,
    previous_period,
    stored_datetime_as_utc,
)


@dataclass(frozen=True, slots=True)
class ExpenseRecord:
    id: str
    occurred_at: datetime
    amount_minor: int
    category_id: str
    refunded_amount_minor: int

    @property
    def net_expense_minor(self) -> int:
        return self.amount_minor - self.refunded_amount_minor


@dataclass(frozen=True, slots=True)
class StatisticsFilters:
    account_id: str | None = None
    category_id: str | None = None
    include_descendants: bool = False
    tag_id: str | None = None
    query: str | None = None


def _records(
    session: Session,
    start: datetime,
    end: datetime,
    filters: StatisticsFilters = StatisticsFilters(),
) -> list[ExpenseRecord]:
    """读取时间范围内原支出，并由数据库关联其全部有效退款。"""

    rows = session.execute(_net_expense_statement(session, start, end, filters))
    return [
        ExpenseRecord(
            row.id,
            stored_datetime_as_utc(row.occurred_at),
            int(row.amount_minor),
            row.category_id,
            int(row.refunded_amount_minor),
        )
        for row in rows
    ]


def _filtered_expense_statement(
    session: Session,
    start: datetime,
    end: datetime,
    filters: StatisticsFilters,
):
    """构造包含完整统计筛选语义的有效原支出查询。"""

    return transaction_statement(
        session,
        start_at=start,
        end_at=end,
        transaction_type=TransactionType.EXPENSE,
        account_id=filters.account_id,
        category_id=filters.category_id,
        include_descendants=filters.include_descendants,
        tag_id=filters.tag_id,
        query=filters.query,
        status="active",
    )


def _refund_totals_subquery():
    """按原支出聚合全部有效退款，不展开原支出 ID 参数。"""

    return (
        select(
            Transaction.refund_of_transaction_id.label("transaction_id"),
            func.coalesce(func.sum(Transaction.amount_minor), 0).label(
                "refunded_amount_minor"
            ),
        )
        .where(
            Transaction.type == TransactionType.EXPENSE_REFUND,
            Transaction.is_void.is_(False),
        )
        .group_by(Transaction.refund_of_transaction_id)
        .subquery("expense_refunds")
    )


def _net_expense_statement(
    session: Session,
    start: datetime,
    end: datetime,
    filters: StatisticsFilters,
):
    """构造筛选后原支出及其有效退款净额的数据库查询。"""

    filtered_statement = _filtered_expense_statement(session, start, end, filters)
    filtered = filtered_statement.with_only_columns(
        Transaction.id,
        Transaction.occurred_at,
        Transaction.amount_minor,
        Transaction.category.label("category_id"),
    ).subquery("filtered_expenses")
    refunds = _refund_totals_subquery()
    refunded_amount = func.coalesce(refunds.c.refunded_amount_minor, 0)
    return (
        select(
            filtered.c.id,
            filtered.c.occurred_at,
            filtered.c.amount_minor,
            filtered.c.category_id,
            refunded_amount.label("refunded_amount_minor"),
            (filtered.c.amount_minor - refunded_amount).label("net_expense_minor"),
        )
        .select_from(filtered)
        .outerjoin(refunds, refunds.c.transaction_id == filtered.c.id)
    )


def _events(
    session: Session,
    start: datetime,
    end: datetime,
    filters: StatisticsFilters = StatisticsFilters(),
) -> list[tuple[datetime, TransactionType, int]]:
    """读取现金流所需的收入、支出和退款事件。"""

    conditions = [
        Transaction.is_void.is_(False),
        Transaction.occurred_at >= start,
        Transaction.occurred_at < end,
        Transaction.type.in_((
            TransactionType.INCOME,
            TransactionType.EXPENSE,
            TransactionType.EXPENSE_REFUND,
        )),
    ]
    if filters.account_id:
        conditions.append(
            (Transaction.src_account_id == filters.account_id)
            | (Transaction.dest_account_id == filters.account_id)
        )
    if filters.query:
        escaped = filters.query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        conditions.append(Transaction.description.like(f"%{escaped}%", escape="\\"))
    if filters.category_id:
        category_ids = {filters.category_id}
        if filters.include_descendants:
            category_ids = category_descendant_ids(session, filters.category_id)
        conditions.append(Transaction.category.in_(category_ids))
    if filters.tag_id:
        conditions.append(
            select(TransactionTag.transaction_id)
            .where(
                TransactionTag.transaction_id == Transaction.id,
                TransactionTag.tag_id == filters.tag_id,
            )
            .exists()
        )
    rows = session.execute(
        select(Transaction.occurred_at, Transaction.type, Transaction.amount_minor)
        .where(*conditions)
    )
    return [(stored_datetime_as_utc(row[0]), TransactionType(row[1]), int(row[2])) for row in rows]


def _amounts(records: list[ExpenseRecord]) -> tuple[int, int]:
    """计算原支出和退款抵减后的净支出。"""

    return sum(item.amount_minor for item in records), sum(
        item.net_expense_minor for item in records
    )


def _change(current: int, previous: int) -> tuple[int, float | None]:
    """按上期绝对值计算两位小数变化百分比。"""

    delta = current - previous
    return delta, round(delta / abs(previous) * 100, 2) if previous else None


def _period(start: date, end: date) -> Period:
    return Period(start_date=start, end_date=end)


def overview(
    session: Session,
    start: datetime,
    end: datetime,
    start_date: date,
    end_date: date,
    filters: StatisticsFilters = StatisticsFilters(),
) -> OverviewResponse:
    """计算期间概览及相邻等长期间比较。"""

    previous_start, previous_end = previous_period(start, end)
    current_records = _records(session, start, end, filters)
    previous_records = _records(session, previous_start, previous_end, filters)
    current_events = _events(session, start, end, filters)
    previous_events = _events(session, previous_start, previous_end, filters)

    def income(events: list[tuple[datetime, TransactionType, int]]) -> int:
        return sum(amount for _, kind, amount in events if kind is TransactionType.INCOME)

    def cash(events: list[tuple[datetime, TransactionType, int]]) -> int:
        return sum(
            amount if kind is not TransactionType.EXPENSE else -amount
            for _, kind, amount in events
        )

    current_net = _amounts(current_records)[1]
    previous_net = _amounts(previous_records)[1]
    current_income, previous_income = income(current_events), income(previous_events)
    current_cash, previous_cash = cash(current_events), cash(previous_events)

    def metric(current: int, previous: int) -> PeriodAmount:
        delta, percent = _change(current, previous)
        return PeriodAmount(
            current_amount_minor=current,
            previous_amount_minor=previous,
            change_amount_minor=delta,
            change_percent=percent,
        )

    return OverviewResponse(
        period=_period(start_date, end_date),
        previous_period=_period(
            previous_start.astimezone(SHANGHAI).date(),
            previous_end.astimezone(SHANGHAI).date(),
        ),
        income=metric(current_income, previous_income),
        net_expense=metric(current_net, previous_net),
        net_cash_flow=metric(current_cash, previous_cash),
    )


def _bucket_range(start: datetime, end: datetime, granularity: str) -> list[tuple[datetime, datetime]]:
    """生成连续并裁剪首尾的时间桶。"""

    cursor = bucket_start(start, granularity)
    result: list[tuple[datetime, datetime]] = []
    while cursor < end:
        next_cursor = add_bucket(cursor, granularity)
        result.append((max(cursor, start), min(next_cursor, end)))
        cursor = next_cursor
    return result


def cash_flow(
    session: Session,
    start: datetime,
    end: datetime,
    start_date: date,
    end_date: date,
    granularity: Literal["day", "week", "month"],
    filters: StatisticsFilters = StatisticsFilters(),
) -> CashFlowResponse:
    buckets = _bucket_range(start, end, granularity)
    values = [defaultdict(int) for _ in buckets]
    bucket_indexes = {
        bucket_start(bucket_start_at, granularity): index
        for index, (bucket_start_at, _) in enumerate(buckets)
    }
    for occurred_at, kind, amount in _events(session, start, end, filters):
        index = bucket_indexes.get(bucket_start(occurred_at, granularity))
        if index is not None:
            values[index][kind.value] += amount
    return CashFlowResponse(
        period=_period(start_date, end_date),
        granularity=granularity,
        buckets=[
            CashFlowBucket(
                start_at=bucket_start_at,
                end_at=bucket_end_at,
                income_amount_minor=value[TransactionType.INCOME.value],
                refund_amount_minor=value[TransactionType.EXPENSE_REFUND.value],
                expense_amount_minor=value[TransactionType.EXPENSE.value],
                net_cash_flow_minor=(
                    value[TransactionType.INCOME.value]
                    + value[TransactionType.EXPENSE_REFUND.value]
                    - value[TransactionType.EXPENSE.value]
                ),
            )
            for (bucket_start_at, bucket_end_at), value in zip(buckets, values)
        ],
    )


def expense_trend(
    session: Session,
    start: datetime,
    end: datetime,
    start_date: date,
    end_date: date,
    granularity: Literal["day", "week", "month"],
    filters: StatisticsFilters = StatisticsFilters(),
) -> ExpensesResponse:
    records = _records(session, start, end, filters)
    bucket_values: dict[datetime, int] = defaultdict(int)
    for record in records:
        bucket_values[bucket_start(record.occurred_at, granularity)] += record.net_expense_minor
    cumulative = 0
    buckets = []
    for bucket_start_at, bucket_end_at in _bucket_range(start, end, granularity):
        amount = bucket_values[bucket_start_at]
        cumulative += amount
        buckets.append(
            ExpenseBucket(
                start_at=bucket_start_at,
                end_at=bucket_end_at,
                net_expense_minor=amount,
                cumulative_net_expense_minor=cumulative,
            )
        )
    return ExpensesResponse(
        period=_period(start_date, end_date),
        granularity=granularity,
        buckets=buckets,
        cumulative_start_minor=0,
    )


def _category_tree(
    categories: list[Category],
    current: dict[str, int],
    previous: dict[str, int],
    *,
    parent_id: str | None,
) -> list[CategoryAmount]:
    children: dict[str | None, list[Category]] = defaultdict(list)
    for category in categories:
        children[category.parent_category_id].append(category)

    def build(category: Category, visiting: set[str]) -> CategoryAmount:
        if category.id in visiting:
            return CategoryAmount(
                category_id=category.id, name=category.name, purpose="expense",
                amount_minor=current.get(category.id, 0),
                direct_amount_minor=current.get(category.id, 0),
                previous_amount_minor=previous.get(category.id, 0),
                change_amount_minor=current.get(category.id, 0) - previous.get(category.id, 0),
                change_contribution_minor=current.get(category.id, 0) - previous.get(category.id, 0),
            )
        descendants = [build(child, visiting | {category.id}) for child in children.get(category.id, [])]
        descendants.sort(key=lambda item: (-item.amount_minor, str(item.category_id)))
        amount = current.get(category.id, 0) + sum(child.amount_minor for child in descendants)
        prior = previous.get(category.id, 0) + sum(child.previous_amount_minor for child in descendants)
        change = amount - prior
        return CategoryAmount(
            category_id=category.id,
            name=category.name,
            purpose="expense",
            amount_minor=amount,
            direct_amount_minor=current.get(category.id, 0),
            previous_amount_minor=prior,
            change_amount_minor=change,
            change_contribution_minor=change,
            children=descendants,
        )

    return [build(item, set()) for item in children.get(parent_id, [])]


def _attach_category_buckets(
    nodes: list[CategoryAmount],
    values: dict[str, dict[datetime, int]],
    ranges: list[tuple[datetime, datetime]],
) -> None:
    """给分类树每个节点附加连续的时间桶。"""

    for node in nodes:
        node.time_buckets = [
            CategoryBucket(
                start_at=start_at,
                end_at=end_at,
                amount_minor=values[str(node.category_id)].get(start_at, 0),
            )
            for start_at, end_at in ranges
        ]
        _attach_category_buckets(node.children, values, ranges)


def categories(
    session: Session,
    start: datetime,
    end: datetime,
    start_date: date,
    end_date: date,
    filters: StatisticsFilters = StatisticsFilters(),
    parent_category_id: str | None = None,
    granularity: Literal["day", "week", "month"] = "month",
) -> CategoriesResponse:
    current_records = _records(session, start, end, filters)
    previous_start, previous_end = previous_period(start, end)
    previous_records = _records(session, previous_start, previous_end, filters)
    current = defaultdict(int)
    previous = defaultdict(int)
    for record in current_records:
        current[record.category_id] += record.net_expense_minor
    for record in previous_records:
        previous[record.category_id] += record.net_expense_minor
    category_rows = list(session.exec(select(Category).where(Category.purpose == CategoryPurpose.EXPENSE)))
    tree = _category_tree(category_rows, current, previous, parent_id=parent_category_id)
    tree.sort(key=lambda item: (-item.amount_minor, str(item.category_id)))
    parent_by_id = {item.id: item.parent_category_id for item in category_rows}
    category_buckets: dict[str, dict[datetime, int]] = defaultdict(lambda: defaultdict(int))
    for record in current_records:
        current_category: str | None = record.category_id
        seen: set[str] = set()
        while current_category is not None and current_category not in seen:
            seen.add(current_category)
            category_buckets[current_category][bucket_start(record.occurred_at, granularity)] += record.net_expense_minor
            current_category = parent_by_id.get(current_category)
    _attach_category_buckets(tree, category_buckets, _bucket_range(start, end, granularity))
    overall_values: dict[datetime, int] = defaultdict(int)
    for record in current_records:
        overall_values[bucket_start(record.occurred_at, granularity)] += record.net_expense_minor
    cumulative = 0
    overall_buckets: list[ExpenseBucket] = []
    for bucket_start_at, bucket_end_at in _bucket_range(start, end, granularity):
        amount = overall_values[bucket_start_at]
        cumulative += amount
        overall_buckets.append(
            ExpenseBucket(
                start_at=bucket_start_at,
                end_at=bucket_end_at,
                net_expense_minor=amount,
                cumulative_net_expense_minor=cumulative,
            )
        )
    top = tree[:5]
    remainder = tree[5:]
    return CategoriesResponse(
        period=_period(start_date, end_date),
        parent_category_id=parent_category_id,
        granularity=granularity,
        items=tree,
        top_categories=top,
        other={
            "category_ids": [item.category_id for item in remainder],
            "amounts": remainder,
            "amount_minor": sum(item.amount_minor for item in remainder),
        },
        buckets=overall_buckets,
    )


def tags(
    session: Session,
    start: datetime,
    end: datetime,
    start_date: date,
    end_date: date,
    filters: StatisticsFilters = StatisticsFilters(),
) -> TagsResponse:
    net_expenses = _net_expense_statement(session, start, end, filters).subquery(
        "net_expenses"
    )
    rows = session.execute(
        select(
            Tag.id,
            Tag.name,
            Tag.color,
            func.sum(net_expenses.c.net_expense_minor).label("net_expense_minor"),
        )
        .select_from(net_expenses)
        .join(
            TransactionTag,
            TransactionTag.transaction_id == net_expenses.c.id,
        )
        .join(Tag, Tag.id == TransactionTag.tag_id)
        .group_by(Tag.id, Tag.name, Tag.color)
    )
    items = [
        TagAmount(
            tag_id=row.id,
            name=row.name,
            color=row.color,
            net_expense_minor=int(row.net_expense_minor or 0),
        )
        for row in rows
    ]
    items.sort(key=lambda item: (-item.net_expense_minor, str(item.tag_id)))
    return TagsResponse(period=_period(start_date, end_date), items=items)


def calendar(
    session: Session,
    start: datetime,
    end: datetime,
    start_date: date,
    end_date: date,
    filters: StatisticsFilters = StatisticsFilters(),
    month: str = "",
) -> CalendarResponse:
    values: dict[date, defaultdict[str, int]] = defaultdict(lambda: defaultdict(int))
    for occurred_at, kind, amount in _events(session, start, end, filters):
        values[occurred_at.astimezone(SHANGHAI).date()][kind.value] += amount
    days = []
    cursor = start_date
    while cursor < end_date:
        value = values[cursor]
        income = value[TransactionType.INCOME.value]
        refund = value[TransactionType.EXPENSE_REFUND.value]
        expense = value[TransactionType.EXPENSE.value]
        days.append(CalendarDay(
            date=cursor,
            income_amount_minor=income,
            refund_amount_minor=refund,
            expense_amount_minor=expense,
            net_cash_flow_minor=income + refund - expense,
        ))
        cursor = date.fromordinal(cursor.toordinal() + 1)
    return CalendarResponse(period=_period(start_date, end_date), month=month, days=days)


def expense_transaction_page(
    session: Session,
    start: datetime,
    end: datetime,
    page: int,
    page_size: int,
    filters: StatisticsFilters = StatisticsFilters(),
) -> ExpenseTransactionPage:
    """按数据库过滤、聚合和分页消费明细。

    原支出的有效退款不按退款发生时间过滤，而是通过退款关联回原支出后
    聚合。这保持了报表“原支出发生时间归属期间、退款抵减原支出”的口径，
    同时避免把所有匹配支出加载到 Python 再切页。
    """

    filtered = _filtered_expense_statement(session, start, end, filters)
    net_expenses = _net_expense_statement(session, start, end, filters).subquery(
        "net_expenses"
    )
    totals_row = session.execute(
        select(
            func.count(net_expenses.c.id),
            func.coalesce(func.sum(net_expenses.c.amount_minor), 0),
            func.coalesce(func.sum(net_expenses.c.refunded_amount_minor), 0),
        )
        .select_from(net_expenses)
    ).one()
    total = int(totals_row[0] or 0)
    original_amount_minor = int(totals_row[1] or 0)
    refunded_amount_minor = int(totals_row[2] or 0)

    refund_transaction = aliased(Transaction)
    refund_amount_for_page = (
        select(func.coalesce(func.sum(refund_transaction.amount_minor), 0))
        .where(
            refund_transaction.type == TransactionType.EXPENSE_REFUND,
            refund_transaction.is_void.is_(False),
            refund_transaction.refund_of_transaction_id == Transaction.id,
        )
        .correlate(Transaction)
        .scalar_subquery()
    )
    page_rows = session.execute(
        filtered
        .options(
            joinedload(Transaction.source_account),
            joinedload(Transaction.destination_account),
            joinedload(Transaction.category_record),
            joinedload(Transaction.refund_of_transaction),
            selectinload(Transaction.tags),
        )
        .add_columns(refund_amount_for_page.label("refunded_amount_minor"))
        .order_by(Transaction.occurred_at.desc(), Transaction.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).unique().all()
    items = [
        ExpenseTransactionItem(
            transaction=TransactionSummary.from_orm_model(transaction),
            original_amount_minor=int(transaction.amount_minor),
            refunded_amount_minor=int(refunded),
            net_expense_minor=int(transaction.amount_minor) - int(refunded),
        )
        for transaction, refunded in page_rows
    ]
    return ExpenseTransactionPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        totals=ExpenseTransactionTotals(
            original_amount_minor=original_amount_minor,
            refunded_amount_minor=refunded_amount_minor,
            net_expense_minor=original_amount_minor - refunded_amount_minor,
        ),
    )


__all__ = (
    "StatisticsFilters", "calendar", "cash_flow", "categories", "expense_transaction_page",
    "expense_trend", "overview", "tags",
)
