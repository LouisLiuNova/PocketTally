"""Issue #15 的筛选组合、时间桶和分类树专项矩阵。"""

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
async def test_issue15_filter_granularity_tree_and_exclusions(tmp_path: Path) -> None:
    """覆盖周一边界、月末、空桶、多 Tag、筛选组合和树移动。"""

    app = create_app(Settings(environment="test", database_path=tmp_path / "matrix.sqlite3"))
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        account = await create_resource(client, "/api/v1/accounts", {"type": "credit", "name": "主账户"})
        other_account = await create_resource(
            client, "/api/v1/accounts", {"type": "debit", "name": "另一账户"}
        )
        root_a = await create_resource(client, "/api/v1/categories", {"name": "生活", "purpose": "expense"})
        child = await create_resource(
            client,
            "/api/v1/categories",
            {"name": "早餐", "purpose": "expense", "parentCategoryId": root_a["id"]},
        )
        root_b = await create_resource(client, "/api/v1/categories", {"name": "成长", "purpose": "expense"})
        tag_alpha = await create_resource(client, "/api/v1/tags", {"name": "必要"})
        tag_beta = await create_resource(client, "/api/v1/tags", {"name": "可报销"})

        async def expense(
            amount: int,
            category_id: str,
            occurred_at: str,
            description: str,
            tag_ids: list[str],
        ) -> dict:
            return await create_resource(
                client,
                "/api/v1/transactions",
                {
                    "type": "expense",
                    "sourceAccountId": account["id"],
                    "amount": amount,
                    "categoryId": category_id,
                    "tagIds": tag_ids,
                    "description": description,
                    "occurredAt": occurred_at,
                },
            )

        await expense(
            10,
            child["id"],
            "2026-03-01T16:00:00Z",  # 上海时间周一 00:00，验证周一归桶
            "早餐",
            [tag_alpha["id"], tag_beta["id"]],
        )
        await expense(
            20,
            child["id"],
            "2026-03-31T15:59:00Z",  # 上海时间月末 23:59
            "月末采购",
            [tag_alpha["id"]],
        )
        await expense(
            30,
            root_b["id"],
            "2026-03-15T04:00:00Z",
            "书籍",
            [tag_beta["id"]],
        )
        voided = await expense(
            40,
            root_a["id"],
            "2026-03-20T04:00:00Z",
            "作废支出",
            [tag_alpha["id"]],
        )
        assert (await client.post(f"/api/v1/transactions/{voided['id']}/void")).status_code == 200

        transfer = await client.post(
            "/api/v1/transactions",
            json={
                "type": "transfer",
                "sourceAccountId": account["id"],
                "destinationAccountId": other_account["id"],
                "amount": 999,
                "occurredAt": "2026-03-10T04:00:00Z",
            },
        )
        assert transfer.status_code == 201, transfer.text
        adjustment = await client.post(
            "/api/v1/transactions",
            json={
                "type": "balance_adjustment",
                "sourceAccountId": account["id"],
                "amount": 888,
                "balanceAdjustmentDirection": "increase",
                "occurredAt": "2026-03-11T04:00:00Z",
            },
        )
        assert adjustment.status_code == 201, adjustment.text

        period = {"startDate": "2026-03-01", "endDate": "2026-04-01"}
        details = (await client.get("/api/v1/statistics/expense-transactions", params=period)).json()
        assert details["total"] == 3
        assert details["totals"] == {
            "originalAmountMinor": 6000,
            "refundedAmountMinor": 0,
            "netExpenseMinor": 6000,
        }
        second_page = (
            await client.get(
                "/api/v1/statistics/expense-transactions",
                params={**period, "page": 2, "pageSize": 2},
            )
        ).json()
        assert second_page["total"] == 3
        assert len(second_page["items"]) == 1
        assert second_page["items"][0]["transaction"]["description"] == "早餐"
        assert second_page["totals"] == details["totals"]

        filtered = (
            await client.get(
                "/api/v1/statistics/expense-transactions",
                params={
                    **period,
                    "accountId": account["id"],
                    "categoryId": root_a["id"],
                    "includeDescendants": "true",
                    "tagId": tag_alpha["id"],
                    "q": "月末",
                },
            )
        ).json()
        assert filtered["total"] == 1
        assert filtered["items"][0]["netExpenseMinor"] == 2000

        tags = (await client.get("/api/v1/statistics/tags", params=period)).json()
        by_tag = {item["tagId"]: item["netExpenseMinor"] for item in tags["items"]}
        assert by_tag[tag_alpha["id"]] == 3000
        assert by_tag[tag_beta["id"]] == 4000

        weekly = (await client.get(
            "/api/v1/statistics/expenses",
            params={**period, "granularity": "week"},
        )).json()
        assert weekly["granularity"] == "week"
        assert sum(bucket["netExpenseMinor"] for bucket in weekly["buckets"]) == 6000
        categories_weekly = (await client.get(
            "/api/v1/statistics/categories",
            params={**period, "granularity": "week"},
        )).json()
        assert categories_weekly["granularity"] == "week"
        assert sum(bucket["netExpenseMinor"] for bucket in categories_weekly["buckets"]) == 6000
        categories_daily = (await client.get(
            "/api/v1/statistics/categories",
            params={**period, "granularity": "day"},
        )).json()
        assert len(categories_daily["buckets"]) == 31
        assert sum(bucket["netExpenseMinor"] for bucket in categories_daily["buckets"]) == 6000
        assert any(bucket["netExpenseMinor"] == 0 for bucket in categories_daily["buckets"])

        before_move = {item["categoryId"]: item["amountMinor"] for item in categories_daily["items"]}
        assert before_move[root_a["id"]] == 3000
        assert before_move[root_b["id"]] == 3000

        moved = await client.patch(
            f"/api/v1/categories/{child['id']}",
            json={"parentCategoryId": root_b["id"]},
        )
        assert moved.status_code == 200, moved.text
        after_move = (
            await client.get("/api/v1/statistics/categories", params={**period, "granularity": "month"})
        ).json()
        after_amounts = {item["categoryId"]: item["amountMinor"] for item in after_move["items"]}
        assert after_amounts[root_a["id"]] == 0
        assert after_amounts[root_b["id"]] == 6000

        invalid = await client.get(
            "/api/v1/statistics/categories",
            params={**period, "granularity": "quarter"},
        )
        assert invalid.status_code == 422
