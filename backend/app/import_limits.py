"""在 multipart 解析前限制上传体，支持无 Content-Length 的流。"""

from tempfile import SpooledTemporaryFile

from starlette.concurrency import run_in_threadpool

from app.api.errors import ApiError, error_response
from app.import_parser import MAX_FILE_BYTES


class ImportBodyLimitMiddleware:
    def __init__(self, app, path: str):
        self.app = app
        self.path = path

    async def __call__(self, scope, receive, send):
        if (
            scope["type"] != "http"
            or scope["method"] != "POST"
            or scope["path"].rstrip("/") != self.path
        ):
            return await self.app(scope, receive, send)
        maximum = MAX_FILE_BYTES + 64 * 1024
        length = dict(scope.get("headers", [])).get(b"content-length", b"")

        async def reject():
            await error_response(
                ApiError(
                    413, "import_file_limit", "导入请求体超过 10 MiB 文件及表单限制"
                )
            )(scope, receive, send)

        if length.isdigit() and int(length) > maximum:
            return await reject()
        # 有界临时流不长期保存；异常和客户端断开均关闭并删除临时文件。
        with SpooledTemporaryFile(max_size=1024 * 1024) as body:
            size = 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                chunk = message.get("body", b"")
                size += len(chunk)
                if size > maximum:
                    return await reject()
                await run_in_threadpool(body.write, chunk)
                if not message.get("more_body", False):
                    break
            body.seek(0)
            consumed = False

            async def bounded_receive():
                nonlocal consumed
                if consumed:
                    return await receive()
                chunk = await run_in_threadpool(body.read, 64 * 1024)
                consumed = body.tell() >= size
                return {
                    "type": "http.request",
                    "body": chunk,
                    "more_body": not consumed,
                }

            return await self.app(scope, bounded_receive, send)
