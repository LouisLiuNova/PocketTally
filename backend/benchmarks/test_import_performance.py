"""十万笔账本上的完整导入 API 提交性能门禁。"""

import platform
import resource
from datetime import UTC, datetime
from time import perf_counter
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, func
from sqlmodel import Session, select

from app.config import Settings
from app.ledger import recalculate_account_balances
from app.main import create_app
from app.models import Account, Transaction
from tests.test_import_parser import csv_bill, record


@pytest.mark.parametrize("size,limit", [(1000, 10.0), (10000, 30.0)])
def test_batch_write_on_large_ledger(tmp_path, size, limit):
    app = create_app(
        Settings(environment="test", database_path=tmp_path / "scale.sqlite3")
    )
    with TestClient(app) as client:
        engine = app.state.resources.engine
        account_id = client.post(
            "/api/v1/accounts", json={"name": "压力账户", "type": "credit"}
        ).json()["id"]
        category_id = next(
            c["id"]
            for c in client.get("/api/v1/categories").json()
            if c["purpose"] == "expense"
        )
        template = {
            "type": "expense",
            "src_account_id": account_id,
            "amount_minor": 100,
            "category": category_id,
            "occurred_at": datetime(2026, 1, 1, tzinfo=UTC),
        }
        with engine.begin() as c:
            for _ in range(100):
                c.execute(
                    Transaction.__table__.insert(),
                    [{"id": str(uuid4()), **template} for _ in range(1000)],
                )
        with Session(engine) as s, s.begin():
            recalculate_account_balances(s)
        data = csv_bill(
            [record(source=f"PERF-{i}", amount="1.00") for i in range(size)]
        )
        response = client.post("/api/v1/imports", files={"file": ("scale.csv", data)})
        assert response.status_code == 201
        batch = response.json()
        response = client.patch(
            "/api/v1/imports/" + batch["id"],
            json={
                "version": batch["version"],
                "changes": [
                    {
                        "paymentKey": "银行卡(1234)",
                        "accountId": account_id,
                        "categoryId": category_id,
                    }
                ],
            },
        )
        assert response.status_code == 200
        scans = []

        def inspect_query(
            _connection, _cursor, statement, _parameters, _context, _many
        ):
            if (
                "SELECT" in statement.upper()
                and "FROM TRANSACTIONS" in statement.upper()
            ):
                scans.append(statement)

        event.listen(engine, "before_cursor_execute", inspect_query)
        start = perf_counter()
        response = client.post(
            "/api/v1/imports/" + batch["id"] + "/commit",
            json={"version": response.json()["version"]},
        )
        elapsed = perf_counter() - start
        event.remove(engine, "before_cursor_execute", inspect_query)
        assert response.status_code == 200
        assert response.json()["summary"]["counts"] == {"imported": size}
        with Session(engine) as s:
            assert s.get(Account, account_id).amount_minor == -(100000 + size) * 100
            assert (
                s.exec(select(func.count()).select_from(Transaction)).one()
                == 100000 + size
            )
        assert len(scans) <= 3
        assert all("WHERE" in statement.upper() for statement in scans)
        assert elapsed <= limit, f"{size} 行提交耗时 {elapsed:.2f}s 超过 {limit}s"
        print(
            "环境",
            platform.platform(),
            "新增",
            size,
            "已有",
            100000,
            "API提交秒",
            round(elapsed, 3),
            "峰值RSS",
            resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "交易查询",
            len(scans),
        )
