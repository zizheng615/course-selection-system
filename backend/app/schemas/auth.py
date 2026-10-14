"""认证相关 DTO / VO。对应参考项目的 `dto/LoginDTO`、`vo/LoginVO`。"""

from __future__ import annotations

from pydantic import Field

from ._base import DTO, VO


class LoginDTO(DTO):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=100)


class LoginVO(VO):
    """`/auth/login` 与 `/auth/me` 共用。

    `/auth/me` 返回时 `token` 与 `expireHours` 为 null，只回填用户信息。
    """

    token: str | None = None
    userId: int
    username: str
    role: str
    realName: str
    #: 学生 = student.id，教师 = teacher.id，管理员 = null
    refId: int | None = None
    expireHours: int | None = None

    @classmethod
    def of_login(
        cls, *, token: str, user_id: int, username: str, role: str, real_name: str,
        ref_id: int | None, expire_hours: int,
    ) -> "LoginVO":
        return cls(
            token=token, userId=user_id, username=username, role=role,
            realName=real_name, refId=ref_id, expireHours=expire_hours,
        )

    @classmethod
    def of_user(cls, *, user_id: int, username: str, role: str, real_name: str, ref_id: int | None) -> "LoginVO":
        return cls(token=None, userId=user_id, username=username, role=role,
                   realName=real_name, refId=ref_id, expireHours=None)
