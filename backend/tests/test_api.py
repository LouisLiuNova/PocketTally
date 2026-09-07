"""基础资源 CRUD 和交易 API 集成测试。"""

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlmodel import Session

from app.config import Settings
from app.main import create_app
from app.models import Category, Transaction, TransactionTag, TransactionType


async def create_resource(
    client: AsyncClient,
    path: str,
    payload: dict[str, object],
) -> dict[str, object]:
    """创建资源并返回响应对象。"""

    response = await client.post(path, json=payload)
    assert response.status_code == 201, response.text
    assert response.headers["Location"].endswith(f"/{response.json()['id']}")
    return response.json()


@pytest.mark.asyncio
async def test_resource_crud_conflicts_and_validation(tmp_path: Path) -> None:
    """验证基础维护、唯一性、分类规则和统一错误契约。"""

    app = create_app(
        Settings(environment="test", database_path=tmp_path / "resources.sqlite3")
    )
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        wallet = await create_resource(
            client,
            "/api/v1/accounts",
            {"type": "debit", "name": "钱包"},
        )
        assert wallet["amount"] == 0.0
        assert (await client.get(f"/api/v1/accounts/{wallet['id']}")).json() == wallet
        duplicate = await client.post(
            "/api/v1/accounts",
            json={"type": "credit", "name": " 钱包 "},
        )
        assert duplicate.status_code == 409
        assert duplicate.json() == {
            "code": "account_name_conflict",
            "message": "名称已被使用",
        }

        card = await create_resource(
            client,
            "/api/v1/accounts",
            {"type": "credit", "name": "信用卡"},
        )
        update_conflict = await client.patch(
            f"/api/v1/accounts/{card['id']}", json={"name": "钱包"}
        )
        assert update_conflict.status_code == 409
        assert update_conflict.json()["code"] == "account_name_conflict"
        updated = await client.patch(
            f"/api/v1/accounts/{card['id']}",
            json={"description": "日常信用账户"},
        )
        assert updated.status_code == 200
        assert updated.json()["description"] == "日常信用账户"
        assert len((await client.get("/api/v1/accounts")).json()) == 2

        expense = await create_resource(
            client,
            "/api/v1/categories",
            {"name": "支出", "purpose": "expense"},
        )
        food = await create_resource(
            client,
            "/api/v1/categories",
            {
                "name": "餐饮",
                "purpose": "expense",
                "parentCategoryId": expense["id"],
            },
        )
        assert food["parentCategory"]["id"] == expense["id"]
        assert (
            await client.get(f"/api/v1/categories/{food['id']}")
        ).json()["parentCategory"]["id"] == expense["id"]
        income = await create_resource(
            client,
            "/api/v1/categories",
            {"name": "收入", "purpose": "income"},
        )
        duplicate_category = await client.post(
            "/api/v1/categories",
            json={"name": "支出", "purpose": "expense"},
        )
        assert duplicate_category.status_code == 409
        assert duplicate_category.json()["code"] == "category_name_conflict"
        category_update_conflict = await client.patch(
            f"/api/v1/categories/{income['id']}", json={"name": "支出"}
        )
        assert category_update_conflict.status_code == 409
        assert category_update_conflict.json()["code"] == "category_name_conflict"
        mismatch = await client.patch(
            f"/api/v1/categories/{food['id']}",
            json={"parentCategoryId": income["id"]},
        )
        assert mismatch.status_code == 409
        assert mismatch.json()["code"] == "category_purpose_mismatch"
        self_parent = await client.patch(
            f"/api/v1/categories/{food['id']}",
            json={"parentCategoryId": food["id"]},
        )
        assert self_parent.status_code == 409
        assert self_parent.json()["code"] == "category_self_parent"
        immutable = await client.patch(
            f"/api/v1/categories/{food['id']}", json={"purpose": "income"}
        )
        assert immutable.status_code == 422
        assert immutable.json()["code"] == "validation_error"

        missing_parent = await client.post(
            "/api/v1/categories",
            json={
                "name": "未知父分类",
                "purpose": "expense",
                "parentCategoryId": "00000000-0000-0000-0000-000000000000",
            },
        )
        assert missing_parent.status_code == 404
        assert missing_parent.json()["code"] == "category_parent_not_found"

        tag = await create_resource(
            client,
            "/api/v1/tags",
            {"name": "必要", "color": "#112233"},
        )
        assert (await client.get(f"/api/v1/tags/{tag['id']}")).json() == tag
        duplicate_tag = await client.post(
            "/api/v1/tags", json={"name": "必要"}
        )
        assert duplicate_tag.status_code == 409
        assert duplicate_tag.json()["code"] == "tag_name_conflict"
        optional_tag = await create_resource(
            client,
            "/api/v1/tags",
            {"name": "可选"},
        )
        tag_update_conflict = await client.patch(
            f"/api/v1/tags/{optional_tag['id']}", json={"name": "必要"}
        )
        assert tag_update_conflict.status_code == 409
        assert tag_update_conflict.json()["code"] == "tag_name_conflict"
        tag_update = await client.patch(
            f"/api/v1/tags/{tag['id']}", json={"description": "固定支出"}
        )
        assert tag_update.status_code == 200
        assert tag_update.json()["description"] == "固定支出"

        invalid_path = await client.get("/api/v1/accounts/not-a-uuid")
        assert invalid_path.status_code == 422
        assert invalid_path.json()["code"] == "validation_error"
        assert invalid_path.json()["details"][0]["location"] == [
            "path",
            "accountId",
        ]
        missing = await client.get(
            "/api/v1/tags/00000000-0000-0000-0000-000000000000"
        )
        assert missing.status_code == 404
        assert missing.json()["code"] == "tag_not_found"

        disposable = await create_resource(
            client,
            "/api/v1/tags",
            {"name": "临时"},
        )
        deleted = await client.delete(f"/api/v1/tags/{disposable['id']}")
        assert deleted.status_code == 204
        assert deleted.content == b""

        disposable_account = await create_resource(
            client,
            "/api/v1/accounts",
            {"type": "debit", "name": "临时账户"},
        )
        deleted_account = await client.delete(
            f"/api/v1/accounts/{disposable_account['id']}"
        )
        assert deleted_account.status_code == 204
        assert deleted_account.content == b""

        disposable_category = await create_resource(
            client,
            "/api/v1/categories",
            {"name": "临时分类", "purpose": "expense"},
        )
        deleted_category = await client.delete(
            f"/api/v1/categories/{disposable_category['id']}"
        )
        assert deleted_category.status_code == 204
        assert deleted_category.content == b""


