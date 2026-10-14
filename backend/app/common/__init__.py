"""通用基础设施：统一响应体、错误码、异常处理、类型收敛。"""

from .convert import SQL_WEEKDAY_NAME, WEEKDAY_NAMES, to_bool, to_float, to_int, to_str, weekday_name
from .errors import DEFAULT_MESSAGES, BusinessException, ErrorCode, fail
from .exception_handlers import register_exception_handlers
from .result import PageResult, error, normalize_page, ok, page

__all__ = [
    "BusinessException",
    "ErrorCode",
    "DEFAULT_MESSAGES",
    "fail",
    "ok",
    "error",
    "page",
    "normalize_page",
    "PageResult",
    "register_exception_handlers",
    "to_float",
    "to_int",
    "to_str",
    "to_bool",
    "weekday_name",
    "WEEKDAY_NAMES",
    "SQL_WEEKDAY_NAME",
]
