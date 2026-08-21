"""应用共用的 HTTP 中间件。"""

from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from loguru import logger


def register_middleware(app: FastAPI) -> None:
    """注册请求上下文和访问日志中间件。

    Args:
        app: 接收该中间件的 FastAPI 应用。

    Returns:
        无返回值。
    """

    @app.middleware("http")
    async def request_context(request: Request, call_next) -> Response:
        """附加请求标识，并记录已完成的 HTTP 请求。

        Args:
            request: 传入的 HTTP 请求。
            call_next: 调用下一个中间件或路由的可调用对象。

        Returns:
            下游应用生成的响应。
        """

        request_id = request.headers.get("X-Request-ID") or uuid4().hex
        request.state.request_id = request_id
        started = perf_counter()

        with logger.contextualize(request_id=request_id):
            try:
                response = await call_next(request)
            except Exception:
                logger.exception(
                    "Unhandled request error: {} {}",
                    request.method,
                    request.url.path,
                )
                raise

            elapsed_ms = (perf_counter() - started) * 1000
            response.headers["X-Request-ID"] = request_id
            logger.info(
                "{} {} -> {} ({:.2f} ms)",
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
            )
            return response
