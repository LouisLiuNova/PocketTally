"""HTTP middleware shared by the application."""

from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from loguru import logger


def register_middleware(app: FastAPI) -> None:
    """Register request context and access logging middleware."""

    @app.middleware("http")
    async def request_context(request: Request, call_next) -> Response:
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
