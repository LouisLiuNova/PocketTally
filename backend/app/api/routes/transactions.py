"""交易只读路由。"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path

from app.api.errors import NOT_FOUND_RESPONSES, VALIDATION_RESPONSES, ApiError
from app.dependencies import SessionDep
from app.resources import get_transaction, list_transactions
from app.schemas import TransactionRead

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
def list_transaction_routes(session: SessionDep) -> list[TransactionRead]:
    """返回交易及其有界关系摘要。"""

    return [
        TransactionRead.from_orm_model(transaction)
        for transaction in list_transactions(session)
    ]


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

    transaction = get_transaction(session, str(transaction_id))
    if transaction is None:
        raise ApiError(404, "transaction_not_found", "交易不存在")
    return TransactionRead.from_orm_model(transaction)
