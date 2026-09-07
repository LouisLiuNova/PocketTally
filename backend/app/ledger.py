"""账本余额计算和原子记账服务。"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import update
from sqlmodel import Session, select

from app.models import (
    Account,
    AccountType,
    BalanceAdjustmentDirection,
    Category,
    CategoryPurpose,
    Tag,
    Transaction,
    TransactionType,
)
from app.money import amount_to_minor
from app.schemas.transaction import BalanceAdjustmentCreate, ExpenseRefundCreate


class LedgerErrorCode(StrEnum):
    """账本服务对外稳定的错误码。"""

    INVALID_TRANSACTION = "invalid_transaction"
    ACCOUNT_NOT_FOUND = "account_not_found"
    CATEGORY_NOT_FOUND = "category_not_found"
    TAG_NOT_FOUND = "tag_not_found"
    INSUFFICIENT_BALANCE = "insufficient_balance"
    TRANSACTION_VOIDED = "transaction_voided"
    TRANSACTION_NOT_FOUND = "transaction_not_found"
    REFUND_LIMIT_EXCEEDED = "refund_limit_exceeded"
    ORIGINAL_HAS_ACTIVE_REFUNDS = "original_has_active_refunds"


class LedgerError(ValueError):
    """账本交易不符合可记账条件。"""

    def __init__(
        self,
        message: str,
        code: LedgerErrorCode = LedgerErrorCode.INVALID_TRANSACTION,
    ) -> None:
        """初始化稳定的账本业务错误。"""

        super().__init__(message)
        self.code = code


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

    if transaction.is_void:
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
    if transaction_type is TransactionType.EXPENSE_REFUND:
        if transaction.src_account_id is None or transaction.dest_account_id is not None:
            raise LedgerError("支出退款必须只有原支出的来源账户")
        return (Posting(transaction.src_account_id, amount),)
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


def validate_transaction_category(
    session: Session,
    transaction: Transaction,
) -> None:
    """验证完整交易状态中的分类必填性和用途匹配。

    Args:
        session: 当前数据库会话。
        transaction: 待创建或更新的完整交易状态。

    Raises:
        LedgerError: 分类缺失、不存在、用途不匹配或不应出现时抛出。
    """

    try:
        transaction_type = TransactionType(transaction.type)
    except ValueError as error:
        raise LedgerError(f"不支持的交易类型: {transaction.type}") from error
    required_purpose = {
        TransactionType.INCOME: CategoryPurpose.INCOME,
        TransactionType.EXPENSE: CategoryPurpose.EXPENSE,
        TransactionType.EXPENSE_REFUND: CategoryPurpose.EXPENSE,
    }.get(transaction_type)
    if required_purpose is None:
        if transaction.category is not None:
            raise LedgerError("转账和余额调整不能引用分类")
        return
    if transaction.category is None:
        raise LedgerError("普通收入和支出交易必须引用分类")
    category = session.get(Category, transaction.category)
    if category is None:
        raise LedgerError("交易引用了不存在的分类", LedgerErrorCode.CATEGORY_NOT_FOUND)
    if category.purpose != required_purpose:
        raise LedgerError("交易类型与分类用途不匹配")


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
        new_balance = balances.get(account.id, 0)
        if account.type is AccountType.DEBIT and new_balance < 0:
            raise LedgerError("借记账户余额不足", LedgerErrorCode.INSUFFICIENT_BALANCE)
        account.amount_minor = new_balance
        result[account.id] = account.amount_minor
    session.flush()
    return result


def _resolve_tags(session: Session, tag_ids: Iterable[str]) -> list[Tag]:
    """按请求顺序读取标签，并拒绝任何不存在的标签。"""

    tags: list[Tag] = []
    for tag_id in tag_ids:
        tag = session.get(Tag, tag_id)
        if tag is None:
            raise LedgerError("交易引用了不存在的标签", LedgerErrorCode.TAG_NOT_FOUND)
        tags.append(tag)
    return tags


def validate_complete_transaction(
    session: Session,
    transaction: Transaction,
    *,
    tag_ids: Iterable[str] = (),
    _refund_entry: bool = False,
) -> tuple[tuple[Posting, ...], list[Tag]]:
    """统一校验一笔完整基础交易及其全部关系。

    Args:
        session: 当前数据库会话。
        transaction: 创建、PATCH 合并结果或未来导入生成的完整候选状态。
        tag_ids: 候选交易的完整标签 ID 集合。

    Returns:
        已验证的余额分录和标签对象。

    Raises:
        LedgerError: 交易矩阵、分类用途或任一关系不合法时抛出。
    """

    if transaction.is_void or transaction.voided_at is not None:
        raise LedgerError("不能通过普通写入设置作废状态")
    if not _refund_entry and (
        transaction.type == TransactionType.EXPENSE_REFUND
        or transaction.refund_of_transaction_id is not None
    ):
        raise LedgerError("退款只能通过专用退款入口创建，不能通过普通交易修改")
    if transaction.type != TransactionType.BALANCE_ADJUSTMENT and (
        transaction.balance_adjustment_direction is not None
    ):
        raise LedgerError("只有余额调整可以设置调整方向")
    postings = transaction_postings(transaction)
    validate_transaction_category(session, transaction)
    account_ids = {posting.account_id for posting in postings}
    existing_account_ids = {
        account.id
        for account in session.exec(
            select(Account).where(Account.id.in_(account_ids))
        )
    }
    if existing_account_ids != account_ids:
        raise LedgerError("交易引用了不存在的账户", LedgerErrorCode.ACCOUNT_NOT_FOUND)
    return postings, _resolve_tags(session, tag_ids)


def post_transaction(
    session: Session,
    transaction: Transaction,
    *,
    tag_ids: Iterable[str] = (),
) -> Transaction:
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
    postings, tags = validate_complete_transaction(
        session,
        transaction,
        tag_ids=tag_ids,
    )
    account_ids = {posting.account_id for posting in postings}
    transaction.tags = tags
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


def post_expense_refund(session: Session, request: ExpenseRefundCreate) -> Transaction:
    """在调用方事务内校验退款累计额，派生原支出关系并更新余额。

    Args:
        session: 已开启事务的数据库会话。
        request: 仅含原支出、金额、时间和说明的退款请求。

    Returns:
        已写入的退款交易。

    Raises:
        LedgerError: 原交易无效或累计退款超过原支出时抛出。
    """

    _require_transaction(session)
    original_id = str(request.refund_of_transaction_id)
    # 在读取累计额前取得 SQLite 写锁，避免两个退款请求同时通过额度检查。
    session.exec(
        update(Transaction)
        .where(
            Transaction.id == original_id,
            Transaction.type == TransactionType.EXPENSE,
            Transaction.is_void.is_(False),
        )
        .values(id=Transaction.id)
    )
    original = session.get(Transaction, original_id)
    if original is None:
        raise LedgerError("原支出不存在", LedgerErrorCode.TRANSACTION_NOT_FOUND)
    if original.type != TransactionType.EXPENSE or original.is_void:
        raise LedgerError("只能对有效支出退款")
    refunded = sum(
        refund.amount_minor
        for refund in session.exec(select(Transaction).where(
            Transaction.refund_of_transaction_id == original.id,
            Transaction.is_void.is_(False),
        ))
    )
    amount_minor = amount_to_minor(request.amount)
    if refunded + amount_minor > original.amount_minor:
        raise LedgerError("累计退款超过原支出金额", LedgerErrorCode.REFUND_LIMIT_EXCEEDED)
    transaction = Transaction(
        type=TransactionType.EXPENSE_REFUND,
        refund_of_transaction_id=original.id,
        src_account_id=original.src_account_id,
        dest_account_id=None,
        category=original.category,
        amount_minor=amount_minor,
        occurred_at=request.occurred_at,
        description=request.description,
    )
    postings, _ = validate_complete_transaction(session, transaction, _refund_entry=True)
    session.add(transaction)
    session.flush()
    recalculate_account_balances(session, (posting.account_id for posting in postings))
    return transaction


def has_active_refunds(session: Session, transaction_id: str) -> bool:
    """判断原支出是否仍有未作废退款。"""

    return session.exec(
        select(Transaction.id).where(
            Transaction.refund_of_transaction_id == transaction_id,
            Transaction.is_void.is_(False),
        )
    ).first() is not None


def update_transaction(
    session: Session,
    transaction: Transaction,
    *,
    tag_ids: Iterable[str] | None = None,
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
    if transaction.is_void:
        raise LedgerError("作废交易不可直接修改", LedgerErrorCode.TRANSACTION_VOIDED)
    protected_fields = {
        "type",
        "src_account_id",
        "dest_account_id",
        "amount_minor",
        "category",
        "balance_adjustment_direction",
        "refund_of_transaction_id",
    }
    if transaction.type == TransactionType.EXPENSE_REFUND:
        if protected_fields.intersection(changes):
            raise LedgerError("退款的类型、金额、账户、分类和原支出不可修改")
        refund_entry = True
    else:
        refund_entry = False
        if (
            transaction.type == TransactionType.EXPENSE
            and protected_fields.intersection(changes)
            and has_active_refunds(session, transaction.id)
        ):
            raise LedgerError(
                "原支出存在有效退款，请先作废退款",
                LedgerErrorCode.ORIGINAL_HAS_ACTIVE_REFUNDS,
            )
    old_account_ids = {posting.account_id for posting in transaction_postings(transaction)}
    candidate_values = {
        "type": transaction.type,
        "src_account_id": transaction.src_account_id,
        "dest_account_id": transaction.dest_account_id,
        "amount_minor": transaction.amount_minor,
        "description": transaction.description,
        "category": transaction.category,
        "refund_of_transaction_id": transaction.refund_of_transaction_id,
        "balance_adjustment_direction": transaction.balance_adjustment_direction,
        "is_void": transaction.is_void,
        "voided_at": transaction.voided_at,
        "occurred_at": transaction.occurred_at,
    }
    for field_name, value in changes.items():
        if not hasattr(transaction, field_name):
            raise LedgerError(f"不支持更新交易字段: {field_name}")
        candidate_values[field_name] = value
    candidate = Transaction(**candidate_values)
    candidate_tag_ids = (
        list(tag_ids) if tag_ids is not None else [tag.id for tag in transaction.tags]
    )
    new_postings, new_tags = validate_complete_transaction(
        session,
        candidate,
        tag_ids=candidate_tag_ids,
        _refund_entry=refund_entry,
    )
    new_account_ids = {posting.account_id for posting in new_postings}
    for field_name, value in changes.items():
        setattr(transaction, field_name, value)
    if tag_ids is not None:
        transaction.tags = new_tags
    session.add(transaction)
    session.flush()
    recalculate_account_balances(
        session,
        account_ids=old_account_ids | new_account_ids,
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
    if transaction.is_void:
        return transaction
    if (
        transaction.type == TransactionType.EXPENSE
        and has_active_refunds(session, transaction.id)
    ):
        raise LedgerError(
            "原支出存在有效退款，请先作废退款",
            LedgerErrorCode.ORIGINAL_HAS_ACTIVE_REFUNDS,
        )
    account_ids = {posting.account_id for posting in transaction_postings(transaction)}
    effective_voided_at = voided_at or datetime.now(UTC)
    result = session.exec(
        update(Transaction)
        .where(Transaction.id == transaction.id, Transaction.is_void.is_(False))
        .values(is_void=True, voided_at=effective_voided_at)
    )
    if result.rowcount == 0:
        session.refresh(transaction)
        return transaction
    session.flush()
    session.refresh(transaction)
    recalculate_account_balances(session, account_ids=account_ids)
    return transaction


def void_transaction_by_id(
    session: Session,
    transaction_id: str,
    voided_at: datetime | None = None,
) -> Transaction:
    """以先写后读的条件更新幂等作废交易。

    条件更新先取得 SQLite 写锁，使并发请求按顺序判断 ``is_void``；只有
    首次请求会获得一条更新记录并重算余额，后续请求直接读取首次结果。

    Args:
        session: 当前数据库会话。
        transaction_id: 待作废的交易 ID。
        voided_at: 作废时间，省略时使用当前 UTC 时间。

    Returns:
        首次写入或已存在的作废交易。

    Raises:
        LedgerError: 交易不存在或未处于显式事务时抛出。
    """

    _require_transaction(session)
    existing = session.get(Transaction, transaction_id)
    if existing is None:
        raise LedgerError("交易不存在", LedgerErrorCode.TRANSACTION_NOT_FOUND)
    if (
        existing.type == TransactionType.EXPENSE
        and not existing.is_void
        and has_active_refunds(session, transaction_id)
    ):
        raise LedgerError(
            "原支出存在有效退款，请先作废退款",
            LedgerErrorCode.ORIGINAL_HAS_ACTIVE_REFUNDS,
        )
    effective_voided_at = voided_at or datetime.now(UTC)
    result = session.exec(
        update(Transaction)
        .where(Transaction.id == transaction_id, Transaction.is_void.is_(False))
        .values(is_void=True, voided_at=effective_voided_at)
    )
    transaction = session.get(Transaction, transaction_id)
    if transaction is None:
        raise LedgerError("交易不存在", LedgerErrorCode.TRANSACTION_NOT_FOUND)
    if result.rowcount == 0:
        return transaction
    account_ids = {
        account_id
        for account_id in (transaction.src_account_id, transaction.dest_account_id)
        if account_id is not None
    }
    recalculate_account_balances(session, account_ids=account_ids)
    session.refresh(transaction)
    return transaction


__all__ = (
    "LedgerError",
    "LedgerErrorCode",
    "Posting",
    "calculate_balances",
    "post_balance_adjustment",
    "post_expense_refund",
    "post_transaction",
    "recalculate_account_balances",
    "transaction_postings",
    "update_transaction",
    "validate_complete_transaction",
    "validate_transaction_category",
    "void_transaction",
    "void_transaction_by_id",
)
