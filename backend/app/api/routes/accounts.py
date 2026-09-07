"""账户基础维护路由。"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Response, status
from sqlmodel import select

from app.api.errors import (
    CONFLICT_RESPONSES,
    NOT_FOUND_CONFLICT_RESPONSES,
    NOT_FOUND_RESPONSES,
    VALIDATION_RESPONSES,
    ApiError,
)
from app.api.routes.common import map_resource_error
from app.dependencies import SessionDep
from app.models import Account
from app.resources import (
    ResourceError,
    create_account,
    delete_account,
    update_account,
)
from app.schemas import AccountCreate, AccountRead, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["accounts"])
AccountId = Annotated[UUID, Path(alias="accountId", description="账户 UUID。")]


def require_account(session: SessionDep, account_id: UUID) -> Account:
    """读取账户，不存在时返回稳定错误。"""

    account = session.get(Account, str(account_id))
    if account is None:
        raise ApiError(404, "account_not_found", "账户不存在")
    return account


@router.get(
    "",
    response_model=list[AccountRead],
    responses=VALIDATION_RESPONSES,
    operation_id="listAccounts",
)
def list_accounts(session: SessionDep) -> list[AccountRead]:
    """按创建时间和 ID 返回全部账户。"""

    accounts = session.exec(
        select(Account).order_by(Account.created_at, Account.id)
    ).all()
    return [AccountRead.from_orm_model(account) for account in accounts]


@router.post(
    "",
    response_model=AccountRead,
    status_code=status.HTTP_201_CREATED,
    responses=CONFLICT_RESPONSES,
    operation_id="createAccount",
)
def create_account_route(
    payload: AccountCreate,
    response: Response,
    session: SessionDep,
) -> AccountRead:
    """创建零余额账户。"""

    try:
        account = create_account(session, Account(**payload.to_orm_kwargs()))
    except ResourceError as error:
        raise map_resource_error(error) from error
    response.headers["Location"] = f"/api/v1/accounts/{account.id}"
    return AccountRead.from_orm_model(account)


@router.get(
    "/{accountId}",
    response_model=AccountRead,
    responses=NOT_FOUND_RESPONSES,
    operation_id="getAccount",
)
def get_account(account_id: AccountId, session: SessionDep) -> AccountRead:
    """返回一个账户。"""

    return AccountRead.from_orm_model(require_account(session, account_id))


@router.patch(
    "/{accountId}",
    response_model=AccountRead,
    responses=NOT_FOUND_CONFLICT_RESPONSES,
    operation_id="updateAccount",
)
def patch_account(
    account_id: AccountId,
    payload: AccountUpdate,
    session: SessionDep,
) -> AccountRead:
    """部分更新一个账户。"""

    account = require_account(session, account_id)
    try:
        update_account(session, account, **payload.to_orm_kwargs())
    except ResourceError as error:
        raise map_resource_error(error) from error
    return AccountRead.from_orm_model(account)


@router.delete(
    "/{accountId}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=NOT_FOUND_CONFLICT_RESPONSES,
    operation_id="deleteAccount",
)
def remove_account(account_id: AccountId, session: SessionDep) -> None:
    """删除未被历史交易引用的账户。"""

    account = require_account(session, account_id)
    try:
        delete_account(session, account)
    except ResourceError as error:
        raise map_resource_error(error) from error
