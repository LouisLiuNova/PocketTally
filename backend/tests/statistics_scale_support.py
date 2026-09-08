"""Issue #16 十万笔统计正确性与性能验收共用数据。"""

from dataclasses import dataclass
from datetime import UTC, datetime

from httpx import AsyncClient
from sqlalchemy import Engine

from app.models import Transaction, TransactionTag, TransactionType

TRANSACTION_COUNT = 100_000
ACTIVE_REFUND_COUNT = 100
VOID_REFUND_COUNT = 100
EXPENSE_AMOUNT_MINOR = 100
REFUND_AMOUNT_MINOR = 20
PERIOD = {"startDate": "2026-01-01", "endDate": "2026-02-01"}


@dataclass(frozen=True, slots=True)
class ScaleLedger:
    """压力账本资源 ID 与预期聚合。"""

    account_id: str
    root_category_id: str
    child_category_id: str
    primary_tag_id: str
    secondary_tag_id: str
    original_amount_minor: int
    refunded_amount_minor: int
    net_expense_minor: int
    primary_tag_amount_minor: int
    secondary_tag_amount_minor: int
    filtered_net_expense_minor: int


async def _create_resource(
    client: AsyncClient,
    path: str,
    payload: dict[str, object],
) -> dict[str, object]:
    response = await client.post(path, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _expense_id(index: int) -> str:
    return f"00000000-0000-4000-8000-{index + 1:012x}"


def _refund_id(index: int) -> str:
    return f"00000000-0000-4001-8000-{index + 1:012x}"


async def seed_scale_ledger(
    client: AsyncClient,
    engine: Engine,
    *,
    transaction_count: int = TRANSACTION_COUNT,
) -> ScaleLedger:
    """在一个事务中批量生成合法支出、有效退款、作废退款与 Tag。"""

    primary_account = await _create_resource(
        client, "/api/v1/accounts", {"type": "credit", "name": "压力账户 A"}
    )
    secondary_account = await _create_resource(
        client, "/api/v1/accounts", {"type": "credit", "name": "压力账户 B"}
    )
    root_category = await _create_resource(
        client,
        "/api/v1/categories",
        {"name": "压力支出", "purpose": "expense"},
    )
    child_category = await _create_resource(
        client,
        "/api/v1/categories",
        {
            "name": "压力子分类",
            "purpose": "expense",
            "parentCategoryId": root_category["id"],
        },
    )
    primary_tag = await _create_resource(
        client, "/api/v1/tags", {"name": "压力主标签"}
    )
    secondary_tag = await _create_resource(
        client, "/api/v1/tags", {"name": "压力次标签"}
    )

    account_ids = (str(primary_account["id"]), str(secondary_account["id"]))
    category_ids = (str(root_category["id"]), str(child_category["id"]))
    primary_tag_id = str(primary_tag["id"])
    secondary_tag_id = str(secondary_tag["id"])
    created_at = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    active_refund_count = min(ACTIVE_REFUND_COUNT, transaction_count)
    void_refund_count = min(
        VOID_REFUND_COUNT,
        max(transaction_count - active_refund_count, 0),
    )
    primary_tag_amount = 0
    secondary_tag_amount = 0
    filtered_net_expense = 0

    transaction_insert = Transaction.__table__.insert()
    tag_insert = TransactionTag.__table__.insert()
    with engine.begin() as connection:
        for batch_start in range(0, transaction_count, 5_000):
            expense_rows = []
            tag_rows = []
            for index in range(
                batch_start,
                min(batch_start + 5_000, transaction_count),
            ):
                net_amount = (
                    EXPENSE_AMOUNT_MINOR - REFUND_AMOUNT_MINOR
                    if index < active_refund_count
                    else EXPENSE_AMOUNT_MINOR
                )
                expense_rows.append(
                    {
                        "id": _expense_id(index),
                        "type": TransactionType.EXPENSE,
                        "src_account_id": account_ids[index % 2],
                        "dest_account_id": None,
                        "amount_minor": EXPENSE_AMOUNT_MINOR,
                        "description": (
                            "目标消费" if index % 10 == 0 else "日常消费"
                        ),
                        "category": category_ids[index % 2],
                        "refund_of_transaction_id": None,
                        "balance_adjustment_direction": None,
                        "is_void": False,
                        "voided_at": None,
                        "occurred_at": datetime(
                            2026, 1, index % 28 + 1, 4, 0, tzinfo=UTC
                        ),
                        "created_at": created_at,
                        "updated_at": created_at,
                    }
                )
                if index % 2 == 0:
                    tag_rows.append(
                        {"transaction_id": _expense_id(index), "tag_id": primary_tag_id}
                    )
                    primary_tag_amount += net_amount
                else:
                    tag_rows.append(
                        {"transaction_id": _expense_id(index), "tag_id": secondary_tag_id}
                    )
                    secondary_tag_amount += net_amount
                if index % 10 == 0:
                    tag_rows.append(
                        {"transaction_id": _expense_id(index), "tag_id": secondary_tag_id}
                    )
                    secondary_tag_amount += net_amount
                    filtered_net_expense += net_amount
            connection.execute(transaction_insert, expense_rows)
            connection.execute(tag_insert, tag_rows)

        refund_rows = []
        for index in range(active_refund_count + void_refund_count):
            is_void = index >= active_refund_count
            refund_rows.append(
                {
                    "id": _refund_id(index),
                    "type": TransactionType.EXPENSE_REFUND,
                    "src_account_id": account_ids[index % 2],
                    "dest_account_id": None,
                    "amount_minor": REFUND_AMOUNT_MINOR,
                    "description": "压力退款",
                    "category": category_ids[index % 2],
                    "refund_of_transaction_id": _expense_id(index),
                    "balance_adjustment_direction": None,
                    "is_void": is_void,
                    "voided_at": created_at if is_void else None,
                    "occurred_at": datetime(2026, 1, 15, 4, 0, tzinfo=UTC),
                    "created_at": created_at,
                    "updated_at": created_at,
                }
            )
        if refund_rows:
            connection.execute(transaction_insert, refund_rows)

    original_amount = transaction_count * EXPENSE_AMOUNT_MINOR
    refunded_amount = active_refund_count * REFUND_AMOUNT_MINOR
    return ScaleLedger(
        account_id=account_ids[0],
        root_category_id=category_ids[0],
        child_category_id=category_ids[1],
        primary_tag_id=primary_tag_id,
        secondary_tag_id=secondary_tag_id,
        original_amount_minor=original_amount,
        refunded_amount_minor=refunded_amount,
        net_expense_minor=original_amount - refunded_amount,
        primary_tag_amount_minor=primary_tag_amount,
        secondary_tag_amount_minor=secondary_tag_amount,
        filtered_net_expense_minor=filtered_net_expense,
    )


def statistics_requests() -> dict[str, tuple[str, dict[str, object]]]:
    """返回正确性与性能验收使用的八个请求。"""

    return {
        "transactions": (
            "/api/v1/transactions",
            {
                "type": "expense",
                "startAt": "2025-12-31T16:00:00Z",
                "endAt": "2026-01-31T16:00:00Z",
                "pageSize": 100,
            },
        ),
        "overview": ("/api/v1/statistics/overview", PERIOD),
        "cash-flow": (
            "/api/v1/statistics/cash-flow",
            {**PERIOD, "granularity": "day"},
        ),
        "expenses": (
            "/api/v1/statistics/expenses",
            {**PERIOD, "granularity": "day"},
        ),
        "categories": (
            "/api/v1/statistics/categories",
            {**PERIOD, "granularity": "day"},
        ),
        "tags": ("/api/v1/statistics/tags", PERIOD),
        "calendar": ("/api/v1/statistics/calendar", {"month": "2026-01"}),
        "expense-transactions": (
            "/api/v1/statistics/expense-transactions",
            {**PERIOD, "pageSize": 100},
        ),
    }


FRONTEND_STATISTICS = (
    "overview",
    "cash-flow",
    "expenses",
    "categories",
    "tags",
    "calendar",
)
