"""Issue #15 的分页、时间和退款双重统计口径测试。"""

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.main import create_app


async def create_resource(client: AsyncClient, path: str, payload: dict) -> dict:
    response = await client.post(path, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_pagination_filters_and_cross_period_refund_statistics(tmp_path: Path) -> None:
    """验证分页筛选、上海日期边界以及退款的两种时间归属。"""

    app = create_app(Settings(environment="test", database_path=tmp_path / "issue15.sqlite3"))
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        account = await create_resource(client, "/api/v1/accounts", {"type": "credit", "name": "信用卡"})
        root = await create_resource(client, "/api/v1/categories", {"name": "日常", "purpose": "expense"})
        child = await create_resource(
            client,
            "/api/v1/categories",
            {"name": "餐饮", "purpose": "expense", "parentCategoryId": root["id"]},
        )
        tag = await create_resource(client, "/api/v1/tags", {"name": "必要"})
        expense = await create_resource(
            client,
            "/api/v1/transactions",
            {
                "type": "expense",
                "sourceAccountId": account["id"],
                "amount": 100,
                "categoryId": child["id"],
                "tagIds": [tag["id"]],
                "description": "午餐 100%",
                "occurredAt": "2026-01-31T16:00:00Z",
            },
        )
        refund = await create_resource(
            client,
            "/api/v1/transactions/refunds",
            {
                "refundOfTransactionId": expense["id"],
                "amount": 20,
                "occurredAt": "2026-02-01T16:00:00Z",
            },
        )

        page = await client.get(
            "/api/v1/transactions",
            params={"pageSize": 1, "q": "100%", "status": "active"},
        )
        assert page.status_code == 200
        assert page.json()["total"] == 1
        assert [item["id"] for item in page.json()["items"]] == [expense["id"]]
        assert (await client.get(f"/api/v1/transactions/{expense['id']}/refund-summary")).json() == {
            "originalAmountMinor": 10000,
            "refundedAmountMinor": 2000,
            "remainingRefundableAmountMinor": 8000,
            "canRefund": True,
            "activeRefundCount": 1,
        }
        assert (await client.get(
            "/api/v1/transactions",
            params={"refundOfTransactionId": expense["id"]},
        )).json()["items"][0]["id"] == refund["id"]

        period = {"startDate": "2026-02-01", "endDate": "2026-03-01"}
        overview = (await client.get("/api/v1/statistics/overview", params=period)).json()
        assert overview["netExpense"]["currentAmountMinor"] == 8000
        assert overview["netCashFlow"]["currentAmountMinor"] == -8000
        cash = (await client.get("/api/v1/statistics/cash-flow", params=period)).json()
        assert sum(bucket["refundAmountMinor"] for bucket in cash["buckets"]) == 2000
        assert sum(bucket["incomeAmountMinor"] for bucket in cash["buckets"]) == 0

        details = (await client.get("/api/v1/statistics/expense-transactions", params=period)).json()
        assert details["totals"] == {
            "originalAmountMinor": 10000,
            "refundedAmountMinor": 2000,
            "netExpenseMinor": 8000,
        }
        assert details["items"][0]["originalAmountMinor"] == 10000
        assert details["items"][0]["refundedAmountMinor"] == 2000
        assert details["items"][0]["netExpenseMinor"] == 8000
        categories = (await client.get(
            "/api/v1/statistics/categories",
            params={**period, "granularity": "day"},
        )).json()
        assert categories["granularity"] == "day"
        assert len(categories["buckets"]) == 28
        assert categories["items"][0]["amountMinor"] == 8000
        assert categories["items"][0]["directAmountMinor"] == 0
        tags = (await client.get("/api/v1/statistics/tags", params=period)).json()
        assert tags["items"][0]["netExpenseMinor"] == 8000

        assert (await client.post(f"/api/v1/transactions/{refund['id']}/void")).status_code == 200
        overview_after_void = (await client.get("/api/v1/statistics/overview", params=period)).json()
        assert overview_after_void["netExpense"]["currentAmountMinor"] == 10000
        cash_after_void = (await client.get("/api/v1/statistics/cash-flow", params=period)).json()
        assert sum(bucket["refundAmountMinor"] for bucket in cash_after_void["buckets"]) == 0

        naive = await client.post(
            "/api/v1/transactions",
            json={
                "type": "expense",
                "sourceAccountId": account["id"],
                "amount": 1,
                "categoryId": child["id"],
                "occurredAt": "2026-02-01T00:00:00",
            },
        )
        assert naive.status_code == 422
        assert naive.json()["code"] == "validation_error"
