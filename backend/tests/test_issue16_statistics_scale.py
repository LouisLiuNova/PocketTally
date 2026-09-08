"""Issue #16 十万笔账本统计正确性回归。"""

import asyncio
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event

from app.config import Settings
from app.main import create_app
from tests.statistics_scale_support import (
    FRONTEND_STATISTICS,
    TRANSACTION_COUNT,
    seed_scale_ledger,
    statistics_requests,
)


@pytest.mark.asyncio
async def test_hundred_thousand_transaction_statistics(tmp_path: Path) -> None:
    """验证大账本全部统计、筛选与前端并发加载保持正确。"""

    app = create_app(
        Settings(environment="test", database_path=tmp_path / "issue16.sqlite3")
    )
    async with (
        app.router.lifespan_context(app),
        AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client,
    ):
        expected = await seed_scale_ledger(client, app.state.resources.engine)
        parameter_counts: list[int] = []

        @event.listens_for(app.state.resources.engine, "before_cursor_execute")
        def capture_parameter_count(
            _connection,
            _cursor,
            _statement,
            parameters,
            _context,
            executemany,
        ) -> None:
            if not executemany:
                parameter_counts.append(len(parameters))

        requests = statistics_requests()
        responses = {
            name: await client.get(path, params=params)
            for name, (path, params) in requests.items()
        }
        concurrent = await asyncio.gather(
            *(
                client.get(requests[name][0], params=requests[name][1])
                for name in FRONTEND_STATISTICS
            )
        )

        filtered = await client.get(
            "/api/v1/statistics/overview",
            params={
                "startDate": "2026-01-01",
                "endDate": "2026-02-01",
                "accountId": expected.account_id,
                "categoryId": expected.root_category_id,
                "includeDescendants": True,
                "tagId": expected.primary_tag_id,
                "q": "目标",
            },
        )

        event.remove(
            app.state.resources.engine,
            "before_cursor_execute",
            capture_parameter_count,
        )

    assert all(response.status_code == 200 for response in responses.values())
    assert all(response.status_code == 200 for response in concurrent)
    assert responses["transactions"].json()["total"] == TRANSACTION_COUNT

    overview = responses["overview"].json()
    assert overview["netExpense"]["currentAmountMinor"] == expected.net_expense_minor

    expenses = responses["expenses"].json()
    assert sum(item["netExpenseMinor"] for item in expenses["buckets"]) == (
        expected.net_expense_minor
    )

    categories = responses["categories"].json()
    assert categories["items"][0]["amountMinor"] == expected.net_expense_minor
    assert sum(item["netExpenseMinor"] for item in categories["buckets"]) == (
        expected.net_expense_minor
    )

    tags = {
        item["tagId"]: item["netExpenseMinor"]
        for item in responses["tags"].json()["items"]
    }
    assert tags == {
        expected.primary_tag_id: expected.primary_tag_amount_minor,
        expected.secondary_tag_id: expected.secondary_tag_amount_minor,
    }

    details = responses["expense-transactions"].json()
    assert details["total"] == TRANSACTION_COUNT
    assert details["totals"] == {
        "originalAmountMinor": expected.original_amount_minor,
        "refundedAmountMinor": expected.refunded_amount_minor,
        "netExpenseMinor": expected.net_expense_minor,
    }

    cash_flow = responses["cash-flow"].json()
    calendar = responses["calendar"].json()
    cash_refunds = sum(item["refundAmountMinor"] for item in cash_flow["buckets"])
    calendar_refunds = sum(item["refundAmountMinor"] for item in calendar["days"])
    assert cash_refunds == expected.refunded_amount_minor
    assert calendar_refunds == expected.refunded_amount_minor
    assert sum(item["netCashFlowMinor"] for item in cash_flow["buckets"]) == (
        -expected.net_expense_minor
    )

    assert filtered.status_code == 200
    assert filtered.json()["netExpense"]["currentAmountMinor"] == (
        expected.filtered_net_expense_minor
    )
    assert parameter_counts
    # 消费下钻对当前页的 Tag 关系使用至多 pageSize 个参数；其余统计参数
    # 均只来自固定筛选条件，不随账本总交易数增长。
    assert max(parameter_counts) <= 100
