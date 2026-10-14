"""当前登录用户的身份载体。

对标参考项目的 `security/UserContext`（那边靠 ThreadLocal 传递），
本项目改成**显式参数传递**：路由函数签名上写 `user: CurrentUser = Depends(...)`。

理由：FastAPI 的同步依赖与同步路由由线程池分派，可能落在不同线程上，
ThreadLocal 在两者之间并不可靠；显式传递既没有这个隐患，也让「这个接口需要什么身份」
在函数签名上一眼可见，跟本项目「权限声明式」的取向一致。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..common.errors import BusinessException, ErrorCode

ROLE_ADMIN = "ADMIN"
ROLE_TEACHER = "TEACHER"
ROLE_STUDENT = "STUDENT"

#: 角色 -> 中文名（账号管理列表里展示用）
ROLE_NAMES: dict[str, str] = {
    ROLE_ADMIN: "管理员",
    ROLE_TEACHER: "教师",
    ROLE_STUDENT: "学生",
}


@dataclass(frozen=True)
class UserContext:
    user_id: int
    username: str
    role: str
    real_name: str
    #: 学生为 student.id，教师为 teacher.id，管理员为 None
    ref_id: int | None = None

    @classmethod
    def from_claims(cls, claims: dict[str, Any]) -> "UserContext":
        ref = claims.get("refId")
        return cls(
            user_id=int(claims.get("sub") or 0),
            username=str(claims.get("username") or ""),
            role=str(claims.get("role") or ""),
            real_name=str(claims.get("realName") or ""),
            ref_id=int(ref) if ref is not None else None,
        )

    # ---- 业务主键取值：拿不到就是越权，一律 1003 ----

    def require_student_id(self) -> int:
        if self.role != ROLE_STUDENT or self.ref_id is None:
            raise BusinessException(ErrorCode.NO_PERMISSION, "该操作仅学生可用")
        return self.ref_id

    def require_teacher_id(self) -> int:
        if self.role != ROLE_TEACHER or self.ref_id is None:
            raise BusinessException(ErrorCode.NO_PERMISSION, "该操作仅教师可用")
        return self.ref_id

    @property
    def role_name(self) -> str:
        return ROLE_NAMES.get(self.role, self.role)
