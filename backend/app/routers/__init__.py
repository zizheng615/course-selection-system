"""路由注册表 —— 「开闭原则」的第二个扩展点。

`main.py` 只做 `for r in ALL_ROUTERS: app.include_router(r)`。
**新增一个业务模块 = 写一个 router 模块 + 往下面这个元组里追加一项**，
不需要修改 `main.py` 或任何既有模块。
"""

from fastapi import APIRouter

from . import ai, auth, course, enrollment, schedule, stats, student, teacher, user

#: 顺序只影响 OpenAPI 文档里的分组顺序，不影响路由匹配
ALL_ROUTERS: tuple[APIRouter, ...] = (
    auth.router,
    course.router,
    schedule.router,
    student.router,
    teacher.router,
    user.router,
    enrollment.router,
    stats.router,
    ai.router,
)

__all__ = ["ALL_ROUTERS"]
