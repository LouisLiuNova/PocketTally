"""交易创建、读取、更新和作废路由。"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Query, Response, status

from app.api.errors import (
    NOT_FOUND_CONFLICT_RESPONSES,
    NOT_FOUND_RESPONSES,
    VALIDATION_RESPONSES,
    ApiError,
)
from app.api.routes.common import map_ledger_error
from app.dependencies import SessionDep
from app.ledger import (
    LedgerError,
    post_expense_refund,
    post_transaction,
    update_transaction,
    void_transaction_by_id,
)
from app.models import Transaction
from app.resources import get_transaction, list_transactions
from app.schemas import (
    ExpenseRefundCreate,
    TransactionCreate,
    TransactionRead,
    TransactionUpdate,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])
TransactionId = Annotated[
    UUID,
    Path(alias="transactionId", description="交易 UUID。"),
]


@router.get(
    "",
    response_model=list[TransactionRead],
    responses=VALIDATION_RESPONSES,
    operation_id="listTransactions",
)
def list_transaction_routes(
    session: SessionDep,
    include_voided: bool = Query(False, alias="includeVoided"),
) -> list[TransactionRead]:
    """返回交易及其有界关系摘要。"""

    return [
        TransactionRead.from_orm_model(transaction)
        for transaction in list_transactions(session, include_voided=include_voided)
    ]


def require_transaction(session: SessionDep, transaction_id: UUID) -> Transaction:
    """读取交易，不存在时返回稳定错误。"""

    transaction = get_transaction(session, str(transaction_id))
    if transaction is None:
        raise ApiError(404, "transaction_not_found", "交易不存在")
    return transaction


def read_after_write(session: SessionDep, transaction_id: str) -> TransactionRead:
    """刷新会话后读取完整交易响应。"""

    session.expire_all()
    transaction = get_transaction(session, transaction_id)
    if transaction is None:
        raise RuntimeError("写入后的交易无法读取")
    return TransactionRead.from_orm_model(transaction)


@router.post(
    "",
    response_model=TransactionRead,
    status_code=status.HTTP_201_CREATED,
    responses=NOT_FOUND_CONFLICT_RESPONSES,
    operation_id="createTransaction",
)
def create_transaction_route(
    payload: TransactionCreate,
    response: Response,
    session: SessionDep,
) -> TransactionRead:
    """创建一笔经过完整矩阵校验的基础交易。"""

    try:
        transaction = post_transaction(
            session,
            Transaction(**payload.to_orm_kwargs()),
            tag_ids=payload.tag_ids_for_relation(),
        )
    except LedgerError as error:
        raise map_ledger_error(error) from error
    response.headers["Location"] = f"/api/v1/transactions/{transaction.id}"
    return read_after_write(session, transaction.id)


@router.post(
    "/refunds",
    response_model=TransactionRead,
    status_code=status.HTTP_201_CREATED,
    responses=NOT_FOUND_CONFLICT_RESPONSES,
    operation_id="createExpenseRefund",
)
def create_expense_refund_route(
    payload: ExpenseRefundCreate,
    response: Response,
    session: SessionDep,
) -> TransactionRead:
    """创建由原支出派生账户和分类的退款。"""

    try:
        transaction = post_expense_refund(session, payload)
    except LedgerError as error:
        raise map_ledger_error(error) from error
    response.headers["Location"] = f"/api/v1/transactions/{transaction.id}"
    return read_after_write(session, transaction.id)


@router.get(
    "/{transactionId}",
    response_model=TransactionRead,
    responses=NOT_FOUND_RESPONSES,
    operation_id="getTransaction",
)
def get_transaction_route(
    transaction_id: TransactionId,
    session: SessionDep,
) -> TransactionRead:
    """返回一个交易及其有界关系摘要。"""

    return TransactionRead.from_orm_model(require_transaction(session, transaction_id))


@router.patch(
    "/{transactionId}",
    response_model=TransactionRead,
    responses=NOT_FOUND_CONFLICT_RESPONSES,
    operation_id="updateTransaction",
)
def patch_transaction_route(
    transaction_id: TransactionId,
    payload: TransactionUpdate,
    session: SessionDep,
) -> TransactionRead:
    """合并部分字段后校验并更新完整交易状态。"""

    transaction = require_transaction(session, transaction_id)
    try:
        update_transaction(
            session,
            transaction,
            tag_ids=payload.tag_ids_for_relation(),
            **payload.to_orm_kwargs(),
        )
    except LedgerError as error:
        raise map_ledger_error(error) from error
    return read_after_write(session, transaction.id)


@router.post(
    "/{transactionId}/void",
    response_model=TransactionRead,
    responses=NOT_FOUND_RESPONSES,
    operation_id="voidTransaction",
)
def void_transaction_route(
    transaction_id: TransactionId,
    session: SessionDep,
) -> TransactionRead:
    """幂等作废交易，并撤销其一次余额影响。"""

    try:
        transaction = void_transaction_by_id(session, str(transaction_id))
    except LedgerError as error:
        raise map_ledger_error(error) from error
    return read_after_write(session, transaction.id)
