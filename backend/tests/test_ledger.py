"""账本余额重算、余额调整和事务边界测试。"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func
from sqlmodel import Session, SQLModel, select

from app.ledger import (
    LedgerError,
    calculate_balances,
    post_balance_adjustment,
    post_transaction,
    update_transaction,
    void_transaction,
)
from app.models import (
    Account,
    AccountType,
    BalanceAdjustmentDirection,
    Transaction,
    TransactionType,
)
from app.schemas.transaction import BalanceAdjustmentCreate


def make_engine():
    """创建账本测试使用的内存数据库。"""

    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    return engine


def adjustment_request(
    account_id: str,
    direction: BalanceAdjustmentDirection,
    amount: float = 10,
) -> BalanceAdjustmentCreate:
    """创建一份测试余额调整请求。"""

    return BalanceAdjustmentCreate.model_validate(
        {
            "accountId": account_id,
            "direction": direction,
            "amount": amount,
            "occurredAt": datetime.now(UTC).isoformat(),
        }
    )


def test_calculate_balances_uses_zero_baseline_and_transaction_direction() -> None:
    """验证余额从零开始，并按四类交易的资金方向计算。"""

    first = str(uuid4())
    second = str(uuid4())
    now = datetime.now(UTC)
    transactions = [
        Transaction(
            type=TransactionType.INCOME,
            src_account_id=None,
            dest_account_id=first,
            amount_minor=1000,
            category=None,
            occurred_at=now,
        ),
        Transaction(
            type=TransactionType.EXPENSE,
            src_account_id=first,
            dest_account_id=None,
            amount_minor=200,
            category=None,
            occurred_at=now,
        ),
        Transaction(
            type=TransactionType.TRANSFER,
            src_account_id=first,
            dest_account_id=second,
            amount_minor=300,
            category=None,
            occurred_at=now,
        ),
        Transaction(
            type=TransactionType.BALANCE_ADJUSTMENT,
            src_account_id=second,
            dest_account_id=None,
            amount_minor=50,
            category=None,
            balance_adjustment_direction=BalanceAdjustmentDirection.INCREASE,
            occurred_at=now,
        ),
    ]

    assert calculate_balances(transactions) == {first: 500, second: 350}


def test_balance_adjustment_is_a_real_transaction_and_can_be_voided() -> None:
    """验证余额调整写入交易，作废后余额可重算恢复。"""

    engine = make_engine()
    account = Account(type=AccountType.CREDIT, name="信用账户")
    with Session(engine, expire_on_commit=False) as session:
        session.add(account)
        session.commit()

        with session.begin():
            transaction = post_balance_adjustment(
                session,
                adjustment_request(
                    account.id,
                    BalanceAdjustmentDirection.INCREASE,
                    amount=25,
                ),
            )

        refreshed_account = session.get(Account, account.id)
        assert refreshed_account is not None
        assert refreshed_account.amount_minor == 2500
        assert transaction.balance_adjustment_direction is BalanceAdjustmentDirection.INCREASE
        assert transaction.category is None

        session.rollback()
        with session.begin():
            update_transaction(session, transaction, amount_minor=3000)

        refreshed_account = session.get(Account, account.id)
        assert refreshed_account is not None
        assert refreshed_account.amount_minor == 3000

        session.rollback()
        with session.begin():
            void_transaction(session, transaction)

        refreshed_account = session.get(Account, account.id)
        assert refreshed_account is not None
        assert refreshed_account.amount_minor == 0
        assert session.get(Transaction, transaction.id).voided_at is not None


def test_transfer_updates_both_accounts_atomically() -> None:
    """验证转账同时影响两个账户且总余额不变。"""

    engine = make_engine()
    source = Account(type=AccountType.CREDIT, name="转出账户")
    destination = Account(type=AccountType.CREDIT, name="转入账户")
    with Session(engine, expire_on_commit=False) as session:
        session.add_all([source, destination])
        session.commit()

        with session.begin():
            post_balance_adjustment(
                session,
                adjustment_request(
                    source.id,
                    BalanceAdjustmentDirection.INCREASE,
                    amount=10,
                ),
            )
            post_balance_adjustment(
                session,
                adjustment_request(
                    destination.id,
                    BalanceAdjustmentDirection.INCREASE,
                    amount=2,
                ),
            )

        transfer = Transaction(
            type=TransactionType.TRANSFER,
            src_account_id=source.id,
            dest_account_id=destination.id,
            amount_minor=300,
            category=None,
            occurred_at=datetime.now(UTC),
        )
        with session.begin():
            post_transaction(session, transfer)

        balances = {
            account.id: account.amount_minor
            for account in session.exec(select(Account)).all()
        }
        assert balances == {source.id: 700, destination.id: 500}
        assert sum(balances.values()) == 1200


def test_failed_atomic_post_does_not_leave_transaction_or_balance_change() -> None:
    """验证同一事务失败时交易和余额一起回滚。"""

    engine = make_engine()
    account = Account(type=AccountType.CREDIT, name="回滚账户")
    with Session(engine, expire_on_commit=False) as session:
        session.add(account)
        session.commit()

        with pytest.raises(LedgerError), session.begin():
            post_balance_adjustment(
                session,
                adjustment_request(
                    account.id,
                    BalanceAdjustmentDirection.INCREASE,
                    amount=10,
                ),
            )
            invalid_transfer = Transaction(
                type=TransactionType.TRANSFER,
                src_account_id=account.id,
                dest_account_id=account.id,
                amount_minor=1,
                category=None,
                occurred_at=datetime.now(UTC),
            )
            post_transaction(session, invalid_transfer)

        refreshed_account = session.get(Account, account.id)
        assert refreshed_account is not None
        assert refreshed_account.amount_minor == 0
        assert session.exec(select(func.count()).select_from(Transaction)).one() == 0


def test_ledger_writes_require_an_explicit_transaction() -> None:
    """验证账本服务不会在缺少事务边界时写入半成品。"""

    engine = make_engine()
    account = Account(type=AccountType.CREDIT, name="事务边界账户")
    with Session(engine, expire_on_commit=False) as session:
        session.add(account)
        session.commit()

        with pytest.raises(LedgerError, match="显式数据库事务"):
            post_balance_adjustment(
                session,
                adjustment_request(
                    account.id,
                    BalanceAdjustmentDirection.INCREASE,
                ),
            )
