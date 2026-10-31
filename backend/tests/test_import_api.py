"""草稿、去重、账户映射及原子提交的 HTTP 验证。"""

from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.config import Settings
from app.import_models import ImportAccountMapping, ImportSource
from app.main import create_app
from app.models import Account, Transaction
from tests.test_import_parser import csv_bill, record


def resources(client, kind="credit"):
    account = client.post(
        "/api/v1/accounts", json={"name": "导入账户", "type": kind}
    ).json()
    categories = client.get("/api/v1/categories").json()
    category = next(c for c in categories if c["purpose"] == "expense")
    return account["id"], category["id"]


def upload(client, rows=None):
    response = client.post(
        "/api/v1/imports",
        files={"file": ("bill.csv", csv_bill(rows or [record()]), "text/csv")},
    )
    assert response.status_code == 201, response.text
    return response.json()


def correct(client, batch, account, category, remember=False):
    change = {
        "paymentKey": "银行卡(1234)",
        "accountId": account,
        "categoryId": category,
        "rememberMapping": remember,
    }
    response = client.patch(
        "/api/v1/imports/" + batch["id"],
        json={"version": batch["version"], "changes": [change]},
    )
    assert response.status_code == 200, response.text
    return response.json()


def commit(client, batch):
    return client.post(
        "/api/v1/imports/" + batch["id"] + "/commit", json={"version": batch["version"]}
    )


def test_atomic_rollback_draft_preservation_and_retry(tmp_path):
    app = create_app(
        Settings(environment="test", database_path=tmp_path / "atomic.sqlite3")
    )
    with TestClient(app) as client:
        account, category = resources(client, "debit")
        batch = upload(client, [record("one"), record("two")])
        batch = correct(client, batch, account, category, True)
        assert batch["summary"]["unresolvedCount"] == 0
        failed = commit(client, batch)
        assert (
            failed.status_code == 409
            and failed.json()["code"] == "import_insufficient_balance"
        )
        with Session(app.state.resources.engine) as session:
            assert session.exec(select(Transaction)).all() == []
            assert session.exec(select(ImportSource)).all() == []
            assert session.exec(select(ImportAccountMapping)).all() == []
        resumed = client.get("/api/v1/imports/" + batch["id"]).json()
        assert (
            resumed["version"] == batch["version"]
            and resumed["items"][0]["categoryId"] == category
        )
        adjustment = client.post(
            "/api/v1/transactions",
            json={
                "type": "balance_adjustment",
                "sourceAccountId": account,
                "balanceAdjustmentDirection": "increase",
                "amount": 100,
                "occurredAt": "2026-01-01T00:00:00Z",
            },
        )
        assert adjustment.status_code == 201, adjustment.text
        success = commit(client, batch)
        assert success.status_code == 200, success.text
        assert success.json()["summary"]["counts"] == {"imported": 2}
        assert commit(client, batch).json()["version"] == success.json()["version"]
        with Session(app.state.resources.engine) as session:
            assert len(session.exec(select(ImportSource)).all()) == 2
            assert len(session.exec(select(ImportAccountMapping)).all()) == 1
            assert session.get(Account, account).amount_minor == 7532
        assert (
            client.delete(
                "/api/v1/imports/" + batch["id"],
                params={"version": success.json()["version"]},
            ).status_code
            == 409
        )


def test_duplicate_upload_new_duplicates_and_concurrent_commit(tmp_path):
    app = create_app(
        Settings(environment="test", database_path=tmp_path / "dedup.sqlite3")
    )
    with TestClient(app) as client:
        account, category = resources(client)
        first = correct(client, upload(client), account, category, True)
        second = correct(client, upload(client), account, category)
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda b: commit(client, b), [first, second]))
        assert sorted(r.status_code for r in responses) == [200, 409]
        again = upload(client)
        assert again["items"][0]["status"] == "duplicate"
        assert again["items"][0]["included"] is False
        assert again["items"][0]["duplicateBatchId"]
        assert again["items"][0]["accountId"] == account
        with Session(app.state.resources.engine) as session:
            assert len(session.exec(select(Transaction)).all()) == 1
        transaction_id = again["items"][0]["transactionId"]
        assert (
            client.post(f"/api/v1/transactions/{transaction_id}/void").status_code
            == 200
        )
        assert upload(client)["items"][0]["status"] == "duplicate"


