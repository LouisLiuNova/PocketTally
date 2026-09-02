"""账本余额计算和原子记账服务。"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlmodel import Session, select

from app.models import (
    Account,
    BalanceAdjustmentDirection,
    Transaction,
    TransactionType,
)
from app.schemas.transaction import BalanceAdjustmentCreate


class LedgerError(ValueError):
    """账本交易不符合可记账条件。"""


@dataclass(frozen=True, slots=True)
class Posting:
    """一笔交易对单个账户产生的余额变化。"""

    account_id: str
    delta_minor: int


def transaction_postings(transaction: Transaction) -> tuple[Posting, ...]:
    """将有效交易转换为账户余额分录。

    作废交易不再参与余额计算，但仍保留在交易表中以维护审计链。

    Args:
        transaction: 待计算的交易。

    Returns:
        按交易资金方向生成的余额分录。

    Raises:
        LedgerError: 交易字段无法表达合法资金方向时抛出。
    """

    if transaction.voided_at is not None:
        return ()
    if transaction.amount_minor <= 0:
        raise LedgerError("交易金额必须为正整数分")

    try:
        transaction_type = TransactionType(transaction.type)
    except ValueError as error:
        raise LedgerError(f"不支持的交易类型: {transaction.type}") from error
    amount = transaction.amount_minor
    if transaction_type is TransactionType.INCOME:
        if transaction.src_account_id is not None or transaction.dest_account_id is None:
            raise LedgerError("收入交易必须只有目标账户")
        return (Posting(transaction.dest_account_id, amount),)
    if transaction_type is TransactionType.EXPENSE:
        if transaction.src_account_id is None or transaction.dest_account_id is not None:
            raise LedgerError("支出交易必须只有来源账户")
        return (Posting(transaction.src_account_id, -amount),)
    if transaction_type is TransactionType.TRANSFER:
        if (
            transaction.src_account_id is None
            or transaction.dest_account_id is None
            or transaction.src_account_id == transaction.dest_account_id
        ):
            raise LedgerError("转账必须使用两个不同的账户")
        return (
            Posting(transaction.src_account_id, -amount),
            Posting(transaction.dest_account_id, amount),
        )
    if transaction_type is TransactionType.BALANCE_ADJUSTMENT:
        if transaction.src_account_id is None or transaction.dest_account_id is not None:
            raise LedgerError("余额调整必须指定一个受影响账户")
        if transaction.balance_adjustment_direction is BalanceAdjustmentDirection.INCREASE:
            delta = amount
        elif transaction.balance_adjustment_direction is BalanceAdjustmentDirection.DECREASE:
            delta = -amount
        else:
            raise LedgerError("余额调整必须指定增加或减少方向")
        return (Posting(transaction.src_account_id, delta),)
    raise LedgerError(f"不支持的交易类型: {transaction.type}")


def calculate_balances(
    transactions: Iterable[Transaction],
) -> dict[str, int]:
    """从有效交易重算账户余额。

    账户不存在交易时不会出现在结果中，调用方应将其解释为 0；这里不保存
    任何初始余额，因此余额的基准永远是 0。

    Args:
        transactions: 需要参与重算的交易集合。

    Returns:
        账户 ID 到最小货币单位余额的映射。

    Raises:
        LedgerError: 交易资金方向不合法时抛出。
    """

    balances: dict[str, int] = {}
    for transaction in transactions:
        for posting in transaction_postings(transaction):
            balances[posting.account_id] = (
                balances.get(posting.account_id, 0) + posting.delta_minor
            )
    return balances


def _require_transaction(session: Session) -> None:
    """确保账本写入由显式事务包裹。"""

    if not session.in_transaction():
        raise LedgerError("账本写入必须在显式数据库事务中执行")


def recalculate_account_balances(
    session: Session,
    account_ids: Iterable[str] | None = None,
) -> dict[str, int]:
    """用有效交易重建账户当前余额投影。

    Args:
        session: 当前数据库会话。
        account_ids: 可选的受影响账户 ID；省略时重算全部账户。

    Returns:
        已重算账户的余额映射。

    Raises:
        LedgerError: 交易资金方向不合法或未处于事务中时抛出。
    """

    _require_transaction(session)
    accounts = list(session.exec(select(Account)))
    transactions = list(session.exec(select(Transaction)))
    balances = calculate_balances(transactions)
    target_ids = set(account_ids) if account_ids is not None else None
    result: dict[str, int] = {}
    for account in accounts:
        if target_ids is not None and account.id not in target_ids:
            continue
        account.amount_minor = balances.get(account.id, 0)
        result[account.id] = account.amount_minor
    session.flush()
    return result


def post_transaction(session: Session, transaction: Transaction) -> Transaction:
    """在同一事务中写入交易并同步受影响账户余额。

    调用方负责使用 ``with session.begin():`` 控制提交或回滚；本函数不会
    提前提交，从而避免交易已写入而余额尚未同步的中间状态。

    Args:
        session: 当前数据库会话。
        transaction: 待写入的交易。

    Returns:
        已刷新数据库 ID 和默认字段的交易实例。

    Raises:
        LedgerError: 未处于显式事务或交易资金方向不合法时抛出。
    """

    _require_transaction(session)
    if transaction.voided_at is not None:
        raise LedgerError("不能直接写入已作废交易")
    postings = transaction_postings(transaction)
    account_ids = {posting.account_id for posting in postings}
    if account_ids:
        existing_account_ids = {
            account.id
            for account in session.exec(
                select(Account).where(Account.id.in_(account_ids))
            )
        }
        if existing_account_ids != account_ids:
            raise LedgerError("交易引用了不存在的账户")
    session.add(transaction)
    session.flush()
    recalculate_account_balances(session, account_ids=account_ids)
    return transaction


def post_balance_adjustment(
    session: Session,
    request: BalanceAdjustmentCreate,
) -> Transaction:
    """将余额调整请求作为真实交易原子写入。

    Args:
        session: 当前数据库会话。
        request: 账户、方向、金额和发生时间请求。

    Returns:
        已写入的余额调整交易。
    """

    return post_transaction(session, Transaction(**request.to_orm_kwargs()))


def update_transaction(
    session: Session,
    transaction: Transaction,
    **changes: object,
) -> Transaction:
    """在同一事务中更新交易并重算受影响账户余额。

    Args:
        session: 当前数据库会话。
        transaction: 已加载的交易实例。
        **changes: 要更新的交易字段。

    Returns:
        已更新的交易实例。

    Raises:
        LedgerError: 交易已作废、未处于显式事务或更新后资金方向不合法时抛出。
    """

    _require_transaction(session)
    if transaction.voided_at is not None:
        raise LedgerError("作废交易不可直接修改")
    old_account_ids = {
        posting.account_id for posting in transaction_postings(transaction)
    }
    for field_name, value in changes.items():
        if not hasattr(transaction, field_name):
            raise LedgerError(f"不支持更新交易字段: {field_name}")
        setattr(transaction, field_name, value)
    new_postings = transaction_postings(transaction)
    session.add(transaction)
    session.flush()
    recalculate_account_balances(
        session,
        account_ids=old_account_ids | {posting.account_id for posting in new_postings},
    )
    return transaction


def void_transaction(
    session: Session,
    transaction: Transaction,
    voided_at: datetime | None = None,
) -> Transaction:
    """作废交易并在同一事务中重算账户余额。

    Args:
        session: 当前数据库会话。
        transaction: 待作废的交易实例。
        voided_at: 作废时间，省略时使用当前 UTC 时间。

    Returns:
        已标记作废且仍保留在数据库中的交易实例。

    Raises:
        LedgerError: 交易已作废或未处于显式事务时抛出。
    """

    _require_transaction(session)
    if transaction.voided_at is not None:
        raise LedgerError("交易已经作废")
    account_ids = {posting.account_id for posting in transaction_postings(transaction)}
    transaction.voided_at = voided_at or datetime.now(UTC)
    session.add(transaction)
    session.flush()
    recalculate_account_balances(session, account_ids=account_ids)
    return transaction


__all__ = (
    "LedgerError",
    "Posting",
    "calculate_balances",
    "post_balance_adjustment",
    "post_transaction",
    "recalculate_account_balances",
    "transaction_postings",
    "update_transaction",
    "void_transaction",
)
