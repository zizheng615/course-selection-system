"""账号仓储（sys_user）。对标参考项目的 `SysUserRepository`。

**SQLite 方言适配**：MySQL 的 `ORDER BY FIELD(u.role,'ADMIN','TEACHER','STUDENT')`
用来按角色优先级排序。SQLite 没有 `FIELD()`，展开成等价的 `CASE WHEN`。
"""

from __future__ import annotations

import sqlite3
from typing import Any

_ALIASED_COLUMNS = """u.id,
       u.username,
       u.role,
       u.real_name,
       u.status,
       u.created_at,
       s.student_no,
       s.major,
       t.teacher_no,
       t.dept"""

#: FIELD(u.role,'ADMIN','TEACHER','STUDENT') 的 SQLite 等价写法
_ROLE_ORDER = """CASE u.role
                      WHEN 'ADMIN'   THEN 1
                      WHEN 'TEACHER' THEN 2
                      WHEN 'STUDENT' THEN 3
                      ELSE 4
                    END"""

_WHERE = """(:keyword = '' OR u.username  LIKE '%' || :keyword || '%'
                         OR u.real_name LIKE '%' || :keyword || '%')
       AND (:role = '' OR u.role = :role)"""


def find_by_id(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM sys_user WHERE id = ?", (user_id,)).fetchone()


def find_by_username(conn: sqlite3.Connection, username: str) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM sys_user WHERE username = ?", (username,)).fetchone()


def exists_by_username(conn: sqlite3.Connection, username: str) -> bool:
    return find_by_username(conn, username) is not None


def search(
    conn: sqlite3.Connection, *, keyword: str = "", role: str = "", page: int = 1, size: int = 10
) -> tuple[list[sqlite3.Row], int]:
    """账号分页列表。

    用 LEFT JOIN 而非 INNER JOIN：管理员账号在 student / teacher 两张业务表里
    都没有记录，用 INNER JOIN 会把管理员从列表里漏掉。
    """
    params = {"keyword": keyword, "role": role}
    total = int(conn.execute(f"SELECT COUNT(*) FROM sys_user u WHERE {_WHERE}", params).fetchone()[0])
    rows = conn.execute(
        f"""SELECT {_ALIASED_COLUMNS}
              FROM sys_user u
              LEFT JOIN student s ON s.user_id = u.id
              LEFT JOIN teacher t ON t.user_id = u.id
             WHERE {_WHERE}
             ORDER BY {_ROLE_ORDER}, u.id
             LIMIT :size OFFSET :offset""",
        {**params, "size": size, "offset": (page - 1) * size},
    ).fetchall()
    return rows, total


def count_all(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM sys_user").fetchone()[0])


def insert(conn: sqlite3.Connection, data: dict[str, Any]) -> int:
    cur = conn.execute(
        """INSERT INTO sys_user (username, password_hash, role, real_name, status)
           VALUES (:username, :password_hash, :role, :real_name, :status)""",
        data,
    )
    return int(cur.lastrowid)


def update_credentials(conn: sqlite3.Connection, user_id: int, username: str, password_hash: str | None) -> int:
    """改登录账号 / 重置密码。`password_hash` 为 None 表示只改账号，不动密码。"""
    if password_hash is None:
        return conn.execute(
            "UPDATE sys_user SET username = ? WHERE id = ?", (username, user_id)
        ).rowcount
    return conn.execute(
        "UPDATE sys_user SET username = ?, password_hash = ? WHERE id = ?",
        (username, password_hash, user_id),
    ).rowcount


def update_real_name(conn: sqlite3.Connection, user_id: int, real_name: str) -> int:
    """改学生/教师姓名时同步 sys_user.real_name，避免两处姓名不一致。"""
    return conn.execute(
        "UPDATE sys_user SET real_name = ? WHERE id = ?", (real_name, user_id)
    ).rowcount


def update_status(conn: sqlite3.Connection, user_id: int, status: int) -> int:
    return conn.execute("UPDATE sys_user SET status = ? WHERE id = ?", (status, user_id)).rowcount


def delete(conn: sqlite3.Connection, user_id: int) -> int:
    return conn.execute("DELETE FROM sys_user WHERE id = ?", (user_id,)).rowcount