@pytest.mark.asyncio
async def test_transaction_reads_and_delete_conflicts_preserve_relations(
    tmp_path: Path,
) -> None:
    """验证交易有界摘要和删除冲突后的全部历史关系保持不变。"""

    app = create_app(
        Settings(environment="test", database_path=tmp_path / "relations.sqlite3")
    )
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        source = await create_resource(
            client,
            "/api/v1/accounts",
            {"type": "debit", "name": "钱包"},
        )
        destination = await create_resource(
            client,
            "/api/v1/accounts",
            {"type": "debit", "name": "储蓄卡"},
        )
        category = await create_resource(
            client,
            "/api/v1/categories",
            {"name": "餐饮", "purpose": "expense"},
        )
        child = await create_resource(
            client,
            "/api/v1/categories",
            {
                "name": "工作餐",
                "purpose": "expense",
                "parentCategoryId": category["id"],
            },
        )
        tag = await create_resource(client, "/api/v1/tags", {"name": "必要"})

        transaction = Transaction(
            type=TransactionType.EXPENSE,
            src_account_id=str(source["id"]),
            amount_minor=1880,
            description="午餐",
            category=str(category["id"]),
            occurred_at=datetime.now(UTC),
        )
        transaction_id = transaction.id
        with Session(app.state.resources.engine) as session, session.begin():
            session.add(transaction)
            session.flush()
            session.add(
                TransactionTag(transaction_id=transaction.id, tag_id=str(tag["id"]))
            )
            related = Transaction(
                type=TransactionType.EXPENSE,
                src_account_id=str(source["id"]),
                amount_minor=500,
                description="关联记录",
                category=str(category["id"]),
                is_refund=True,
                related_transaction_id=transaction.id,
                occurred_at=datetime.now(UTC),
            )
            related_id = related.id
            session.add(related)
            voided_transfer = Transaction(
                type=TransactionType.TRANSFER,
                src_account_id=str(source["id"]),
                dest_account_id=str(destination["id"]),
                amount_minor=100,
                description="已作废转账",
                is_void=True,
                voided_at=datetime.now(UTC),
                occurred_at=datetime.now(UTC),
            )
            voided_transfer_id = voided_transfer.id
            session.add(voided_transfer)
        statements: list[str] = []

        def record_statement(
            _connection,
            _cursor,
            statement: str,
            _parameters,
            _context,
            _executemany,
        ) -> None:
            """记录交易列表请求发出的 SQL。"""

            statements.append(statement)

        event.listen(
            app.state.resources.engine,
            "before_cursor_execute",
            record_statement,
        )
        try:
            listing = await client.get("/api/v1/transactions")
        finally:
            event.remove(
                app.state.resources.engine,
                "before_cursor_execute",
                record_statement,
            )
        assert listing.status_code == 200
        assert len(listing.json()) == 2
        assert len(statements) == 2
        audit_listing = await client.get(
            "/api/v1/transactions", params={"includeVoided": "true"}
        )
        assert audit_listing.status_code == 200
        assert len(audit_listing.json()) == 3
        detail = await client.get(f"/api/v1/transactions/{transaction_id}")
        assert detail.status_code == 200
        body = detail.json()
        assert body["sourceAccount"]["id"] == source["id"]
        assert body["category"]["id"] == category["id"]
        assert body["tags"][0]["id"] == tag["id"]
        assert body["amount"] == 18.8

        related_detail = await client.get(f"/api/v1/transactions/{related_id}")
        assert related_detail.status_code == 200
        assert related_detail.json()["relatedTransaction"]["id"] == transaction_id
        assert related_detail.json()["relatedTransaction"]["amount"] == 18.8

        for path, code in (
            (f"/api/v1/accounts/{source['id']}", "account_in_use"),
            (f"/api/v1/accounts/{destination['id']}", "account_in_use"),
            (f"/api/v1/categories/{category['id']}", "category_in_use"),
            (f"/api/v1/tags/{tag['id']}", "tag_in_use"),
        ):
            response = await client.delete(path)
            assert response.status_code == 409
            assert response.json()["code"] == code

        with Session(app.state.resources.engine) as session:
            preserved = session.get(Transaction, transaction_id)
            assert preserved is not None
            assert preserved.src_account_id == source["id"]
            assert preserved.category == category["id"]
            preserved_transfer = session.get(Transaction, voided_transfer_id)
            assert preserved_transfer is not None
            assert preserved_transfer.src_account_id == source["id"]
            assert preserved_transfer.dest_account_id == destination["id"]
            assert preserved_transfer.is_void is True
            assert preserved_transfer.voided_at is not None
            assert session.get(TransactionTag, (transaction_id, tag["id"])) is not None
            preserved_child = session.get(Category, child["id"])
            assert preserved_child is not None
            assert preserved_child.parent_category_id == category["id"]

        missing_transaction = await client.get(
            "/api/v1/transactions/00000000-0000-0000-0000-000000000000"
        )
        assert missing_transaction.status_code == 404
        assert missing_transaction.json()["code"] == "transaction_not_found"


