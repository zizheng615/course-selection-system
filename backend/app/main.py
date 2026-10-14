"""应用入口 —— 组装各层，本身不含业务逻辑。

职责只有四件事：
1. 启动时校验数据库结构与种子数据（`assert_schema`），让配置错误在启动期暴露；
2. 注册全局异常处理器，保证**任何**异常都返回 `{code,message,data}` 且 HTTP 200；
3. 把 `routers.ALL_ROUTERS` 里的路由全部挂上（开闭原则扩展点，见 `routers/__init__.py`）；
4. 把内嵌前端挂到 `/`。

**不要在这里写业务判断** —— 它属于 service 层。
"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import db
from .common.exception_handlers import register_exception_handlers
from .config import settings
from .routers import ALL_ROUTERS

logger = logging.getLogger("course_selection")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动期自检。数据库未初始化时给出可执行的修复指引，而不是抛一堆栈。"""
    try:
        db.assert_schema()
    except sqlite3.Error as exc:
        raise RuntimeError(
            f"数据库不可用：{exc}\n"
            f"数据库路径：{settings.db_path}\n"
            f"请先执行：python scripts/init_db.py"
        ) from exc
    logger.info("数据库就绪：%s", settings.db_path)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="高校选课管理系统（Python + SQLite）",
        description="对标 Vue3 + Spring Boot 3 + MySQL 版本的功能等价实现",
        version="1.0.0",
        lifespan=lifespan,
    )

    # 同源部署不需要 CORS；保留是为了方便用浏览器控制台或外部工具调试。
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    # 扩展点：新增业务模块只需往 ALL_ROUTERS 追加一项
    for router in ALL_ROUTERS:
        app.include_router(router)

    # 前端挂在最后：Starlette 按注册顺序匹配，先匹配到的 /api 路由优先，
    # 剩下的才落到静态文件。StaticFiles(html=True) 让 "/" 命中 index.html。
    if settings.static_dir.is_dir():
        app.mount("/", StaticFiles(directory=str(settings.static_dir), html=True), name="static")
    else:
        logger.warning("未找到前端静态目录：%s（仅 API 可用）", settings.static_dir)

    return app


app = create_app()
