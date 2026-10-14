"""DTO/VO 的公共约定。

**字段命名**：DTO 与 VO 的字段名一律直接写成 camelCase，与前端 JSON 逐字对齐。
按 PEP 8 它们本该是 snake_case，但这里刻意不这么做 —— 用 `alias` 映射会引入
一层「名字写错了也不报错」的间接性，而字段名本身就是对外契约的一部分
（参考项目的 Java 字段名即 JSON 字段名）。宁可让 Python 侧看着别扭一点。

**VO 映射**：`@Query(nativeQuery = true)` 在 Java 侧返回 `Object[]`，由 VO 的
具名工厂方法按下标映射。本项目沿用同样的做法：每个 VO 有一个 `from_row`
类方法，按**下标**取列。用命名而非重载区分不同列集，就是为了在改 SQL 列顺序时
能立刻发现对应关系 —— **改原生查询的 SELECT 列表时，必须同步改这里的下标**。
"""

from __future__ import annotations

import sqlite3
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict


class DTO(BaseModel):
    """所有入参 DTO 的基类。

    `extra="forbid"` 让「前端多传了一个字段」变成显式错误，
    避免拼错字段名时静默使用默认值。
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class VO(BaseModel):
    """所有出参 VO 的基类。

    字段顺序即 JSON 序列化顺序，与参考项目的声明顺序保持一致，
    方便对照 `docs/api-contract.md` 逐字段核对。
    """

    model_config = ConfigDict(from_attributes=True)


def row_value(row: Mapping[str, Any] | sqlite3.Row | tuple, index: int) -> Any:
    """按下标取列，兼容 `sqlite3.Row` 与普通元组。"""
    if isinstance(row, sqlite3.Row):
        return row[index]
    if isinstance(row, tuple):
        return row[index]
    return list(row.values())[index]