@pytest.mark.asyncio
async def test_transaction_write_patch_tags_and_idempotent_void(tmp_path: Path) -> None:
    """验证四类交易写入、合并校验、标签语义和幂等作废。"""

    app = create_app(
        Settings(environment="test", database_path=tmp_path / "transactions.sqlite3")
    )
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        source = await create_resource(
            client, "/api/v1/accounts", {"type": "credit", "name": "来源"}
        )
        destination = await create_resource(
            client, "/api/v1/accounts", {"type": "debit", "name": "目标"}
        )
        income_category = await create_resource(
            client,
            "/api/v1/categories",
            {"name": "工资", "purpose": "income"},
        )
        expense_category = await create_resource(
            client,
            "/api/v1/categories",
            {"name": "餐饮", "purpose": "expense"},
        )
        tag = await create_resource(client, "/api/v1/tags", {"name": "日常"})
        occurred_at = datetime.now(UTC).isoformat()

        adjustment = await client.post(
            "/api/v1/transactions",
            json={
                "type": "balance_adjustment",
                "sourceAccountId": source["id"],
                "amount": 100,
                "balanceAdjustmentDirection": "increase",
                "occurredAt": occurred_at,
            },
        )
        assert adjustment.status_code == 201, adjustment.text
        assert adjustment.json()["isVoid"] is False
        assert adjustment.json()["voidedAt"] is None

        income = await client.post(
            "/api/v1/transactions",
            json={
                "type": "income",
                "destinationAccountId": destination["id"],
                "amount": 5,
                "categoryId": income_category["id"],
                "occurredAt": occurred_at,
            },
        )
        assert income.status_code == 201, income.text

        expense = await client.post(
            "/api/v1/transactions",
            json={
                "type": "expense",
                "sourceAccountId": source["id"],
                "amount": 12.5,
                "categoryId": expense_category["id"],
                "tagIds": [tag["id"]],
                "occurredAt": occurred_at,
            },
        )
        assert expense.status_code == 201, expense.text
        expense_body = expense.json()
        assert expense_body["tags"][0]["id"] == tag["id"]

        transfer = await client.post(
            "/api/v1/transactions",
            json={
                "type": "transfer",
                "sourceAccountId": source["id"],
                "destinationAccountId": destination["id"],
                "amount": 20,
                "occurredAt": occurred_at,
            },
        )
        assert transfer.status_code == 201, transfer.text

        forbidden_refund = await client.post(
            "/api/v1/transactions",
            json={
                "type": "expense",
                "sourceAccountId": source["id"],
                "amount": 1,
                "categoryId": expense_category["id"],
                "isRefund": True,
                "occurredAt": occurred_at,
            },
        )
        assert forbidden_refund.status_code == 422

        missing_tag = await client.patch(
            f"/api/v1/transactions/{expense_body['id']}",
            json={"tagIds": ["00000000-0000-0000-0000-000000000000"]},
        )
        assert missing_tag.status_code == 404
        assert missing_tag.json()["code"] == "tag_not_found"

        invalid_merged_state = await client.patch(
            f"/api/v1/transactions/{expense_body['id']}",
            json={"type": "transfer"},
        )
        assert invalid_merged_state.status_code == 422
        preserved = await client.get(
            f"/api/v1/transactions/{expense_body['id']}"
        )
        assert preserved.json()["type"] == "expense"
        assert len(preserved.json()["tags"]) == 1

        cleared = await client.patch(
            f"/api/v1/transactions/{expense_body['id']}",
            json={"tagIds": []},
        )
        assert cleared.status_code == 200, cleared.text
        assert cleared.json()["tags"] == []

        first_void = await client.post(
            f"/api/v1/transactions/{expense_body['id']}/void"
        )
        assert first_void.status_code == 200, first_void.text
        first_body = first_void.json()
        assert first_body["isVoid"] is True
        assert first_body["voidedAt"] is not None
        repeated_void = await client.post(
            f"/api/v1/transactions/{expense_body['id']}/void"
        )
        assert repeated_void.status_code == 200, repeated_void.text
        assert repeated_void.json()["voidedAt"] == first_body["voidedAt"]
        assert repeated_void.json()["updatedAt"] == first_body["updatedAt"]

        rejected_patch = await client.patch(
            f"/api/v1/transactions/{expense_body['id']}",
            json={"description": "不可修改"},
        )
        assert rejected_patch.status_code == 409
        assert rejected_patch.json()["code"] == "transaction_voided"

        default_ids = {
            item["id"] for item in (await client.get("/api/v1/transactions")).json()
        }
        assert expense_body["id"] not in default_ids
        audit_ids = {
            item["id"]
            for item in (
                await client.get(
                    "/api/v1/transactions", params={"includeVoided": "true"}
                )
            ).json()
        }
        assert expense_body["id"] in audit_ids

        concurrent_target = await client.post(
            "/api/v1/transactions",
            json={
                "type": "balance_adjustment",
                "sourceAccountId": source["id"],
                "amount": 3,
                "balanceAdjustmentDirection": "increase",
                "occurredAt": occurred_at,
            },
        )
        assert concurrent_target.status_code == 201
        concurrent_id = concurrent_target.json()["id"]
        concurrent_results = await asyncio.gather(
            client.post(f"/api/v1/transactions/{concurrent_id}/void"),
            client.post(f"/api/v1/transactions/{concurrent_id}/void"),
        )
        assert [response.status_code for response in concurrent_results] == [200, 200]
        assert (
            concurrent_results[0].json()["voidedAt"]
            == concurrent_results[1].json()["voidedAt"]
        )


@pytest.mark.asyncio
async def test_unexpected_error_does_not_expose_internal_exception(tmp_path: Path) -> None:
    """验证未预期错误仍使用统一结构且不泄露内部异常文本。"""

    app = create_app(
        Settings(environment="test", database_path=tmp_path / "error.sqlite3")
    )

    @app.get("/api/v1/test-only-failure", include_in_schema=False)
    async def fail_for_test() -> None:
        """制造仅供本测试使用的未预期错误。"""

        raise RuntimeError("private sqlite detail")

    async with (
        app.router.lifespan_context(app),
        AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as client,
    ):
        response = await client.get("/api/v1/test-only-failure")

    assert response.status_code == 500
    assert response.json() == {
        "code": "internal_error",
        "message": "服务器内部错误",
    }
    assert "private sqlite detail" not in response.text
