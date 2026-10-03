"""持久化草稿、预览、修正及原子提交业务服务。"""

from collections import Counter
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path

from sqlalchemy import delete, exists, func
from sqlmodel import Session, select

from app.api.errors import ApiError
from app.import_models import ImportAccountMapping, ImportBatch, ImportRow, ImportSource
from app.import_parser import ParsedBill
from app.ledger import LedgerError, post_transactions
from app.models import Account, Category, Transaction, TransactionType
from app.schemas.imports import (
    ImportBatchRead,
    ImportHistory,
    ImportPatch,
    ImportRowRead,
    ImportSummary,
)
from app.time_utils import SHANGHAI


def require_batch(session: Session, batch_id: str) -> ImportBatch:
    batch = session.get(ImportBatch, batch_id)
    if batch is None:
        raise ApiError(404, "import_not_found", "导入批次不存在")
    return batch


def create_batch(
    session: Session, parsed: ParsedBill, filename: str, data: bytes
) -> ImportBatch:
    batch = ImportBatch(
        provider=parsed.provider,
        filename=Path(filename).name[:255],
        sha256=sha256(data).hexdigest(),
        summary={**parsed.summary, "rememberMappings": {}},
    )
    session.add(batch)
    session.flush()
    mappings = {
        m.payment_key: m.account_id
        for m in session.exec(
            select(ImportAccountMapping).where(
                ImportAccountMapping.provider == parsed.provider
            )
        )
    }
    accounts = list(session.exec(select(Account)))
    occupied = {
        s.source_id
        for s in session.exec(
            select(ImportSource).where(
                ImportSource.provider == parsed.provider,
                ImportSource.source_id.in_({r.source_id for r in parsed.rows}),
            )
        )
    }
    for item in parsed.rows:
        suggested = mappings.get(item.payment_key)
        if not suggested:
            import re

            tail = re.search(r"[（(](\d{4})[）)]", item.payment_key)
            matches = [
                a
                for a in accounts
                if (
                    tail
                    and a.card_number
                    and a.card_number.replace(" ", "").endswith(tail[1])
                )
                or a.name == item.payment_key
            ]
            if len(matches) == 1:
                suggested = matches[0].id
        session.add(
            ImportRow(
                batch_id=batch.id,
                **vars(item),
                included=item.state == "candidate" and item.source_id not in occupied,
                account_id=suggested,
            )
        )
    session.flush()
    return batch


def row_context(session: Session, batch: ImportBatch, rows: list[ImportRow]):
    accounts = {a.id: a for a in session.exec(select(Account))}
    categories = {c.id: c for c in session.exec(select(Category))}
    ids = {r.source_id for r in rows if r.source_id}
    sources = {
        s.source_id: s
        for s in session.exec(
            select(ImportSource).where(
                ImportSource.provider == batch.provider, ImportSource.source_id.in_(ids)
            )
        )
    }
    return accounts, categories, sources


def row_status(row: ImportRow, context):
    accounts, categories, sources = context
    if row.transaction_id:
        return "imported", None
    if row.state != "candidate":
        return row.state, row.reason
    if row.source_id in sources:
        return "duplicate", "来源单号已入账"
    if not row.included:
        return "skipped", "用户选择跳过"
    if row.account_id not in accounts:
        return "needs_account", "请选择有效账户"
    category = categories.get(row.category_id)
    if category is None or category.purpose.value != row.transaction_type:
        return "needs_category", "请选择对应用途的分类"
    return "ready", None


