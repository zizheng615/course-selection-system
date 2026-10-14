"""统一响应体。

与参考项目 `common/Result.java`、`common/PageResult.java` 的 JSON 结构逐字段对齐：

    { "code": 0, "message": "ok", "data": ... }
    { "code": 0, "message": "ok", "data": { "list": [...], "total": 218, "page": 1, "size": 10 } }

关键约定：**HTTP 状态码恒为 200**，业务成败只由 `code` 表达。
这跟参考项目一致 —— Spring 的 `@RestControllerAdvice` 返回 `Result` 时状态码也是 200，
前端 `request.js` 的拦截器据此判断。
"""

from __future__ import annotations

from typing import Any, Generic, Sequence, TypeVar

from .errors import DEFAULT_MESSAGES, ErrorCode

T = TypeVar("T")

#: 分页默认值（对标参考项目 Controller 上的 @RequestParam defaultValue）
DEFAULT_PAGE = 1
DEFAULT_SIZE = 10
MAX_SIZE = 200


def ok(data: Any = None, message: str = "ok") -> dict[str, Any]:
    return {"code": ErrorCode.SUCCESS, "message": message, "data": data}


def error(code: int, message: str | None = None, data: Any = None) -> dict[str, Any]:
    return {
        "code": code,
        "message": message or DEFAULT_MESSAGES.get(code, "操作失败"),
        "data": data,
    }


def page(items: Sequence[Any], total: int, page_no: int, size: int) -> dict[str, Any]:
    """构造 `PageResult` 结构的 `data` 段。"""
    return {"list": list(items), "total": total, "page": page_no, "size": size}


def normalize_page(page_no: Any, size: Any) -> tuple[int, int]:
    """把可能非法/缺省的分页参数收敛到合法范围。"""
    try:
        p = int(page_no)
    except (TypeError, ValueError):
        p = DEFAULT_PAGE
    try:
        s = int(size)
    except (TypeError, ValueError):
        s = DEFAULT_SIZE
    if p < 1:
        p = DEFAULT_PAGE
    if s < 1:
        s = DEFAULT_SIZE
    if s > MAX_SIZE:
        s = MAX_SIZE
    return p, s


class PageResult(Generic[T]):
    """仅供测试与类型标注使用的轻量载体。"""

    __slots__ = ("list", "total", "page", "size")

    def __init__(self, items: Sequence[T], total: int, page_no: int, size: int) -> None:
        self.list = list(items)
        self.total = total
        self.page = page_no
        self.size = size

    def to_dict(self) -> dict[str, Any]:
        return {"list": self.list, "total": self.total, "page": self.page, "size": self.size}