def test_stale_patch_deletion_resource_invalidation_and_manual_similarity(tmp_path):
    app = create_app(
        Settings(environment="test", database_path=tmp_path / "patch.sqlite3")
    )
    with TestClient(app) as client:
        account, category = resources(client)
        batch = upload(client)
        fixed = correct(client, batch, account, category)
        stale = client.patch(
            "/api/v1/imports/" + batch["id"],
            json={
                "version": batch["version"],
                "changes": [{"rowIds": [batch["items"][0]["id"]], "included": False}],
            },
        )
        assert stale.status_code == 409
        assert (
            client.post(
                "/api/v1/transactions",
                json={
                    "type": "expense",
                    "amount": 12.34,
                    "occurredAt": "2026-07-02T16:00:00Z",
                    "sourceAccountId": account,
                    "categoryId": category,
                },
            ).status_code
            == 201
        )
        preview = client.get("/api/v1/imports/" + batch["id"]).json()
        assert len(preview["items"][0]["similarTransactionIds"]) == 1
        assert preview["items"][0]["status"] == "ready"
        assert commit(client, fixed).status_code == 200
        # 未被正式交易引用的资源删除会使草稿映射失效。
        spare = client.post(
            "/api/v1/accounts", json={"name": "临时账户", "type": "credit"}
        ).json()["id"]
        another = correct(client, upload(client, [record("new")]), spare, category)
        assert client.delete("/api/v1/accounts/" + spare).status_code == 204
        invalidated = client.get("/api/v1/imports/" + another["id"]).json()
        assert invalidated["items"][0]["status"] == "needs_account"
        assert (
            client.delete(
                "/api/v1/imports/" + another["id"],
                params={"version": another["version"]},
            ).status_code
            == 204
        )
        assert client.get("/api/v1/imports/" + another["id"]).status_code == 404


def test_invalid_correction_locked_refund_and_upload_limits(tmp_path):
    app = create_app(
        Settings(environment="test", database_path=tmp_path / "limits.sqlite3")
    )
    with TestClient(app) as client:
        resources(client)
        batch = upload(
            client,
            [
                record(),
                record(
                    "refund", direction="不计收支", status="退款成功", category="退款"
                ),
            ],
        )
        refund = batch["items"][1]
        response = client.patch(
            "/api/v1/imports/" + batch["id"],
            json={
                "version": 1,
                "changes": [{"rowIds": [refund["id"]], "included": True}],
            },
        )
        assert response.status_code == 409
        response = client.patch(
            "/api/v1/imports/" + batch["id"],
            json={
                "version": 1,
                "changes": [{"rowIds": [batch["items"][0]["id"]], "amountMinor": 0}],
            },
        )
        assert response.status_code == 422
        data = b"x" * (10 * 1024 * 1024 + 65537)
        response = client.post(
            "/api/v1/imports",
            content=data,
            headers={"content-type": "application/octet-stream"},
        )
        assert (
            response.status_code == 413
            and response.json()["code"] == "import_file_limit"
        )

        def chunks():
            yield b'--testing\r\nContent-Disposition: form-data; name="file"; filename="bill.csv"\r\nContent-Type: text/csv\r\n\r\n'
            for _ in range(12):
                yield b"x" * (1024 * 1024)
            yield b"\r\n--testing--\r\n"

        response = client.post(
            "/api/v1/imports",
            content=chunks(),
            headers={"content-type": "multipart/form-data; boundary=testing"},
        )
        assert (
            response.status_code == 413
            and response.json()["code"] == "import_file_limit"
        )
        assert (
            client.post(
                "/api/v1/imports", files={"file": ("bad.xlsx", b"bad")}
            ).status_code
            == 422
        )


def test_import_auth_required(tmp_path):
    app = create_app(
        Settings(
            environment="test",
            auth_enabled=True,
            database_path=tmp_path / "auth.sqlite3",
        )
    )
    with TestClient(app) as client:
        assert client.get("/api/v1/imports").status_code == 401
        assert (
            client.post(
                "/api/v1/imports", files={"file": ("bill.csv", csv_bill([record()]))}
            ).status_code
            == 401
        )