def read_batch(
    session: Session, batch: ImportBatch, page=1, page_size=50, status_filter=None
) -> ImportBatchRead:
    rows = list(
        session.exec(
            select(ImportRow)
            .where(ImportRow.batch_id == batch.id)
            .order_by(ImportRow.row_number)
        )
    )
    context = row_context(session, batch, rows)
    statuses = {r.id: row_status(r, context) for r in rows}
    counts = dict(Counter(statuses[r.id][0] for r in rows))
    selected = [r for r in rows if r.included and r.state == "candidate"]
    selected_ids = {r.id for r in selected}
    summary = ImportSummary(
        input_rows=len(rows),
        counts=counts,
        selected_count=len(selected),
        unresolved_count=sum(
            statuses[r.id][0] in {"needs_account", "needs_category", "duplicate"}
            for r in selected
        ),
        income_minor=sum(
            r.amount_minor for r in selected if r.transaction_type == "income"
        ),
        expense_minor=sum(
            r.amount_minor for r in selected if r.transaction_type == "expense"
        ),
        excluded_minor=sum(r.amount_minor for r in rows if r.id not in selected_ids),
        source={k: v for k, v in batch.summary.items() if k != "rememberMappings"},
    )
    filtered = [
        r for r in rows if not status_filter or statuses[r.id][0] == status_filter
    ]
    items = []
    for row in filtered[(page - 1) * page_size : page * page_size]:
        state, reason = statuses[row.id]
        source = context[2].get(row.source_id)
        similar = []
        if state in {"ready", "needs_category"} and row.occurred_at and row.account_id:
            local = (
                row.occurred_at.replace(tzinfo=UTC)
                .astimezone(SHANGHAI)
                .replace(hour=0, minute=0, second=0, microsecond=0)
            )
            start = local.astimezone(UTC).replace(tzinfo=None)
            account_field = (
                Transaction.dest_account_id
                if row.transaction_type == "income"
                else Transaction.src_account_id
            )
            similar = list(
                session.exec(
                    select(Transaction.id)
                    .where(
                        Transaction.type == row.transaction_type,
                        Transaction.amount_minor == row.amount_minor,
                        account_field == row.account_id,
                        Transaction.is_void.is_(False),
                        Transaction.occurred_at >= start,
                        Transaction.occurred_at < start + timedelta(days=1),
                        ~exists().where(ImportSource.transaction_id == Transaction.id),
                    )
                    .limit(3)
                )
            )
        items.append(
            ImportRowRead(
                id=row.id,
                row_number=row.row_number,
                source_id=row.source_id,
                status=state,
                reason=reason,
                included=row.included,
                editable=row.state == "candidate" and batch.status == "draft",
                type=row.transaction_type,
                amount_minor=row.amount_minor,
                occurred_at=row.occurred_at,
                description=row.description,
                payment_key=row.payment_key,
                account_id=row.account_id,
                category_id=row.category_id,
                transaction_id=row.transaction_id
                or (source.transaction_id if source else None),
                duplicate_batch_id=source.batch_id if source else None,
                original=row.original,
                similar_transaction_ids=similar,
            )
        )
    return ImportBatchRead(
        **{
            name: getattr(batch, name)
            for name in (
                "id",
                "provider",
                "filename",
                "sha256",
                "parser_version",
                "status",
                "version",
                "created_at",
                "updated_at",
                "committed_at",
            )
        },
        summary=summary,
        payment_keys=sorted({r.payment_key for r in rows if r.state == "candidate"}),
        items=items,
        total=len(filtered),
        page=page,
        page_size=page_size,
    )


