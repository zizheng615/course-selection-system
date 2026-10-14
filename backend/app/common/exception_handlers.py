"""全局异常处理。

对标参考项目的 `GlobalExceptionHandler`（`@RestControllerAdvice`）。

**所有响应的 HTTP 状态码都是 200**，业务成败由响应体的 `code` 表达。
例外是静态资源与未匹配到的非 `/api` 路径 —— 那些仍走正常的 HTTP 语义，
否则浏览器的 404 会变成「返回 200 的空 HTML」，更难排查。
"""

from __future__ import annotations

import logging
import sqlite3

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .errors import BusinessException, ErrorCode
from .result import error

logger = logging.getLogger("app.error")


def _json(code: int, message: str | None = None) -> JSONResponse:
    # HTTP 200 + 业务错误码，与参考项目一致
    return JSONResponse(status_code=200, content=error(code, message))


def _translate_integrity_error(exc: sqlite3.IntegrityError) -> tuple[int, str]:
    """把 SQLite 的约束报错翻译成业务错误码。

    这是「数据库约束是最后一道防线」的兑现代价：Service 层已经做过业务校验，
    这里兜住并发下才可能撞上的唯一键/外键/CHECK 冲突。
    """
    text = str(exc)
    if "UNIQUE constraint failed" in text:
        if "enrollment.student_id" in text or "enrollment.course_id" in text:
            return ErrorCode.ALREADY_SELECTED, "已选过该课程，请勿重复选课"
        return ErrorCode.DUPLICATE_KEY, "数据已存在，请勿重复提交"
    if "FOREIGN KEY constraint failed" in text:
        return ErrorCode.COURSE_DELETE_FORBIDDEN, "该记录已被其它数据引用，无法删除"
    if "CHECK constraint failed" in text:
        if "chk_capacity" in text:
            return ErrorCode.PARAM_ERROR, "容量不足，操作被拒绝"
        if "chk_score" in text:
            return ErrorCode.PARAM_ERROR, "成绩必须在 0 到 100 之间"
        return ErrorCode.PARAM_ERROR, "数据不满足约束条件"
    if "NOT NULL constraint failed" in text:
        return ErrorCode.PARAM_ERROR, "必填字段不能为空"
    return ErrorCode.SYSTEM_ERROR, "数据写入失败"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessException)
    async def _business(_: Request, exc: BusinessException) -> JSONResponse:
        logger.info("业务异常 code=%s message=%s", exc.code, exc.message)
        return _json(exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        loc = [str(p) for p in first.get("loc", []) if p not in ("body", "query", "path")]
        field = ".".join(loc) or "参数"
        return _json(ErrorCode.PARAM_ERROR, f"{field} 不合法：{first.get('msg', '校验未通过')}")

    @app.exception_handler(sqlite3.IntegrityError)
    async def _integrity(_: Request, exc: sqlite3.IntegrityError) -> JSONResponse:
        code, message = _translate_integrity_error(exc)
        logger.warning("数据库约束冲突：%s -> %s", exc, code)
        return _json(code, message)

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        # 只有 /api 下的 404/405 才转成统一响应体；静态资源保持原样
        if request.url.path.startswith("/api"):
            if exc.status_code == 404:
                return _json(ErrorCode.NOT_FOUND, "接口不存在")
            if exc.status_code == 405:
                return _json(ErrorCode.PARAM_ERROR, "请求方法不被支持")
            if exc.status_code == 401:
                return _json(ErrorCode.TOKEN_INVALID)
            if exc.status_code == 403:
                return _json(ErrorCode.NO_PERMISSION)
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.status_code, "message": str(exc.detail), "data": None},
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("未捕获异常：%s", exc)
        return _json(ErrorCode.SYSTEM_ERROR)
