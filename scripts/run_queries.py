"""逐条执行 `sql/03_queries.sql` 并打印结果。

用途是把「SQL 设计」这部分变成可以直接跑、可以直接看的演示，
而不是一份需要人肉复制粘贴到客户端里的文本。

    python scripts/run_queries.py                 # 跑全部语句
    python scripts/run_queries.py --only 3 3b     # 只跑编号匹配的语句
    python scripts/run_queries.py --db path.db    # 指定数据库文件

脚本本身不修改数据（03_queries.sql 里全是只读查询），因此可以反复执行。
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from app.config import settings  # noqa: E402

QUERY_FILE = BASE_DIR / "sql" / "03_queries.sql"

#: 语句上方的注释块里若有「查询 3：…」「8.1 …：」这样的编号标题，就取它做标题
NUMBER_PATTERN = re.compile(r"^(?:查询\s*)?([0-9]+(?:\.[0-9]+)?[a-z]?)\s*[:：]")
MAX_ROWS = 30


def split_statements(sql: str) -> list[tuple[str, str]]:
    """把脚本切成 (标题, 语句) 列表。

    引号里不会出现分号（本脚本的取值都是固定字面量），所以按 `;` 切是安全的。
    """
    statements: list[tuple[str, str]] = []
    title = ""
    buffer: list[str] = []

    for raw_line in sql.splitlines():
        line = raw_line.rstrip()
        stripped = line.lstrip("- ").strip()

        # 注释行：既可能是标题，也可能是普通说明，都不进 buffer
        if line.strip().startswith("--"):
            match = NUMBER_PATTERN.match(stripped)
            if match:
                title = stripped
            continue

        if not line.strip():
            continue

        buffer.append(line)
        if line.rstrip().endswith(";"):
            statement = "\n".join(buffer).strip().rstrip(";").strip()
            if statement:
                statements.append((title, statement))
            buffer = []
            title = ""

    return statements


def print_rows(cursor: sqlite3.Cursor) -> None:
    rows = cursor.fetchall()
    columns = [d[0] for d in cursor.description] if cursor.description else []

    if not columns:
        print("  （无结果集）")
        return
    if not rows:
        print("  （空结果集）")
        return

    widths = [len(str(c)) for c in columns]
    table = [[("" if v is None else str(v)) for v in row] for row in rows[:MAX_ROWS]]
    for row in table:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    def render(cells: list[str]) -> str:
        return "  " + " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(cells))

    print(render([str(c) for c in columns]))
    print("  " + "-+-".join("-" * w for w in widths))
    for row in table:
        print(render(row))
    if len(rows) > MAX_ROWS:
        print(f"  … 共 {len(rows)} 行，只显示前 {MAX_ROWS} 行")


def main() -> int:
    parser = argparse.ArgumentParser(description="执行演示查询脚本")
    parser.add_argument("--db", default=str(settings.db_path), help="SQLite 数据库文件")
    parser.add_argument("--only", nargs="*", help="只执行编号匹配的语句，如 3 3b 4")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"数据库不存在：{db_path}\n请先执行：python scripts/init_db.py", file=sys.stderr)
        return 1

    statements = split_statements(QUERY_FILE.read_text(encoding="utf-8"))
    if not statements:
        print("没有解析到任何语句", file=sys.stderr)
        return 1

    conn = sqlite3.connect(db_path)
    failures = 0

    for index, (title, statement) in enumerate(statements, start=1):
        if args.only and not any(title.startswith(f"查询 {n}") or title.startswith(n) for n in args.only):
            continue

        print()
        print("=" * 78)
        print(f"[{index}] {title or '（未命名语句）'}")
        print("=" * 78)
        try:
            print_rows(conn.execute(statement))
        except sqlite3.Error as exc:
            failures += 1
            print(f"  执行失败：{exc}", file=sys.stderr)

    conn.close()
    print()
    print(f"共执行 {len(statements)} 条语句，失败 {failures} 条。")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
