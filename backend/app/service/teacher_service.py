"""教师服务。对标参考项目的 `service/TeacherService`。结构与 `student_service` 对称。"""

from __future__ import annotations

import sqlite3

from .. import db
from ..common.errors import BusinessException, ErrorCode
from ..common.result import normalize_page, page
from ..config import settings
from ..repository import course_repo, teacher_repo, user_repo
from ..schemas.person import TeacherDTO, TeacherVO
from ..security.context import ROLE_TEACHER
from ..security.password import hash_password


def list_teachers(
    *, keyword: str | None = None, dept: str | None = None,
    page_no: int | None = None, size: int | None = None,
) -> dict:
    p, s = normalize_page(page_no, size)
    rows, total = teacher_repo.search(
        db.connection(),
        keyword=(keyword or "").strip(),
        dept=(dept or "").strip(),
        page=p,
        size=s,
    )
    return page([TeacherVO.of_row(r) for r in rows], total, p, s)


def list_all() -> list[TeacherVO]:
    """全部教师，供课程表单的教师下拉框使用（不分页）。"""
    return [TeacherVO.of_row(r) for r in teacher_repo.find_all(db.connection())]


def _assert_no_conflict(
    conn: sqlite3.Connection, dto: TeacherDTO, *, exclude_id: int | None = None
) -> None:
    existing = conn.execute(
        "SELECT id FROM teacher WHERE teacher_no = ?", (dto.teacherNo,)
    ).fetchone()
    if existing is not None and (exclude_id is None or int(existing["id"]) != exclude_id):
        raise BusinessException(ErrorCode.DUPLICATE_KEY, f"工号已存在：{dto.teacherNo}")


def create_teacher(dto: TeacherDTO) -> TeacherVO:
    with db.transaction() as conn:
        _assert_no_conflict(conn, dto)

        username = (dto.username or dto.teacherNo).strip()
        if user_repo.exists_by_username(conn, username):
            raise BusinessException(ErrorCode.DUPLICATE_KEY, f"登录账号已存在：{username}")

        user_id = user_repo.insert(conn, {
            "username": username,
            "password_hash": hash_password(dto.password or settings.default_password),
            "role": ROLE_TEACHER,
            "real_name": dto.name,
            "status": 1,
        })
        teacher_id = teacher_repo.insert(conn, {
            "user_id": user_id,
            "teacher_no": dto.teacherNo,
            "name": dto.name,
            "title": dto.title,
            "dept": dto.dept,
        })
        row = teacher_repo.find_by_id(conn, teacher_id)

    return TeacherVO.of_row(row)


def update_teacher(teacher_id: int, dto: TeacherDTO) -> TeacherVO:
    with db.transaction() as conn:
        current = teacher_repo.find_by_id(conn, teacher_id)
        if current is None:
            raise BusinessException(ErrorCode.NOT_FOUND, "教师不存在")
        _assert_no_conflict(conn, dto, exclude_id=teacher_id)

        teacher_repo.update(conn, teacher_id, {
            "teacher_no": dto.teacherNo,
            "name": dto.name,
            "title": dto.title,
            "dept": dto.dept,
        })
        user_repo.update_real_name(conn, int(current["user_id"]), dto.name)
        row = teacher_repo.find_by_id(conn, teacher_id)

    return TeacherVO.of_row(row)


def delete_teacher(teacher_id: int) -> None:
    with db.transaction() as conn:
        current = teacher_repo.find_by_id(conn, teacher_id)
        if current is None:
            raise BusinessException(ErrorCode.NOT_FOUND, "教师不存在")

        count = course_repo.count_by_teacher(conn, teacher_id)
        if count > 0:
            raise BusinessException(
                ErrorCode.COURSE_DELETE_FORBIDDEN,
                f"该教师还有 {count} 门课程，请先转移或删除课程",
            )
        user_id = int(current["user_id"])
        teacher_repo.delete(conn, teacher_id)
        user_repo.delete(conn, user_id)
