"""服务端统计查询：所有金额均以整数分计算。"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal

from sqlalchemy import func
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
    """读取时间范围内原支出，并一次性聚合其全部有效退款。"""

    statement = transaction_statement(
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
    ).with_only_columns(
        Transaction.id,
        Transaction.occurred_at,
        Transaction.amount_minor,
        Transaction.category,
    )
    rows = list(session.execute(statement).all())
    if not rows:
        return []
    ids = [row[0] for row in rows]
    refund_rows = session.execute(
        select(
            Transaction.refund_of_transaction_id,
            func.coalesce(func.sum(Transaction.amount_minor), 0),
        ).where(
            Transaction.type == TransactionType.EXPENSE_REFUND,
            Transaction.is_void.is_(False),
            Transaction.refund_of_transaction_id.in_(ids),
        ).group_by(Transaction.refund_of_transaction_id)
    )
    refunds = {row[0]: int(row[1] or 0) for row in refund_rows}
    return [
        ExpenseRecord(row[0], stored_datetime_as_utc(row[1]), int(row[2]), row[3], refunds.get(row[0], 0))
        for row in rows
    ]


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
    records = _records(session, start, end, filters)
    by_id = {record.id: record.net_expense_minor for record in records}
    if not by_id:
        return TagsResponse(period=_period(start_date, end_date), items=[])
    rows = session.execute(
        select(TransactionTag.tag_id, TransactionTag.transaction_id)
        .where(TransactionTag.transaction_id.in_(by_id))
    )
    totals: dict[str, int] = defaultdict(int)
    for tag_id, transaction_id in rows:
        totals[tag_id] += by_id[transaction_id]
    tag_rows = {
        tag.id: tag for tag in session.exec(select(Tag).where(Tag.id.in_(totals)))
    }
    items = [
        TagAmount(tag_id=tag.id, name=tag.name, color=tag.color, net_expense_minor=totals[tag.id])
        for tag in tag_rows.values()
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
    records = _records(session, start, end, filters)
    records.sort(key=lambda item: (item.occurred_at, item.id), reverse=True)
    total = len(records)
    selected = records[(page - 1) * page_size : page * page_size]
    ids = [record.id for record in selected]
    transactions = {item.id: item for item in session.exec(select(Transaction).where(Transaction.id.in_(ids)))}
    items = [
        ExpenseTransactionItem(
            transaction=TransactionSummary.from_orm_model(transactions[record.id]),
            original_amount_minor=record.amount_minor,
            refunded_amount_minor=record.refunded_amount_minor,
            net_expense_minor=record.net_expense_minor,
        )
        for record in selected
    ]
    return ExpenseTransactionPage(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        totals=ExpenseTransactionTotals(
            original_amount_minor=sum(item.amount_minor for item in records),
            refunded_amount_minor=sum(item.refunded_amount_minor for item in records),
            net_expense_minor=sum(item.net_expense_minor for item in records),
        ),
    )


__all__ = (
    "StatisticsFilters", "calendar", "cash_flow", "categories", "expense_transaction_page",
    "expense_trend", "overview", "tags",
)
