"""排课服务。对标参考项目的 `service/ScheduleService`。

这里的教师冲突检查是**排课侧**的冲突（同一教师不能在同一时段有两门课），
与学生选课侧的「个人课表冲突」是两回事，判定维度不同（前者不跨课程看学生，
后者只看单个学生的已选课程）。
"""

from __future__ import annotations

from .. import db
from ..common.convert import weekday_name
from ..common.errors import BusinessException, ErrorCode
from ..repository import course_repo, schedule_repo
from ..schemas.schedule import ScheduleDTO, ScheduleVO


def list_by_course(course_id: int) -> list[ScheduleVO]:
    return [ScheduleVO.of_row(r) for r in schedule_repo.find_by_course(db.connection(), course_id)]


def _validate_order(dto: ScheduleDTO) -> None:
    if dto.startSection > dto.endSection:
        raise BusinessException(ErrorCode.PARAM_ERROR, "开始节次不能大于结束节次")
    if dto.startWeek > dto.endWeek:
        raise BusinessException(ErrorCode.PARAM_ERROR, "起始周不能大于结束周")


def _assert_no_teacher_conflict(
    conn, *, course_id: int, dto: ScheduleDTO, exclude_id: int
) -> None:
    """同一教师在同一学期、同一星期，不允许节次区间重叠。

    `exclude_id`：新增时传 0，修改时传自身 id 以排除自己 —— 否则一条排课
    会和它自己判为重叠，导致「什么都不改也保存不了」。
    """
    course = course_repo.find_by_id(conn, course_id)
    if course is None:
        raise BusinessException(ErrorCode.NOT_FOUND, "课程不存在")

    conflict = schedule_repo.count_teacher_conflict(
        conn,
        teacher_id=int(course["teacher_id"]),
        semester=str(course["semester"]),
        weekday=dto.weekday,
        start_section=dto.startSection,
        end_section=dto.endSection,
        exclude_id=exclude_id,
    )
    if conflict:
        raise BusinessException(
            ErrorCode.TIME_CONFLICT,
            f"该教师在{weekday_name(dto.weekday)} {dto.startSection}-{dto.endSection} 节"
            "已有其他课程安排，排课冲突",
        )


def create_schedule(dto: ScheduleDTO) -> ScheduleVO:
    _validate_order(dto)
    with db.transaction() as conn:
        _assert_no_teacher_conflict(conn, course_id=dto.courseId, dto=dto, exclude_id=0)
        schedule_id = schedule_repo.insert(conn, {
            "course_id": dto.courseId,
            "weekday": dto.weekday,
            "start_section": dto.startSection,
            "end_section": dto.endSection,
            "start_week": dto.startWeek,
            "end_week": dto.endWeek,
            "classroom": dto.classroom,
        })
        course = course_repo.find_by_id(conn, dto.courseId)
        course_name = str(course["name"]) if course else ""

    return ScheduleVO.of_detail(
        schedule_id=schedule_id, course_id=dto.courseId, course_name=course_name,
        weekday=dto.weekday, start_section=dto.startSection, end_section=dto.endSection,
        start_week=dto.startWeek, end_week=dto.endWeek, classroom=dto.classroom,
    )


def update_schedule(schedule_id: int, dto: ScheduleDTO) -> ScheduleVO:
    _validate_order(dto)
    with db.transaction() as conn:
        if schedule_repo.find_by_id(conn, schedule_id) is None:
            raise BusinessException(ErrorCode.NOT_FOUND, "上课时间记录不存在")
        _assert_no_teacher_conflict(conn, course_id=dto.courseId, dto=dto, exclude_id=schedule_id)
        schedule_repo.update(conn, schedule_id, {
            "course_id": dto.courseId,
            "weekday": dto.weekday,
            "start_section": dto.startSection,
            "end_section": dto.endSection,
            "start_week": dto.startWeek,
            "end_week": dto.endWeek,
            "classroom": dto.classroom,
        })
        course = course_repo.find_by_id(conn, dto.courseId)
        course_name = str(course["name"]) if course else ""

    return ScheduleVO.of_detail(
        schedule_id=schedule_id, course_id=dto.courseId, course_name=course_name,
        weekday=dto.weekday, start_section=dto.startSection, end_section=dto.endSection,
        start_week=dto.startWeek, end_week=dto.endWeek, classroom=dto.classroom,
    )


def delete_schedule(schedule_id: int) -> None:
    with db.transaction() as conn:
        if schedule_repo.find_by_id(conn, schedule_id) is None:
            raise BusinessException(ErrorCode.NOT_FOUND, "上课时间记录不存在")
        schedule_repo.delete(conn, schedule_id)