def history(session: Session, page: int, page_size: int) -> ImportHistory:
    total = session.exec(select(func.count()).select_from(ImportBatch)).one()
    batches = session.exec(
        select(ImportBatch)
        .order_by(ImportBatch.created_at.desc(), ImportBatch.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return ImportHistory(
        items=[
            {
                **{
                    name: getattr(b, name)
                    for name in (
                        "id",
                        "provider",
                        "filename",
                        "status",
                        "version",
                        "created_at",
                        "committed_at",
                    )
                },
                "input_rows": b.summary["inputRows"],
            }
            for b in batches
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


def check_version(batch: ImportBatch, version: int):
    if batch.version != version:
        raise ApiError(409, "import_version_conflict", "草稿已更新，请重新载入后确认")
    if batch.status != "draft":
        raise ApiError(409, "import_already_committed", "已提交批次不能修改或删除")


def patch_batch(session: Session, batch: ImportBatch, payload: ImportPatch):
    check_version(batch, payload.version)
    rows = list(session.exec(select(ImportRow).where(ImportRow.batch_id == batch.id)))
    mapping = dict(batch.summary.get("rememberMappings", {}))
    for change in payload.changes:
        ids = {str(i) for i in change.row_ids}
        selected = [
            r
            for r in rows
            if (r.id in ids if ids else r.payment_key == change.payment_key)
        ]
        if change.match_type is not None:
            selected = [
                r
                for r in selected
                if r.transaction_type == change.match_type and r.state == "candidate"
            ]
        if not selected or (ids and len(selected) != len(ids)):
            raise ApiError(422, "import_invalid_selection", "选择中包含不存在的候选行")
        changes = change.model_dump(
            exclude_unset=True,
            exclude={"row_ids", "payment_key", "remember_mapping", "match_type"},
        )
        for name, model in [("account_id", Account), ("category_id", Category)]:
            if changes.get(name) is not None:
                changes[name] = str(changes[name])
                if session.get(model, changes[name]) is None:
                    raise ApiError(
                        409, "import_resource_missing", "选择的账户或分类已不存在"
                    )
        for row in selected:
            if row.state != "candidate":
                if len(selected) == 1 or ids:
                    raise ApiError(
                        409,
                        "import_row_locked",
                        "退款、跳过或不支持的来源记录不能改为普通交易",
                    )
                continue
            for name, value in changes.items():
                target = "transaction_type" if name == "type" else name
                if name == "occurred_at":
                    value = value.astimezone(UTC).replace(tzinfo=None)
                setattr(row, target, value)
        if change.remember_mapping:
            mapping[change.payment_key] = str(change.account_id)
    batch.summary = {**batch.summary, "rememberMappings": mapping}
    batch.version += 1
    session.flush()


def commit_batch(session: Session, batch: ImportBatch, version: int):
    if batch.status == "committed":
        return
    check_version(batch, version)
    rows = list(
        session.exec(
            select(ImportRow)
            .where(ImportRow.batch_id == batch.id)
            .order_by(ImportRow.row_number)
        )
    )
    context = row_context(session, batch, rows)
    included = [r for r in rows if r.included and r.state == "candidate"]
    errors = [
        {"rowId": r.id, "rowNumber": r.row_number, "status": row_status(r, context)[0]}
        for r in included
        if row_status(r, context)[0] != "ready"
    ]
    if errors:
        raise ApiError(
            409,
            "import_rows_unresolved",
            "部分记录已重复或账户、分类未解决，请重新预览",
            details=errors[:100],
        )
    if not included:
        raise ApiError(409, "import_empty_selection", "没有可提交的记录")
    transactions = [
        Transaction(
            type=TransactionType(r.transaction_type),
            amount_minor=r.amount_minor,
            occurred_at=r.occurred_at,
            description=r.description,
            src_account_id=r.account_id if r.transaction_type == "expense" else None,
            dest_account_id=r.account_id if r.transaction_type == "income" else None,
            category=r.category_id,
        )
        for r in included
    ]
    try:
        post_transactions(session, transactions)
    except LedgerError as error:
        insufficient = error.code.value == "insufficient_balance"
        raise ApiError(
            409,
            "import_insufficient_balance" if insufficient else error.code.value,
            "借记账户余额不足，请先通过调账建立正确余额基线"
            if insufficient
            else str(error),
            details={"accountIds": sorted({r.account_id for r in included})},
        ) from error
    for row, transaction in zip(included, transactions, strict=True):
        row.transaction_id = transaction.id
        session.add(
            ImportSource(
                provider=batch.provider,
                source_id=row.source_id,
                batch_id=batch.id,
                row_id=row.id,
                transaction_id=transaction.id,
            )
        )
    for payment_key, account_id in batch.summary.get("rememberMappings", {}).items():
        if session.get(Account, account_id) is None:
            raise ApiError(
                409, "import_resource_missing", "记住的映射账户已不存在，请修正草稿"
            )
        mapping = session.exec(
            select(ImportAccountMapping).where(
                ImportAccountMapping.provider == batch.provider,
                ImportAccountMapping.payment_key == payment_key,
            )
        ).first()
        if mapping:
            mapping.account_id = account_id
        else:
            session.add(
                ImportAccountMapping(
                    provider=batch.provider,
                    payment_key=payment_key,
                    account_id=account_id,
                )
            )
    batch.status = "committed"
    batch.version += 1
    batch.committed_at = datetime.now(UTC).replace(tzinfo=None)
    session.flush()


def delete_batch(session: Session, batch: ImportBatch, version: int):
    check_version(batch, version)
    session.execute(delete(ImportRow).where(ImportRow.batch_id == batch.id))
    session.delete(batch)
    session.flush()
