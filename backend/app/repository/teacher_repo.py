"""教师仓储。"""

from __future__ import annotations

import sqlite3
from typing import Any

_COLUMNS = "id, user_id, teacher_no, name, title, dept"

_ALIASED_COLUMNS = """t.id,
       t.user_id,
       t.teacher_no,
       t.name,
       t.title,
       t.dept"""

_WHERE = """(:keyword = '' OR t.teacher_no LIKE '%' || :keyword || '%'
                         OR t.name       LIKE '%' || :keyword || '%')
       AND (:dept = '' OR t.dept = :dept)"""


def find_by_id(conn: sqlite3.Connection, teacher_id: int) -> sqlite3.Row | None:
    return conn.execute(f"SELECT {_COLUMNS} FROM teacher WHERE id = ?", (teacher_id,)).fetchone()


def find_by_user_id(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return conn.execute(f"SELECT {_COLUMNS} FROM teacher WHERE user_id = ?", (user_id,)).fetchone()


def exists_by_no(conn: sqlite3.Connection, teacher_no: str) -> bool:
    return conn.execute("SELECT 1 FROM teacher WHERE teacher_no = ?", (teacher_no,)).fetchone() is not None


def find_all(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """全部教师，供课程表单的教师下拉框使用。"""
    return conn.execute(f"SELECT {_COLUMNS} FROM teacher ORDER BY id").fetchall()


def search(
    conn: sqlite3.Connection, *, keyword: str = "", dept: str = "", page: int = 1, size: int = 10
) -> tuple[list[sqlite3.Row], int]:
    params = {"keyword": keyword, "dept": dept}
    total = int(conn.execute(f"SELECT COUNT(*) FROM teacher t WHERE {_WHERE}", params).fetchone()[0])
    rows = conn.execute(
        f"""SELECT {_ALIASED_COLUMNS}
              FROM teacher t
             WHERE {_WHERE}
             ORDER BY t.id
             LIMIT :size OFFSET :offset""",
        {**params, "size": size, "offset": (page - 1) * size},
    ).fetchall()
    return rows, total


def insert(conn: sqlite3.Connection, data: dict[str, Any]) -> int:
    cur = conn.execute(
        """INSERT INTO teacher (user_id, teacher_no, name, title, dept)
           VALUES (:user_id, :teacher_no, :name, :title, :dept)""",
        data,
    )
    return int(cur.lastrowid)


def update(conn: sqlite3.Connection, teacher_id: int, data: dict[str, Any]) -> int:
    return conn.execute(
        """UPDATE teacher
              SET teacher_no = :teacher_no, name = :name, title = :title, dept = :dept
            WHERE id = :id""",
        {**data, "id": teacher_id},
    ).rowcount


def delete(conn: sqlite3.Connection, teacher_id: int) -> int:
    return conn.execute("DELETE FROM teacher WHERE id = ?", (teacher_id,)).rowcount
