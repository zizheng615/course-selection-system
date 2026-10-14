"""账号 DTO / VO。对标参考项目的 `dto/UserCredentialDTO`、`vo/UserVO`。"""

from __future__ import annotations

import sqlite3

from pydantic import Field, field_validator

from ..common.convert import to_int
from ..security.context import ROLE_NAMES
from ._base import DTO, VO

_LINK_STUDENT = "学生"
_LINK_TEACHER = "教师"
_LINK_NONE = "—"


class UserCredentialDTO(DTO):
    username: str = Field(..., min_length=3, max_length=50)
    #: **留空 = 只改账号，不动密码**
    password: str | None = Field(None, min_length=6, max_length=32)

    @field_validator("username")
    @classmethod
    def _username_charset(cls, v: str) -> str:
        if not all(c.isascii() and (c.isalnum() or c in "_.-") for c in v):
            raise ValueError("登录账号只能包含字母、数字、下划线、点或短横线")
        return v


class UserVO(VO):
    id: int
    username: str
    role: str
    roleName: str
    realName: str
    status: int | None = None
    createdAt: str | None = None
    #: 学生 / 教师 / —
    linkType: str
    linkNo: str | None = None
    linkExtra: str | None = None

    @classmethod
    def of_row(cls, row: sqlite3.Row) -> "UserVO":
        """10 列：u.id, u.username, u.role, u.real_name, u.status, u.created_at,
        s.student_no, s.major, t.teacher_no, t.dept
        """
        student_no, major, teacher_no, dept = row[6], row[7], row[8], row[9]
        if student_no:
            link_type, link_no, link_extra = _LINK_STUDENT, student_no, major
        elif teacher_no:
            link_type, link_no, link_extra = _LINK_TEACHER, teacher_no, dept
        else:
            link_type, link_no, link_extra = _LINK_NONE, None, None

        role = row[2]
        return cls(
            id=row[0],
            username=row[1],
            role=role,
            roleName=ROLE_NAMES.get(role, role),
            realName=row[3],
            status=to_int(row[4]),
            createdAt=row[5],
            linkType=link_type,
            linkNo=link_no,
            linkExtra=link_extra,
        )
