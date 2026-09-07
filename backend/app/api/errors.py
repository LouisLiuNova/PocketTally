"""HTTP API 的稳定错误结构与异常处理。"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import Field

from app.schemas.base import ContractModel


class ErrorResponse(ContractModel):
    """公开接口统一返回的错误模型。"""

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    details: dict[str, Any] | list[Any] | None = None


class ApiError(Exception):
    """可安全返回给客户端的预期 API 错误。"""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | list[Any] | None = None,
    ) -> None:
        """初始化稳定 API 错误。

        Args:
            status_code: HTTP 状态码。
            code: 稳定机器错误码。
            message: 面向客户端的简体中文说明。
            details: 可选的结构化错误详情。
        """

        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def error_response(error: ApiError) -> JSONResponse:
    """将预期 API 错误转换为统一 JSON 响应。"""

    body = ErrorResponse(
        code=error.code,
        message=error.message,
        details=error.details,
    ).model_dump(mode="json", by_alias=True, exclude_none=True)
    return JSONResponse(status_code=error.status_code, content=body)


def register_exception_handlers(application: FastAPI) -> None:
    """为应用注册公开错误处理器。

    Args:
        application: 待配置的 FastAPI 应用。
    """

    @application.exception_handler(ApiError)
    async def handle_api_error(_request: Request, error: ApiError) -> JSONResponse:
        """返回服务层声明的预期错误。"""

        return error_response(error)

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        """将 FastAPI/Pydantic 校验错误统一为公开契约。"""

        details = [
            {
                "location": list(item["loc"]),
                "message": item["msg"],
                "type": item["type"],
            }
            for item in error.errors()
        ]
        return error_response(
            ApiError(
                422,
                "validation_error",
                "请求参数校验失败",
                details=details,
            )
        )

    @application.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request,
        error: Exception,
    ) -> JSONResponse:
        """记录未预期错误，并避免向客户端泄露内部异常文本。"""

        logger.exception(
            "Unhandled API error: {} {}: {!r}",
            request.method,
            request.url.path,
            error,
        )
        return error_response(
            ApiError(500, "internal_error", "服务器内部错误")
        )


ERROR_RESPONSES = {
    404: {"model": ErrorResponse, "description": "资源不存在。"},
    409: {"model": ErrorResponse, "description": "操作与当前数据或业务规则冲突。"},
    422: {"model": ErrorResponse, "description": "请求参数校验失败。"},
    500: {"model": ErrorResponse, "description": "未预期的服务器内部错误。"},
}
VALIDATION_RESPONSES = {
    422: ERROR_RESPONSES[422],
    500: ERROR_RESPONSES[500],
}
NOT_FOUND_RESPONSES = {
    404: ERROR_RESPONSES[404],
    422: ERROR_RESPONSES[422],
    500: ERROR_RESPONSES[500],
}
CONFLICT_RESPONSES = {
    409: ERROR_RESPONSES[409],
    422: ERROR_RESPONSES[422],
    500: ERROR_RESPONSES[500],
}
NOT_FOUND_CONFLICT_RESPONSES = {
    404: ERROR_RESPONSES[404],
    409: ERROR_RESPONSES[409],
    422: ERROR_RESPONSES[422],
    500: ERROR_RESPONSES[500],
}


__all__ = (
    "CONFLICT_RESPONSES",
    "ERROR_RESPONSES",
    "NOT_FOUND_CONFLICT_RESPONSES",
    "NOT_FOUND_RESPONSES",
    "VALIDATION_RESPONSES",
    "ApiError",
    "ErrorResponse",
    "register_exception_handlers",
)
