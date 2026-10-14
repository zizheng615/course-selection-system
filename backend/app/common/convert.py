"""原生查询结果 -> JSON 的类型收敛。

对标参考项目的 `support/SqlUtils`：SQLite 与 MySQL 一样，对同一列可能返回
不同 Python 类型（`NUMERIC` 列存了整数值时会回 int），而前端期望稳定的形状。
所有对外的数字字段都过一遍这里的函数。

**为什么不直接把列声明成 REAL**：那会丢掉「学分 4.0 / 学时 64」的语义差别。
真问题是 SQLite 的动态类型，所以在读出边界统一收敛，而不是在存储上做妥协。
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any


def to_float(value: Any, default: float | None = None) -> float | None:
    """转 float。None 保持 None（成绩未录入必须是 null，不能变 0）。"""
    if value is None:
        return default
    if isinstance(value, float):
        return value
    if isinstance(value, (int, Decimal)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def to_int(value: Any, default: int | None = None) -> int | None:
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def to_str(value: Any, default: str = "") -> str:
    return default if value is None else str(value)


def to_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


#: 星期 -> 中文名。前端课表网格与冲突提示共用。
WEEKDAY_NAMES: dict[int, str] = {
    1: "周一",
    2: "周二",
    3: "周三",
    4: "周四",
    5: "周五",
    6: "周六",
    7: "周日",
}


def weekday_name(weekday: Any) -> str:
    return WEEKDAY_NAMES.get(to_int(weekday) or 0, "未知")


#: SQLite 的 CASE WHEN 版「星期转中文」，与上面的字典必须保持一致。
#: 用在原生 SQL 里（对标 MySQL 的 FIELD()/CASE，见 sql/03_queries.sql 查询 2）。
SQL_WEEKDAY_NAME = """CASE cs.weekday
        WHEN 1 THEN '周一' WHEN 2 THEN '周二' WHEN 3 THEN '周三'
        WHEN 4 THEN '周四' WHEN 5 THEN '周五' WHEN 6 THEN '周六'
        ELSE '周日' END"""
