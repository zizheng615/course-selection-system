"""开发环境启动脚本：`python run.py` -> http://localhost:8000

生产部署不需要它，直接用 uvicorn：
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir backend
"""

from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / "backend"))

import uvicorn  # noqa: E402

from app.config import settings  # noqa: E402


def main() -> None:
    if not settings.db_path.exists():
        print(f"[提示] 未找到数据库 {settings.db_path}")
        print("       请先执行：python scripts/init_db.py")
        raise SystemExit(1)

    print("=" * 62)
    print("  高校选课管理系统 (Python + SQLite)")
    print("=" * 62)
    print(f"  地址      http://localhost:8000")
    print(f"  接口文档  http://localhost:8000/docs")
    print(f"  数据库    {settings.db_path}")
    print(f"  AI 模式   {'知识库 + ' + settings.ai_provider_name if settings.ai_enabled and settings.ai_api_key else '仅本地知识库'}")
    print("=" * 62)
    print("  演示账号：admin / tea001 / stu001，口令均为 123456")
    print("=" * 62)

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
