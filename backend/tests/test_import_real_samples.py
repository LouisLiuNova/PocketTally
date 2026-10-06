"""用户真实账单的本地验收；CI 没有原文件时跳过。"""

import csv
import os
import re
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import text
from sqlmodel import Session, select

from app.config import Settings
from app.import_parser import parse_bill
from app.main import create_app
from app.models import Transaction

ROOT = os.environ.get("POCKET_TALLY_REAL_BILLS_DIR")
pytestmark = pytest.mark.skipif(
    not ROOT, reason="真实账单只在用户本地验收，不进入 Git/CI"
)


def independent_rows(path):
    if path.suffix == ".csv":
        data = path.read_bytes()
        for encoding in ("utf-8-sig", "gb18030"):
            try:
                rows = list(csv.reader(data.decode(encoding).splitlines()))
                break
            except UnicodeDecodeError:
                continue
    else:
        w = load_workbook(path, read_only=True, data_only=False, keep_links=False)
        try:
            rows = [
                [str(v).strip() if v is not None else "" for v in r]
                for r in w.active.values
            ]
        finally:
            w.close()
    header = next(i for i, r in enumerate(rows) if "交易时间" in r)
    fields = [v.strip() for v in rows[header]]
    return [
        dict(zip(fields, [v.strip() for v in r])) for r in rows[header + 1 :] if any(r)
    ], rows[:header]


@pytest.mark.parametrize("pattern", ["支付宝*.csv", "微信*.xlsx"])
def test_real_bill_preview_commit_and_summary(tmp_path, pattern):
    matches = list(Path(ROOT).glob(pattern))
    assert len(matches) == 1, "需要唯一的支付宝 CSV 和微信 XLSX 本地样本"
    path = matches[0]
    raw, prelude = independent_rows(path)
    parsed = parse_bill(path.read_bytes(), path.name)
    assert len(parsed.rows) == len(raw)
    independent_totals = {}
    for direction in ("收入", "支出", "不计收支", "/"):
        total = sum(
            (
                Decimal(re.sub(r"[¥￥,\s]", "", r.get("金额", r.get("金额(元)", "0"))))
                for r in raw
                if r.get("收/支") == direction
            ),
            Decimal(0),
        )
        independent_totals[direction] = int(total * 100)
    assert independent_totals == parsed.summary["sourceAmountMinor"]
    # 真实平台摘要笔数与逐行收支数量一致，金额口径差异单独核对。
    counts = Counter(r.get("收/支") for r in raw)
    for direction in ("收入", "支出", "不计收支"):
        line = next(
            (" ".join(r) for r in prelude if any(direction in v for v in r)), None
        )
        if line:
            numbers = re.findall(r"\d+(?:\.\d+)?", line)
            if numbers:
                assert int(numbers[0]) == counts[direction]
    if parsed.provider == "alipay":
        expense_line = next(" ".join(r) for r in prelude if any("支出" in v for v in r))
        official = int(Decimal(re.findall(r"\d+(?:\.\d+)?", expense_line)[1]) * 100)
        refund_total = sum(
            r.amount_minor for r in parsed.rows if r.state == "refund_pending"
        )
        assert independent_totals["支出"] - refund_total == official
    expected = [r for r in parsed.rows if r.state == "candidate"]
    app = create_app(
        Settings(environment="test", database_path=tmp_path / "real.sqlite3")
    )
    with TestClient(app) as client:
        account = client.post(
            "/api/v1/accounts", json={"name": "真实样本验收账户", "type": "credit"}
        ).json()["id"]
        categories = client.get("/api/v1/categories").json()
        category_ids = {
            kind: next(c["id"] for c in categories if c["purpose"] == kind)
            for kind in ("income", "expense")
        }
        uploaded = client.post(
            "/api/v1/imports", files={"file": (path.name, path.read_bytes())}
        )
        assert uploaded.status_code == 201
        batch = uploaded.json()
        rows = []
        for page in range(1, (batch["summary"]["inputRows"] + 99) // 100 + 1):
            rows += client.get(
                "/api/v1/imports/" + batch["id"], params={"page": page, "pageSize": 100}
            ).json()["items"]
        changes = [
            {
                "rowIds": [
                    r["id"] for r in rows if r["editable"] and r["type"] == kind
                ],
                "accountId": account,
                "categoryId": category_ids[kind],
            }
            for kind in ("income", "expense")
            if any(r["editable"] and r["type"] == kind for r in rows)
        ]
        fixed = client.patch(
            "/api/v1/imports/" + batch["id"],
            json={"version": batch["version"], "changes": changes},
        )
        assert fixed.status_code == 200
        assert fixed.json()["summary"]["selectedCount"] == len(expected)
        committed = client.post(
            "/api/v1/imports/" + batch["id"] + "/commit",
            json={"version": fixed.json()["version"]},
        )
        assert committed.status_code == 200
        assert committed.json()["summary"]["counts"].get("imported") == len(expected)
        with Session(app.state.resources.engine) as s:
            tx = list(s.exec(select(Transaction)))
            assert len(tx) == len(expected)
            assert sum(t.amount_minor for t in tx) == sum(
                r.amount_minor for r in expected
            )
            assert {t.type.value for t in tx} <= {"income", "expense"}
            assert s.exec(text("PRAGMA foreign_key_check")).all() == []
        repeated = client.post(
            "/api/v1/imports", files={"file": (path.name, path.read_bytes())}
        )
        assert repeated.status_code == 201
        assert repeated.json()["summary"]["selectedCount"] == 0
        assert repeated.json()["summary"]["counts"]["duplicate"] == len(expected)
    print(
        parsed.provider,
        "来源行",
        len(raw),
        "正式交易",
        len(expected),
        "退款识别且跳过",
        parsed.summary["parseCounts"].get("refund_pending", 0),
        "独立笔数与金额核对通过",
    )
