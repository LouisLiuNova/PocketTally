"""领域路由共用的错误映射。"""

from app.api.errors import ApiError
from app.categories import CategoryHierarchyError, CategoryHierarchyErrorCode
from app.ledger import LedgerError, LedgerErrorCode
from app.resources import ResourceError, ResourceErrorCode

_RESOURCE_STATUS = {
    ResourceErrorCode.ACCOUNT_NOT_FOUND: 404,
    ResourceErrorCode.CATEGORY_NOT_FOUND: 404,
    ResourceErrorCode.TAG_NOT_FOUND: 404,
    ResourceErrorCode.TRANSACTION_NOT_FOUND: 404,
}


def map_resource_error(error: ResourceError) -> ApiError:
    """把基础资源错误映射为 HTTP 404 或 409。"""

    return ApiError(
        _RESOURCE_STATUS.get(error.code, 409),
        error.code,
        str(error),
    )


def map_category_error(error: CategoryHierarchyError) -> ApiError:
    """把分类层级错误映射为约定的 HTTP 状态码。"""

    status_code = (
        404
        if error.code is CategoryHierarchyErrorCode.PARENT_NOT_FOUND
        else 409
    )
    return ApiError(status_code, error.code, str(error))


def map_ledger_error(error: LedgerError) -> ApiError:
    """把账本服务错误映射为约定的 HTTP 状态码。"""

    status_code = {
        LedgerErrorCode.ACCOUNT_NOT_FOUND: 404,
        LedgerErrorCode.CATEGORY_NOT_FOUND: 404,
        LedgerErrorCode.TAG_NOT_FOUND: 404,
        LedgerErrorCode.TRANSACTION_NOT_FOUND: 404,
        LedgerErrorCode.INSUFFICIENT_BALANCE: 409,
        LedgerErrorCode.TRANSACTION_VOIDED: 409,
    }.get(error.code, 422)
    return ApiError(status_code, error.code, str(error))


__all__ = ("map_category_error", "map_ledger_error", "map_resource_error")
