"""有效交易的最小收支统计，不划分期间。"""

from collections.abc import Iterable
from dataclasses import dataclass

from app.models import Transaction, TransactionType


@dataclass(frozen=True, slots=True)
class IncomeExpenseTotals:
    """以整数分表达的收入、原始支出、退款及净支出。"""

    income_minor: int
    gross_expense_minor: int
    expense_refund_minor: int
    net_expense_minor: int


def calculate_income_expense(transactions: Iterable[Transaction]) -> IncomeExpenseTotals:
    """汇总有效交易，退款抵减支出，转账和余额调整不计收支。

    Args:
        transactions: 需要汇总的交易集合；不按原支出时间重新归属退款。

    Returns:
        以整数分表示的收支汇总。
    """

    totals = {
        kind: 0
        for kind in (
            TransactionType.INCOME,
            TransactionType.EXPENSE,
            TransactionType.EXPENSE_REFUND,
        )
    }
    for transaction in transactions:
        if not transaction.is_void and transaction.type in totals:
            totals[transaction.type] += transaction.amount_minor
    return IncomeExpenseTotals(
        income_minor=totals[TransactionType.INCOME],
        gross_expense_minor=totals[TransactionType.EXPENSE],
        expense_refund_minor=totals[TransactionType.EXPENSE_REFUND],
        net_expense_minor=(
            totals[TransactionType.EXPENSE]
            - totals[TransactionType.EXPENSE_REFUND]
        ),
    )


__all__ = ("IncomeExpenseTotals", "calculate_income_expense")
