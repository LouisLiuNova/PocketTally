"""账户、分类、标签与交易读取的应用服务。"""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from sqlalchemy import and_, func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import Session, select

from app.categories import CategoryHierarchyError, create_category, update_category
from app.models import (
    Account,
    Category,
    Tag,
    Transaction,
    TransactionTag,
    TransactionType,
)


class ResourceErrorCode(StrEnum):
    """基础资源服务的稳定业务错误码。"""

    ACCOUNT_NOT_FOUND = "account_not_found"
    CATEGORY_NOT_FOUND = "category_not_found"
    TAG_NOT_FOUND = "tag_not_found"
    TRANSACTION_NOT_FOUND = "transaction_not_found"
    ACCOUNT_NAME_CONFLICT = "account_name_conflict"
    CATEGORY_NAME_CONFLICT = "category_name_conflict"
    TAG_NAME_CONFLICT = "tag_name_conflict"
    ACCOUNT_IN_USE = "account_in_use"
    CATEGORY_IN_USE = "category_in_use"
    TAG_IN_USE = "tag_in_use"


class ResourceError(ValueError):
    """基础资源操作无法完成。"""

    def __init__(self, code: ResourceErrorCode, message: str) -> None:
        """初始化资源业务错误。"""

        super().__init__(message)
        self.code = code


def _ensure_unique_name(
    session: Session,
    model: type[Account | Category | Tag],
    name: str,
    *,
    current_id: str | None,
    code: ResourceErrorCode,
) -> None:
    """在写入前按 SQLite NOCASE 规则检查名称唯一性。"""

    statement = select(model.id).where(func.lower(model.name) == name.lower())
    if current_id is not None:
        statement = statement.where(model.id != current_id)
    if session.exec(statement).first() is not None:
        raise ResourceError(code, "名称已被使用")


def _flush_or_name_conflict(
    session: Session,
    code: ResourceErrorCode,
) -> None:
    """刷新写入，并把唯一性失败收敛为稳定错误。"""

    try:
        session.flush()
    except IntegrityError as error:
        raise ResourceError(code, "名称已被使用") from error


def create_account(session: Session, account: Account) -> Account:
    """创建账户并保持事务提交权在调用方。"""

    _ensure_unique_name(
        session,
        Account,
        account.name,
        current_id=None,
        code=ResourceErrorCode.ACCOUNT_NAME_CONFLICT,
    )
    session.add(account)
    _flush_or_name_conflict(session, ResourceErrorCode.ACCOUNT_NAME_CONFLICT)
    return account


def update_account(session: Session, account: Account, **changes: object) -> Account:
    """更新账户可编辑字段。"""

    if "name" in changes:
        _ensure_unique_name(
            session,
            Account,
            str(changes["name"]),
            current_id=account.id,
            code=ResourceErrorCode.ACCOUNT_NAME_CONFLICT,
        )
    for field_name, value in changes.items():
        setattr(account, field_name, value)
    session.add(account)
    _flush_or_name_conflict(session, ResourceErrorCode.ACCOUNT_NAME_CONFLICT)
    return account


def create_tag(session: Session, tag: Tag) -> Tag:
    """创建标签并保持事务提交权在调用方。"""

    _ensure_unique_name(
        session,
        Tag,
        tag.name,
        current_id=None,
        code=ResourceErrorCode.TAG_NAME_CONFLICT,
    )
    session.add(tag)
    _flush_or_name_conflict(session, ResourceErrorCode.TAG_NAME_CONFLICT)
    return tag


def update_tag(session: Session, tag: Tag, **changes: object) -> Tag:
    """更新标签可编辑字段。"""

    if "name" in changes:
        _ensure_unique_name(
            session,
            Tag,
            str(changes["name"]),
            current_id=tag.id,
            code=ResourceErrorCode.TAG_NAME_CONFLICT,
        )
    for field_name, value in changes.items():
        setattr(tag, field_name, value)
    session.add(tag)
    _flush_or_name_conflict(session, ResourceErrorCode.TAG_NAME_CONFLICT)
    return tag


def create_validated_category(session: Session, category: Category) -> Category:
    """检查名称以及树结构后创建分类。"""

    _ensure_unique_name(
        session,
        Category,
        category.name,
        current_id=None,
        code=ResourceErrorCode.CATEGORY_NAME_CONFLICT,
    )
    try:
        return create_category(session, category)
    except IntegrityError as error:
        raise ResourceError(
            ResourceErrorCode.CATEGORY_NAME_CONFLICT,
            "名称已被使用",
        ) from error


