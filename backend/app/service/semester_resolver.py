"""学期参数归一化。对标参考项目的 `service/SemesterResolver`。

前端下拉框可能在数据还没加载完时就把 semester 传成空串，
此时按「库里最新的学期」兜底，而不是让查询返回空结果。
"""

from __future__ import annotations

import sqlite3

from ..config import settings


def resolve(conn: sqlite3.Connection, semester: str | None) -> str:
    if semester is not None and semester.strip():
        return semester.strip()
    row = conn.execute("SELECT DISTINCT semester FROM course ORDER BY semester DESC LIMIT 1").fetchone()
    if row is not None and row[0]:
        return str(row[0])
    return settings.default_semester
