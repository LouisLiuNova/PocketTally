"""真实格式脱敏基线及安全解析回归。"""

import csv
import io
from pathlib import Path

import pytest
from openpyxl import Workbook

from app.import_parser import ParseError, parse_bill

HEADER = [
    "交易时间",
    "交易分类",
    "交易对方",
    "对方账号",
    "商品说明",
    "收/支",
    "金额",
    "收/付款方式",
    "交易状态",
    "交易订单号",
    "商家订单号",
    "备注",
    "",
]


def csv_bill(rows, encoding="utf-8-sig"):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["支付宝个人账单"])
    writer.writerow(HEADER)
    writer.writerows(rows)
    return output.getvalue().encode(encoding)


def record(
    source="000012345678901234567890",
    amount="12.34",
    direction="支出",
    status="交易成功",
    category="餐饮美食",
):
    return [
        "2026-07-03 00:00:00",
        category,
        "测试商户",
        "不保留的对方账号",
        '商品,含逗号与"引号"',
        direction,
        amount,
        "银行卡(1234)",
        status,
        source,
        "商户单号",
        "",
        "",
    ]


@pytest.mark.parametrize("encoding", ["utf-8-sig", "gb18030"])
def test_csv_preserves_precision_ids_and_utc(encoding):
    bill = parse_bill(csv_bill([record()], encoding), "账单.csv")
    row = bill.rows[0]
    assert bill.provider == "alipay"
    assert row.amount_minor == 1234
    assert row.source_id == "000012345678901234567890"
    assert row.occurred_at.isoformat() == "2026-07-02T16:00:00"
    assert "对方账号" not in row.original
    assert "含逗号" in row.description


def test_refund_same_source_does_not_exclude_original_and_conflicts_are_explicit():
    bill = parse_bill(
        csv_bill(
            [
                record(),
                record(direction="不计收支", status="退款成功", category="退款"),
                record(source="same"),
                record(source="same"),
                record(source="conflict"),
                record(source="conflict", amount="20.00"),
            ]
        ),
        "账单.csv",
    )
    assert [r.state for r in bill.rows] == [
        "candidate",
        "refund_pending",
        "candidate",
        "skipped",
        "unsupported",
        "unsupported",
    ]
    assert bill.rows[2].original["rowNumbers"] == [5, 6]


@pytest.mark.parametrize(
    "row,state",
    [
        (record(amount="0.00", status="支付成功"), "skipped"),
        (record(status="交易关闭"), "skipped"),
        (record(category="投资理财"), "skipped"),
        (record(status="等待确认收货"), "unsupported"),
        (record(source=""), "unsupported"),
        (record(amount="NaN"), "unsupported"),
        (record(amount="1.001"), "unsupported"),
        (record(amount="-1"), "unsupported"),
        (record(status="已全额退款"), "candidate"),
    ],
)
def test_all_rows_have_explicit_decisions(row, state):
    bill = parse_bill(csv_bill([row]), "bill.csv")
    assert len(bill.rows) == 1
    assert bill.rows[0].state == state
    assert bill.summary["inputRows"] == 1


def xlsx_bill(formula=False):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["微信支付账单流水文件"])
    sheet.append(
        [
            "交易时间",
            "交易类型",
            "交易对方",
            "商品",
            "收/支",
            "金额(元)",
            "支付方式",
            "当前状态",
            "交易单号",
            "商户单号",
            "备注",
        ]
    )
    sheet.append(
        [
            "2026-07-03 00:00:00",
            "转账",
            "测试用户",
            "商品",
            "支出",
            "=1+1" if formula else "￥12.34",
            "零钱",
            "对方已收钱",
            "0000000000001",
            "",
            "",
        ]
    )
    output = io.BytesIO()
    workbook.save(output)
    return output.getvalue()


def test_wechat_xlsx_and_disguised_files():
    row = parse_bill(xlsx_bill(), "file.xlsx").rows[0]
    assert row.transaction_type == "expense" and row.amount_minor == 1234
    with pytest.raises(ParseError, match="公式"):
        parse_bill(xlsx_bill(True), "file.xlsx")
    for data, name in [
        (xlsx_bill(), "file.csv"),
        (b"not xlsx", "file.xlsx"),
        (b"not a bill", "file.csv"),
        (b"x", "file.xls"),
    ]:
        with pytest.raises(ParseError):
            parse_bill(data, name)


def test_limits_and_broken_csv(monkeypatch):
    import app.import_parser as parser

    with pytest.raises(ParseError):
        parse_bill(b"\x00", "file.csv")
    with pytest.raises(ParseError):
        parse_bill(b'"unterminated', "file.csv")
    monkeypatch.setattr(parser, "MAX_ROWS", 1)
    with pytest.raises(ParseError, match="10,000"):
        parse_bill(csv_bill([record(), record("two")]), "file.csv")
    monkeypatch.setattr(parser, "MAX_EXPANDED_BYTES", 10)
    with pytest.raises(ParseError, match="安全限制"):
        parse_bill(xlsx_bill(), "file.xlsx")


def test_sanitized_real_format_fixtures():
    """仅格式、状态和关系来自真实样本；身份、单号、金额和时间已替换。"""
    paths = list((Path(__file__).parent / "fixtures" / "imports").glob("*.csv"))
    assert len(paths) == 2
    for path in paths:
        bill = parse_bill(path.read_bytes(), path.name)
        assert len(bill.rows) >= 10
        assert sum(bill.summary["parseCounts"].values()) == bill.summary["inputRows"]
        assert any(r.state == "refund_pending" for r in bill.rows)
        assert all(
            not r.source_id or r.source_id.startswith("SAMPLE") for r in bill.rows
        )
