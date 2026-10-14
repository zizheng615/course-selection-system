"""SQLite 连接与事务管理。

对标参考项目里 HikariCP + `@Transactional` 的组合，做法是：

* **连接按线程隔离**（`threading.local`）。FastAPI 的同步路由跑在线程池里，
  每个线程拿到自己的连接，天然避免 SQLite 连接不可跨线程复用的问题。
* **事务边界只在 Service 层**。Repository 只接受 `conn` 参数执行 SQL，
  自己不开关事务 —— 与参考项目「`@Transactional` 只出现在 Service」一致。
* **写事务用 `BEGIN IMMEDIATE`**。SQLite 默认的 deferred 事务是「第一次写才加锁」，
  并发下会先读到旧值再加锁，退化成 SELECT-then-UPDATE 的经典超卖模式。
  IMMEDIATE 在事务开始就取写锁，配合 `busy_timeout` 让并发写串行化，
  这正是参考项目靠 InnoDB 行锁 + 原子 UPDATE 拿到的效果。

注意：`isolation_level=None` 关闭了 Python sqlite3 模块的隐式事务管理，
事务完全由下面这两个上下文管理器显式控制。
"""

from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from typing import Any, Iterable, Iterator, Sequence

from .config import settings

_state = threading.local()

# 期望存在的表与视图，启动时校验（对标参考项目的 ddl-auto=validate）
EXPECTED_TABLES = ("sys_user", "student", "teacher", "course", "course_schedule", "enrollment")
EXPECTED_VIEWS = ("v_course_detail", "v_student_credit")


class SchemaError(RuntimeError):
    """数据库结构缺失或不匹配。"""


def _new_connection() -> sqlite3.Connection:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        str(settings.db_path),
        timeout=10.0,
        isolation_level=None,  # 显式事务，见模块 docstring
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn


def connection() -> sqlite3.Connection:
    """取当前线程的连接（不存在则创建）。"""
    conn = getattr(_state, "conn", None)
    if conn is None:
        conn = _new_connection()
        _state.conn = conn
    return conn


def close_connection() -> None:
    """关闭当前线程的连接。线程结束时调用，避免句柄泄漏。"""
    conn = getattr(_state, "conn", None)
    if conn is not None:
        conn.close()
        _state.conn = None


def in_transaction() -> bool:
    return getattr(_state, "depth", 0) > 0


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    """写事务。嵌套调用时复用外层事务（内层不再 BEGIN/COMMIT）。

    嵌套复用是必要的：管理员代选课 (`adminEnroll`) 会复用学生自助选课
    (`selectCourse`) 的完整校验逻辑，两者都是 Service 层的写操作。
    """
    conn = connection()
    depth = getattr(_state, "depth", 0)

    if depth > 0:
        # 已在事务中：直接复用，由最外层负责提交/回滚
        _state.depth = depth + 1
        try:
            yield conn
        finally:
            _state.depth -= 1
        return

    conn.execute("BEGIN IMMEDIATE")
    _state.depth = 1
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")
    finally:
        _state.depth = 0


@contextmanager
def read_connection() -> Iterator[sqlite3.Connection]:
    """只读查询用的连接（不开显式事务）。"""
    yield connection()


# --------------------------------------------------------------------------
# 查询辅助
# --------------------------------------------------------------------------

def query_all(sql: str, params: Sequence[Any] = ()) -> list[sqlite3.Row]:
    return connection().execute(sql, params).fetchall()


def query_one(sql: str, params: Sequence[Any] = ()) -> sqlite3.Row | None:
    return connection().execute(sql, params).fetchone()


def query_scalar(sql: str, params: Sequence[Any] = (), default: Any = None) -> Any:
    row = query_one(sql, params)
    if row is None:
        return default
    value = row[0]
    return default if value is None else value


def execute(conn: sqlite3.Connection, sql: str, params: Sequence[Any] = ()) -> sqlite3.Cursor:
    return conn.execute(sql, params)


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return None if row is None else {k: row[k] for k in row.keys()}


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
    return [{k: r[k] for k in r.keys()} for r in rows]


def assert_schema() -> None:
    """启动期结构校验：6 张表 + 2 个视图必须齐全。

    对标参考项目的 `ddl-auto=validate`：结构由 `sql/01_schema.sql` 决定，
    应用只做校验，绝不自动建表。
    """
    if not settings.db_path.is_file():
        raise SchemaError(
            f"数据库不存在：{settings.db_path}\n"
            f"请先执行：python scripts/init_db.py"
        )
    rows = query_all("SELECT type, name FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'")
    have_tables = {r["name"] for r in rows if r["type"] == "table"}
    have_views = {r["name"] for r in rows if r["type"] == "view"}

    missing_tables = [t for t in EXPECTED_TABLES if t not in have_tables]
    missing_views = [v for v in EXPECTED_VIEWS if v not in have_views]
    if missing_tables or missing_views:
        raise SchemaError(
            "数据库结构与 sql/01_schema.sql 不一致，"
            f"缺少表 {missing_tables} 视图 {missing_views}。请重新执行：python scripts/init_db.py"
        )
