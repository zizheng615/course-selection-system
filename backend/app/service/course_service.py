"""课程服务。对标参考项目的 `service/CourseService`。"""

from __future__ import annotations

from .. import db
from ..common.errors import BusinessException, ErrorCode
from ..common.result import normalize_page, page
from ..repository import course_repo, enrollment_repo, schedule_repo, teacher_repo
from ..schemas.course import CourseDTO, CourseVO

VALID_STATUS = ("OPEN", "CLOSED")


def list_courses(
    *,
    keyword: str | None = None,
    semester: str | None = None,
    status: str | None = None,
    page_no: int | None = None,
    size: int | None = None,
) -> dict:
    p, s = normalize_page(page_no, size)
    rows, total = course_repo.search_courses(
        db.connection(),
        # 条件参数统一归一化成空字符串，SQL 里就能用 :param = '' 简单比较
        keyword=(keyword or "").strip(),
        semester=(semester or "").strip(),
        status=(status or "").strip(),
        page=p,
        size=s,
    )
    return page([CourseVO.of_list_row(r) for r in rows], total, p, s)


def list_semesters() -> list[str]:
    return course_repo.find_distinct_semesters(db.connection())


def list_by_teacher(teacher_id: int, semester: str | None) -> list[CourseVO]:
    rows = course_repo.find_by_teacher(db.connection(), teacher_id, (semester or "").strip())
    return [CourseVO.of_list_row(r) for r in rows]


def get_course(course_id: int) -> CourseVO:
    row = course_repo.find_detail_by_id(db.connection(), course_id)
    if row is None:
        raise BusinessException(ErrorCode.NOT_FOUND, "课程不存在")
    return CourseVO.of_list_row(row)


def _assert_valid_status(status: str) -> str:
    if status not in VALID_STATUS:
        raise BusinessException(ErrorCode.PARAM_ERROR, "状态只能为 OPEN 或 CLOSED")
    return status


def create_course(dto: CourseDTO) -> CourseVO:
    with db.transaction() as conn:
        if teacher_repo.find_by_id(conn, dto.teacherId) is None:
            raise BusinessException(ErrorCode.NOT_FOUND, "授课教师不存在")
        if course_repo.exists_by_code_and_semester(conn, dto.courseCode, dto.semester):
            raise BusinessException(ErrorCode.DUPLICATE_KEY, f"课程代码已存在：{dto.courseCode}")

        course_id = course_repo.insert(conn, {
            "course_code": dto.courseCode,
            "name": dto.name,
            "credit": dto.credit,
            "hours": dto.hours,
            "course_type": dto.courseType,
            "dept": dto.dept,
            "semester": dto.semester,
            "teacher_id": dto.teacherId,
            "capacity": dto.capacity,
            "status": _assert_valid_status(dto.status),
            "intro": dto.intro,
        })
    return get_course(course_id)


def update_course(course_id: int, dto: CourseDTO) -> CourseVO:
    with db.transaction() as conn:
        current = course_repo.find_by_id(conn, course_id)
        if current is None:
            raise BusinessException(ErrorCode.NOT_FOUND, "课程不存在")
        if teacher_repo.find_by_id(conn, dto.teacherId) is None:
            raise BusinessException(ErrorCode.NOT_FOUND, "授课教师不存在")

        # 唯一键是 (course_code, semester)，只在两者之一变化时才需要查重
        if dto.courseCode != current["course_code"] or dto.semester != current["semester"]:
            if course_repo.exists_by_code_and_semester(conn, dto.courseCode, dto.semester):
                raise BusinessException(ErrorCode.DUPLICATE_KEY, f"课程代码已存在：{dto.courseCode}")

        enrolled = int(current["enrolled_count"])
        if dto.capacity < enrolled:
            raise BusinessException(ErrorCode.PARAM_ERROR, f"容量不能小于当前已选人数 {enrolled}")

        course_repo.update(conn, course_id, {
            "course_code": dto.courseCode,
            "name": dto.name,
            "credit": dto.credit,
            "hours": dto.hours,
            "course_type": dto.courseType,
            "dept": dto.dept,
            "semester": dto.semester,
            "teacher_id": dto.teacherId,
            "capacity": dto.capacity,
            "status": _assert_valid_status(dto.status),
            "intro": dto.intro,
        })
    return get_course(course_id)


def update_status(course_id: int, status: str) -> None:
    _assert_valid_status(status)
    with db.transaction() as conn:
        if course_repo.find_by_id(conn, course_id) is None:
            raise BusinessException(ErrorCode.NOT_FOUND, "课程不存在")
        course_repo.update_status(conn, course_id, status)


def delete_course(course_id: int) -> None:
    with db.transaction() as conn:
        if course_repo.find_by_id(conn, course_id) is None:
            raise BusinessException(ErrorCode.NOT_FOUND, "课程不存在")

        # 已退课的历史记录同样计入 —— 与「学生有选课历史不允许删」同一口径
        count = enrollment_repo.count_by_course(conn, course_id)
        if count > 0:
            raise BusinessException(
                ErrorCode.COURSE_DELETE_FORBIDDEN,
                f"该课程已有 {count} 条选课记录，无法删除；如需停止选课请改为「关闭」",
            )
        # 上课时间表有外键指向课程，必须先删
        schedule_repo.delete_by_course(conn, course_id)
        course_repo.delete(conn, course_id)
