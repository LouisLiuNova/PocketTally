"""最小收支报表口径测试。"""

from datetime import UTC, datetime

from app.models import Transaction, TransactionType
from app.reports import calculate_income_expense


def transaction(kind: TransactionType, amount_minor: int, *, is_void: bool = False) -> Transaction:
    """构造只用于统计的交易。"""

    return Transaction(
        type=kind,
        src_account_id="source",
        dest_account_id="destination",
        category="category",
        amount_minor=amount_minor,
        is_void=is_void,
        occurred_at=datetime.now(UTC),
    )


def test_refunds_offset_expenses_without_becoming_income() -> None:
    """验证退款冲减支出，作废项和转账不计入收支。"""

    totals = calculate_income_expense(
        [
            transaction(TransactionType.INCOME, 2000),
            transaction(TransactionType.EXPENSE, 1200),
            transaction(TransactionType.EXPENSE_REFUND, 300),
            transaction(TransactionType.EXPENSE_REFUND, 100, is_void=True),
            transaction(TransactionType.TRANSFER, 500),
            transaction(TransactionType.BALANCE_ADJUSTMENT, 700),
        ]
    )

    assert totals.income_minor == 2000
    assert totals.gross_expense_minor == 1200
    assert totals.expense_refund_minor == 300
    assert totals.net_expense_minor == 900
