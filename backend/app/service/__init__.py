"""业务服务层：**事务边界只在这一层**。

Repository 只接受 `conn` 执行 SQL，自己不开关事务；路由只做参数绑定与响应包装，
不写业务规则。与参考项目「`@Transactional` 只出现在 Service」的分层约定一致。
"""

from . import (
    ai_service,
    auth_service,
    course_service,
    enrollment_service,
    schedule_service,
    semester_resolver,
    stats_service,
    student_service,
    teacher_service,
    user_service,
)

__all__ = [
    "ai_service",
    "auth_service",
    "course_service",
    "enrollment_service",
    "schedule_service",
    "semester_resolver",
    "stats_service",
    "student_service",
    "teacher_service",
    "user_service",
]
