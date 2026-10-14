"""学生服务。对标参考项目的 `service/StudentService`。

新增学生时**自动创建登录账号**（账号 = 学号，初始密码取系统默认值），
否则新学生无法登录系统，管理员还得再去「账号管理」里手工补一个。
"""

from __future__ import annotations

import sqlite3

from .. import db
from ..common.errors import BusinessException, ErrorCode
from ..common.result import normalize_page, page
from ..config import settings
from ..repository import enrollment_repo, student_repo, user_repo
from ..schemas.person import StudentDTO, StudentVO
from ..security.context import ROLE_STUDENT
from ..security.password import hash_password


def list_students(
    *, keyword: str | None = None, major: str | None = None,
    page_no: int | None = None, size: int | None = None,
) -> dict:
    p, s = normalize_page(page_no, size)
    rows, total = student_repo.search(
        db.connection(),
        keyword=(keyword or "").strip(),
        major=(major or "").strip(),
        page=p,
        size=s,
    )
    return page([StudentVO.of_row(r) for r in rows], total, p, s)


def list_majors() -> list[str]:
    return student_repo.find_distinct_majors(db.connection())


def _assert_no_conflict(
    conn: sqlite3.Connection, dto: StudentDTO, *, exclude_id: int | None = None
) -> None:
    existing = student_repo.find_by_no(conn, dto.studentNo)
    if existing is not None and (exclude_id is None or int(existing["id"]) != exclude_id):
        raise BusinessException(ErrorCode.DUPLICATE_KEY, f"学号已存在：{dto.studentNo}")


def create_student(dto: StudentDTO) -> StudentVO:
    with db.transaction() as conn:
        _assert_no_conflict(conn, dto)

        username = (dto.username or dto.studentNo).strip()
        if user_repo.exists_by_username(conn, username):
            raise BusinessException(ErrorCode.DUPLICATE_KEY, f"登录账号已存在：{username}")

        user_id = user_repo.insert(conn, {
            "username": username,
            "password_hash": hash_password(dto.password or settings.default_password),
            "role": ROLE_STUDENT,
            "real_name": dto.name,
            "status": 1,
        })
        student_id = student_repo.insert(conn, {
            "user_id": user_id,
            "student_no": dto.studentNo,
            "name": dto.name,
            "gender": dto.gender,
            "major": dto.major,
            "grade": dto.grade,
            "phone": dto.phone,
        })
        row = student_repo.find_by_id(conn, student_id)

    return StudentVO.of_row(row)


def update_student(student_id: int, dto: StudentDTO) -> StudentVO:
    with db.transaction() as conn:
        current = student_repo.find_by_id(conn, student_id)
        if current is None:
            raise BusinessException(ErrorCode.NOT_FOUND, "学生不存在")
        _assert_no_conflict(conn, dto, exclude_id=student_id)

        student_repo.update(conn, student_id, {
            "student_no": dto.studentNo,
            "name": dto.name,
            "gender": dto.gender,
            "major": dto.major,
            "grade": dto.grade,
            "phone": dto.phone,
        })
        # 姓名同步到账号表，否则登录后顶栏显示的还是旧名字
        user_repo.update_real_name(conn, int(current["user_id"]), dto.name)
        row = student_repo.find_by_id(conn, student_id)

    return StudentVO.of_row(row)


def delete_student(student_id: int) -> None:
    with db.transaction() as conn:
        current = student_repo.find_by_id(conn, student_id)
        if current is None:
            raise BusinessException(ErrorCode.NOT_FOUND, "学生不存在")

        # 已退课的历史记录同样计入 —— 这是有意保留修读记录
        count = enrollment_repo.count_by_student(conn, student_id)
        if count > 0:
            raise BusinessException(
                ErrorCode.COURSE_DELETE_FORBIDDEN,
                f"该学生存在 {count} 条选课历史记录（已退课的记录同样计入），"
                "为保留修读记录不允许删除",
            )
        # 先删业务行再删账号：student.user_id 有外键指向 sys_user
        user_id = int(current["user_id"])
        student_repo.delete(conn, student_id)
        user_repo.delete(conn, user_id)
