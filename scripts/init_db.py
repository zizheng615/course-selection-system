"""建库脚本：重建 SQLite 数据库并灌入演示数据。

幂等 —— 每次执行都会删掉旧库文件重新来一遍，因此可以随时把演示数据恢复到
种子状态（跑测试或手测把数据弄脏之后很有用）。

用法：
    python scripts/init_db.py            # 重建
    python scripts/init_db.py --keep     # 保留现有库（仅当库不存在时才建）

对标参考项目的：
    mysql -u root -p < sql/01_schema.sql
    mysql -u root -p course_selection < sql/02_seed_data.sql
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from app.config import settings  # noqa: E402
from app.db import EXPECTED_TABLES, EXPECTED_VIEWS  # noqa: E402

SQL_FILES = ("01_schema.sql", "02_seed_data.sql")


def _remove_db_files(db_path: Path) -> None:
    """删掉主库文件与 WAL/SHM 边车文件。

    只删 WAL 不删主库，或反过来，都会留下不一致的状态。
    """
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(db_path) + suffix)
        if candidate.exists():
            candidate.unlink()


def _run_script(conn: sqlite3.Connection, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    conn.executescript(sql)


def _summary(conn: sqlite3.Connection) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in EXPECTED_TABLES:
        counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    counts["已录成绩"] = conn.execute(
        "SELECT COUNT(*) FROM enrollment WHERE score IS NOT NULL"
    ).fetchone()[0]
    return counts


def _consistency_issues(conn: sqlite3.Connection) -> list[tuple]:
    """容量一致性自检：反范式字段 enrolled_count 必须等于真实选课数。"""
    return conn.execute(
        """
        SELECT c.id, c.name, c.capacity, c.enrolled_count,
               (SELECT COUNT(*) FROM enrollment e
                 WHERE e.course_id = c.id AND e.status = 'SELECTED') AS actual
          FROM course c
         WHERE c.enrolled_count <> (SELECT COUNT(*) FROM enrollment e
                                     WHERE e.course_id = c.id AND e.status = 'SELECTED')
            OR c.enrolled_count > c.capacity
        """
    ).fetchall()


def main() -> int:
    parser = argparse.ArgumentParser(description="重建选课系统 SQLite 数据库")
    parser.add_argument("--keep", action="store_true", help="库已存在时不重建")
    args = parser.parse_args()

    db_path = settings.db_path
    if args.keep and db_path.is_file():
        print(f"[skip] 数据库已存在：{db_path}")
        return 0

    db_path.parent.mkdir(parents=True, exist_ok=True)
    _remove_db_files(db_path)
    print(f"[1/3] 已清理旧库：{db_path}")

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        for name in SQL_FILES:
            script = settings.sql_dir / name
            _run_script(conn, script)
            print(f"[2/3] 已执行 {name}")
        conn.commit()

        counts = _summary(conn)
        print("[3/3] 数据规模：")
        for key, value in counts.items():
            print(f"        {key:<16} {value}")

        issues = _consistency_issues(conn)
        if issues:
            print(f"\n[警告] 容量一致性校验未通过，{len(issues)} 门课程不一致：")
            for row in issues:
                print(f"        id={row[0]} {row[1]} capacity={row[2]} enrolled={row[3]} actual={row[4]}")
            return 1
        print("\n容量一致性校验：通过（enrolled_count 与真实选课数完全一致）")
    finally:
        conn.close()

    missing = []
    check = sqlite3.connect(str(db_path))
    try:
        names = {r[0] for r in check.execute("SELECT name FROM sqlite_master")}
        missing = [n for n in (*EXPECTED_TABLES, *EXPECTED_VIEWS) if n not in names]
    finally:
        check.close()
    if missing:
        print(f"[错误] 缺少对象：{missing}")
        return 1

    print("\n建库完成。默认账号：admin / tea001 / stu001，密码均为 123456")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
