"""交易创建、读取、更新和作废路由。"""

from typing import Annotated, Literal
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
from app.models import Transaction, TransactionType
from app.resources import get_transaction, list_transactions_page, refund_summary
from app.schemas import (
    ExpenseRefundCreate,
    RefundSummary,
    TransactionCreate,
    TransactionPage,
    TransactionRead,
    TransactionUpdate,
)
from app.time_utils import AwareDateTime

router = APIRouter(prefix="/transactions", tags=["transactions"])
TransactionId = Annotated[
    UUID,
    Path(alias="transactionId", description="交易 UUID。"),
]


@router.get(
    "",
    response_model=TransactionPage,
    responses=VALIDATION_RESPONSES,
    operation_id="listTransactions",
)
def list_transaction_routes(
    session: SessionDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    start_at: AwareDateTime | None = Query(None, alias="startAt"),
    end_at: AwareDateTime | None = Query(None, alias="endAt"),
    transaction_type: TransactionType | None = Query(None, alias="type"),
    account_id: UUID | None = Query(None, alias="accountId"),
    source_account_id: UUID | None = Query(None, alias="sourceAccountId"),
    destination_account_id: UUID | None = Query(None, alias="destinationAccountId"),
    category_id: UUID | None = Query(None, alias="categoryId"),
    include_descendants: bool = Query(False, alias="includeDescendants"),
    tag_id: UUID | None = Query(None, alias="tagId"),
    q: str | None = Query(None),
    status_filter: Literal["active", "voided", "all"] = Query("active", alias="status"),
    refund_of_transaction_id: UUID | None = Query(None, alias="refundOfTransactionId"),
    sort_by: Literal["occurredAt", "amount"] = Query("occurredAt", alias="sortBy"),
    sort_order: Literal["asc", "desc"] = Query("desc", alias="sortOrder"),
) -> TransactionPage:
    """按组合条件返回分页交易；旧的 ``includeVoided`` 参数已移除。"""

    if start_at is not None and end_at is not None and start_at >= end_at:
        raise ApiError(422, "validation_error", "startAt 必须早于 endAt")
    transactions, total = list_transactions_page(
        session,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        start_at=start_at,
        end_at=end_at,
        transaction_type=transaction_type,
        account_id=str(account_id) if account_id else None,
        source_account_id=str(source_account_id) if source_account_id else None,
        destination_account_id=str(destination_account_id) if destination_account_id else None,
        category_id=str(category_id) if category_id else None,
        include_descendants=include_descendants,
        tag_id=str(tag_id) if tag_id else None,
        query=q,
        status=status_filter,
        refund_of_transaction_id=str(refund_of_transaction_id) if refund_of_transaction_id else None,
    )
    return TransactionPage(
        items=[TransactionRead.from_orm_model(item) for item in transactions],
        total=total,
        page=page,
        page_size=page_size,
    )


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


@router.get(
    "/{transactionId}/refund-summary",
    response_model=RefundSummary,
    responses=NOT_FOUND_CONFLICT_RESPONSES,
    operation_id="getRefundSummary",
)
def get_refund_summary_route(
    transaction_id: TransactionId,
    session: SessionDep,
) -> RefundSummary:
    """返回原支出的有界退款额度摘要。"""

    original, refunded, count = refund_summary(session, str(transaction_id))
    if original is None:
        raise ApiError(404, "transaction_not_found", "交易不存在")
    if original.type is not TransactionType.EXPENSE:
        raise ApiError(409, "refund_original_not_expense", "只有支出交易可以查询退款摘要")
    remaining = 0 if original.is_void else max(original.amount_minor - refunded, 0)
    return RefundSummary(
        original_amount_minor=original.amount_minor,
        refunded_amount_minor=refunded,
        remaining_refundable_amount_minor=remaining,
        can_refund=not original.is_void and remaining > 0,
        active_refund_count=count,
    )


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