def update_validated_category(
    session: Session,
    category: Category,
    **changes: object,
) -> Category:
    """检查名称以及树结构后更新分类。"""

    if "name" in changes:
        _ensure_unique_name(
            session,
            Category,
            str(changes["name"]),
            current_id=category.id,
            code=ResourceErrorCode.CATEGORY_NAME_CONFLICT,
        )
    try:
        return update_category(session, category, **changes)
    except IntegrityError as error:
        raise ResourceError(
            ResourceErrorCode.CATEGORY_NAME_CONFLICT,
            "名称已被使用",
        ) from error


def delete_account(session: Session, account: Account) -> None:
    """仅删除未被任何历史交易引用的账户。"""

    reference = session.exec(
        select(Transaction.id).where(
            or_(
                Transaction.src_account_id == account.id,
                Transaction.dest_account_id == account.id,
            )
        )
    ).first()
    if reference is not None:
        raise ResourceError(ResourceErrorCode.ACCOUNT_IN_USE, "账户已被交易引用")
    session.delete(account)
    session.flush()


def delete_category(session: Session, category: Category) -> None:
    """仅删除没有子分类且未被历史交易引用的分类。"""

    has_child = session.exec(
        select(Category.id).where(Category.parent_category_id == category.id)
    ).first()
    has_transaction = session.exec(
        select(Transaction.id).where(Transaction.category == category.id)
    ).first()
    if has_child is not None or has_transaction is not None:
        raise ResourceError(ResourceErrorCode.CATEGORY_IN_USE, "分类仍被引用")
    session.delete(category)
    session.flush()


def delete_tag(session: Session, tag: Tag) -> None:
    """仅删除未与任何历史交易关联的标签。"""

    reference = session.exec(
        select(TransactionTag.transaction_id).where(TransactionTag.tag_id == tag.id)
    ).first()
    if reference is not None:
        raise ResourceError(ResourceErrorCode.TAG_IN_USE, "标签已被交易引用")
    session.delete(tag)
    session.flush()


def list_transactions(
    session: Session,
    *,
    include_voided: bool = False,
) -> list[Transaction]:
    """一次性预加载交易响应需要的全部有界关系。"""

    statement = (
        select(Transaction)
        .options(
            joinedload(Transaction.source_account),
            joinedload(Transaction.destination_account),
            joinedload(Transaction.category_record),
            joinedload(Transaction.refund_of_transaction),
            selectinload(Transaction.tags),
        )
        .order_by(Transaction.occurred_at.desc(), Transaction.created_at.desc())
    )
    if not include_voided:
        statement = statement.where(Transaction.is_void.is_(False))
    return list(session.exec(statement).unique())


def category_descendant_ids(session: Session, category_id: str) -> set[str]:
    """返回分类自身及当前子树的 ID，遍历有环数据时也能终止。"""

    children: dict[str, list[str]] = {}
    for item in session.execute(select(Category.id, Category.parent_category_id)):
        children.setdefault(item[1] or "", []).append(item[0])
    result = {category_id}
    pending = [category_id]
    while pending:
        parent = pending.pop()
        for child in children.get(parent, []):
            if child not in result:
                result.add(child)
                pending.append(child)
    return result


def _literal_contains(column: object, value: str):
    """构造不把 ``%`` 和 ``_`` 当作通配符的 SQLite 子串条件。"""

    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return column.like(f"%{escaped}%", escape="\\")  # type: ignore[union-attr]


