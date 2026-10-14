"""学生 / 教师 DTO 与 VO。对标 `dto/StudentDTO`、`dto/TeacherDTO` 及其 VO。"""

from __future__ import annotations

import sqlite3

from pydantic import Field, field_validator

from ..common.convert import to_int
from ._base import DTO, VO


class StudentDTO(DTO):
    studentNo: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=50)
    gender: str = "M"
    major: str = Field(..., min_length=1, max_length=50)
    grade: str = Field(..., min_length=1, max_length=10)
    phone: str | None = Field(None, max_length=20)
    #: 缺省时取 studentNo；新建学生必然同时创建登录账号
    username: str | None = Field(None, min_length=3, max_length=50)
    #: 初始密码，缺省用系统默认密码
    password: str | None = Field(None, min_length=6, max_length=32)

    @field_validator("gender")
    @classmethod
    def _gender(cls, v: str) -> str:
        if v not in ("M", "F"):
            raise ValueError("性别只能为 M 或 F")
        return v


class StudentVO(VO):
    id: int
    userId: int | None = None
    studentNo: str
    name: str
    gender: str | None = None
    major: str | None = None
    grade: str | None = None
    phone: str | None = None

    @classmethod
    def of_row(cls, row: sqlite3.Row) -> "StudentVO":
        """7 列：id, user_id, student_no, name, gender, major, grade, phone（下标 0-6）"""
        return cls(
            id=row[0], userId=to_int(row[1]), studentNo=row[2], name=row[3],
            gender=row[4], major=row[5], grade=row[6], phone=row[7],
        )


class TeacherDTO(DTO):
    teacherNo: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=50)
    title: str | None = Field(None, max_length=20)
    dept: str = Field(..., min_length=1, max_length=50)
    username: str | None = Field(None, min_length=3, max_length=50)
    password: str | None = Field(None, min_length=6, max_length=32)


class TeacherVO(VO):
    id: int
    userId: int | None = None
    teacherNo: str
    name: str
    title: str | None = None
    dept: str | None = None

    @classmethod
    def of_row(cls, row: sqlite3.Row) -> "TeacherVO":
        """6 列：id, user_id, teacher_no, name, title, dept"""
        return cls(
            id=row[0], userId=to_int(row[1]), teacherNo=row[2],
            name=row[3], title=row[4], dept=row[5],
        )
