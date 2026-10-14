"""学生仓储。

参考项目这里用 `JpaSpecificationExecutor` 组装动态条件（为了绕开 JPQL 的
`:param IS NULL` 类型推断问题）。SQL 里没有这个包袱，
直接用 `:keyword = ''` 归一化写法，与其它仓储保持一致。
"""

from __future__ import annotations

import sqlite3
from typing import Any

_COLUMNS = "id, user_id, student_no, name, gender, major, grade, phone"

#: 带表别名的列清单。分页查询要 JOIN 时用这个，避免别名与列名混写。
_ALIASED_COLUMNS = """s.id,
       s.user_id,
       s.student_no,
       s.name,
       s.gender,
       s.major,
       s.grade,
       s.phone"""

_WHERE = """(:keyword = '' OR s.student_no LIKE '%' || :keyword || '%'
                         OR s.name       LIKE '%' || :keyword || '%')
       AND (:major = '' OR s.major = :major)"""


def find_by_id(conn: sqlite3.Connection, student_id: int) -> sqlite3.Row | None:
    return conn.execute(f"SELECT {_COLUMNS} FROM student WHERE id = ?", (student_id,)).fetchone()


def find_by_user_id(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return conn.execute(f"SELECT {_COLUMNS} FROM student WHERE user_id = ?", (user_id,)).fetchone()


def find_by_no(conn: sqlite3.Connection, student_no: str) -> sqlite3.Row | None:
    return conn.execute(f"SELECT {_COLUMNS} FROM student WHERE student_no = ?", (student_no,)).fetchone()


def exists_by_no(conn: sqlite3.Connection, student_no: str) -> bool:
    return find_by_no(conn, student_no) is not None


def find_distinct_majors(conn: sqlite3.Connection) -> list[str]:
    return [r[0] for r in conn.execute("SELECT DISTINCT major FROM student ORDER BY major").fetchall()]


def search(
    conn: sqlite3.Connection, *, keyword: str = "", major: str = "", page: int = 1, size: int = 10
) -> tuple[list[sqlite3.Row], int]:
    params = {"keyword": keyword, "major": major}
    total = int(conn.execute(f"SELECT COUNT(*) FROM student s WHERE {_WHERE}", params).fetchone()[0])
    rows = conn.execute(
        f"""SELECT {_ALIASED_COLUMNS}
              FROM student s
             WHERE {_WHERE}
             ORDER BY s.id
             LIMIT :size OFFSET :offset""",
        {**params, "size": size, "offset": (page - 1) * size},
    ).fetchall()
    return rows, total


def count_all(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM student").fetchone()[0])


def insert(conn: sqlite3.Connection, data: dict[str, Any]) -> int:
    cur = conn.execute(
        """INSERT INTO student (user_id, student_no, name, gender, major, grade, phone)
           VALUES (:user_id, :student_no, :name, :gender, :major, :grade, :phone)""",
        data,
    )
    return int(cur.lastrowid)


def update(conn: sqlite3.Connection, student_id: int, data: dict[str, Any]) -> int:
    return conn.execute(
        """UPDATE student
              SET student_no = :student_no, name = :name, gender = :gender,
                  major = :major, grade = :grade, phone = :phone
            WHERE id = :id""",
        {**data, "id": student_id},
    ).rowcount


def delete(conn: sqlite3.Connection, student_id: int) -> int:
    return conn.execute("DELETE FROM student WHERE id = ?", (student_id,)).rowcount