def transaction_statement(
    session: Session,
    *,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    transaction_type: TransactionType | None = None,
    account_id: str | None = None,
    source_account_id: str | None = None,
    destination_account_id: str | None = None,
    category_id: str | None = None,
    include_descendants: bool = False,
    tag_id: str | None = None,
    query: str | None = None,
    status: Literal["active", "voided", "all"] = "active",
    refund_of_transaction_id: str | None = None,
):
    """构造交易列表和消费下钻共用的数据库过滤语句。"""

    statement = select(Transaction)
    conditions = []
    if start_at is not None:
        conditions.append(Transaction.occurred_at >= start_at)
    if end_at is not None:
        conditions.append(Transaction.occurred_at < end_at)
    if transaction_type is not None:
        conditions.append(Transaction.type == transaction_type)
    if account_id is not None:
        conditions.append(
            or_(Transaction.src_account_id == account_id, Transaction.dest_account_id == account_id)
        )
    if source_account_id is not None:
        conditions.append(Transaction.src_account_id == source_account_id)
    if destination_account_id is not None:
        conditions.append(Transaction.dest_account_id == destination_account_id)
    if category_id is not None:
        category_ids = {category_id}
        if include_descendants:
            category_ids = category_descendant_ids(session, category_id)
        conditions.append(Transaction.category.in_(category_ids))
    if tag_id is not None:
        conditions.append(
            select(TransactionTag.transaction_id)
            .where(
                TransactionTag.transaction_id == Transaction.id,
                TransactionTag.tag_id == tag_id,
            )
            .exists()
        )
    if query:
        conditions.append(_literal_contains(Transaction.description, query))
    if status == "active":
        conditions.append(Transaction.is_void.is_(False))
    elif status == "voided":
        conditions.append(Transaction.is_void.is_(True))
    if refund_of_transaction_id is not None:
        conditions.append(Transaction.refund_of_transaction_id == refund_of_transaction_id)
    return statement.where(and_(*conditions)) if conditions else statement


def list_transactions_page(
    session: Session,
    *,
    page: int = 1,
    page_size: int = 20,
    sort_by: Literal["occurredAt", "amount"] = "occurredAt",
    sort_order: Literal["asc", "desc"] = "desc",
    **filters: object,
) -> tuple[list[Transaction], int]:
    """在数据库中完成交易计数、稳定排序和分页。"""

    statement = transaction_statement(session, **filters)  # type: ignore[arg-type]
    total = int(session.exec(select(func.count()).select_from(statement.subquery())).one())
    primary = Transaction.occurred_at if sort_by == "occurredAt" else Transaction.amount_minor
    ordering = primary.asc() if sort_order == "asc" else primary.desc()
    statement = statement.options(
        joinedload(Transaction.source_account),
        joinedload(Transaction.destination_account),
        joinedload(Transaction.category_record),
        joinedload(Transaction.refund_of_transaction),
        selectinload(Transaction.tags),
    ).order_by(
        ordering,
        Transaction.occurred_at.asc() if sort_order == "asc" else Transaction.occurred_at.desc(),
        Transaction.created_at.asc() if sort_order == "asc" else Transaction.created_at.desc(),
        Transaction.id.asc() if sort_order == "asc" else Transaction.id.desc(),
    ).offset((page - 1) * page_size).limit(page_size)
    return list(session.exec(statement).unique()), total


def get_transaction(session: Session, transaction_id: str) -> Transaction | None:
    """按 ID 读取并预加载一个交易的有界关系。"""

    statement = (
        select(Transaction)
        .where(Transaction.id == transaction_id)
        .options(
            joinedload(Transaction.source_account),
            joinedload(Transaction.destination_account),
            joinedload(Transaction.category_record),
            joinedload(Transaction.refund_of_transaction),
            selectinload(Transaction.tags),
        )
    )
    return session.exec(statement).unique().one_or_none()


def refund_summary(session: Session, transaction_id: str) -> tuple[Transaction | None, int, int]:
    """读取原交易及有效退款总额和笔数，不加载退款明细。"""

    original = session.get(Transaction, transaction_id)
    if original is None:
        return None, 0, 0
    result = session.exec(
        select(
            func.coalesce(func.sum(Transaction.amount_minor), 0),
            func.count(Transaction.id),
        ).where(
            Transaction.refund_of_transaction_id == transaction_id,
            Transaction.is_void.is_(False),
        )
    ).one()
    return original, int(result[0] or 0), int(result[1] or 0)


__all__ = (
    "CategoryHierarchyError",
    "ResourceError",
    "ResourceErrorCode",
    "category_descendant_ids",
    "create_account",
    "create_tag",
    "create_validated_category",
    "delete_account",
    "delete_category",
    "delete_tag",
    "get_transaction",
    "list_transactions",
    "list_transactions_page",
    "refund_summary",
    "transaction_statement",
    "update_account",
    "update_tag",
    "update_validated_category",
)
