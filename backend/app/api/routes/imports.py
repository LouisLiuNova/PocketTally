"""受保护的账单导入 API。"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Path, Query, Response, UploadFile
from sqlalchemy.exc import IntegrityError, OperationalError

from app.api.errors import NOT_FOUND_CONFLICT_RESPONSES, ApiError, ErrorResponse
from app.dependencies import SessionDep
from app.import_parser import MAX_FILE_BYTES, ParseError, parse_bill
from app.imports import (
    commit_batch,
    create_batch,
    delete_batch,
    history,
    patch_batch,
    read_batch,
    require_batch,
)
from app.schemas.imports import (
    ImportBatchRead,
    ImportCommit,
    ImportHistory,
    ImportPatch,
    ImportStatus,
)

router = APIRouter(prefix="/imports", tags=["imports"])
BatchId = Annotated[UUID, Path(alias="batchId")]
RESPONSES = {
    **NOT_FOUND_CONFLICT_RESPONSES,
    413: {"model": ErrorResponse, "description": "文件或请求体超过限制。"},
}


def write_lock(session: SessionDep):
    """先拿写锁再读取草稿，串行化并发修正和提交。"""
    try:
        session.connection().exec_driver_sql("BEGIN IMMEDIATE")
    except OperationalError as error:
        raise ApiError(409, "import_busy", "账本正在写入，请稍后重试") from error


@router.post(
    "",
    response_model=ImportBatchRead,
    status_code=201,
    responses=RESPONSES,
    operation_id="createImport",
)
def upload_import(session: SessionDep, file: Annotated[UploadFile, File()]):
    try:
        data = file.file.read(MAX_FILE_BYTES + 1)
        parsed = parse_bill(data, file.filename or "")
    except ParseError as error:
        raise ApiError(
            413 if error.code in {"import_file_limit", "import_row_limit"} else 422,
            error.code,
            str(error),
        ) from error
    finally:
        file.file.close()
    write_lock(session)
    return read_batch(session, create_batch(session, parsed, file.filename or "", data))


@router.get(
    "", response_model=ImportHistory, responses=RESPONSES, operation_id="listImports"
)
def list_imports(
    session: SessionDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
):
    return history(session, page, page_size)


@router.get(
    "/{batchId}",
    response_model=ImportBatchRead,
    responses=RESPONSES,
    operation_id="getImport",
)
def get_import(
    batch_id: BatchId,
    session: SessionDep,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100, alias="pageSize"),
    status: ImportStatus | None = Query(None),
):
    return read_batch(
        session, require_batch(session, str(batch_id)), page, page_size, status
    )


@router.patch(
    "/{batchId}",
    response_model=ImportBatchRead,
    responses=RESPONSES,
    operation_id="updateImport",
)
def update_import(batch_id: BatchId, payload: ImportPatch, session: SessionDep):
    write_lock(session)
    batch = require_batch(session, str(batch_id))
    patch_batch(session, batch, payload)
    return read_batch(session, batch)


@router.post(
    "/{batchId}/commit",
    response_model=ImportBatchRead,
    responses=RESPONSES,
    operation_id="commitImport",
)
def commit_import(batch_id: BatchId, payload: ImportCommit, session: SessionDep):
    write_lock(session)
    batch = require_batch(session, str(batch_id))
    try:
        commit_batch(session, batch, payload.version)
    except IntegrityError as error:
        raise ApiError(409, "import_duplicate", "来源记录已入账，请重新预览") from error
    return read_batch(session, batch)


@router.delete(
    "/{batchId}", status_code=204, responses=RESPONSES, operation_id="deleteImport"
)
def remove_import(
    batch_id: BatchId, session: SessionDep, version: int = Query(..., gt=0)
):
    write_lock(session)
    delete_batch(session, require_batch(session, str(batch_id)), version)
    return Response(status_code=204)
