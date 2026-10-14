"""仓储层：只承载 SQL，不开关事务。

事务边界一律由 Service 层通过 `db.transaction()` 控制 —— 与参考项目
「`@Transactional` 只出现在 Service」的分层约定一致。
每个函数第一个参数都是 `conn`，由调用方传入，便于把多个仓储操作
纳入同一个事务。
"""

from . import (
    course_repo,
    enrollment_repo,
    schedule_repo,
    stats_repo,
    student_repo,
    teacher_repo,
    user_repo,
)

__all__ = [
    "course_repo",
    "enrollment_repo",
    "schedule_repo",
    "stats_repo",
    "student_repo",
    "teacher_repo",
    "user_repo",
]
