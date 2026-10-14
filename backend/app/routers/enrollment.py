"""选课接口。对标参考项目的 `controller/EnrollmentController`。

**路径约定**：学生自助与管理员操作都挂在 `/api/enrollments` 下，两者都有删除语义。
为避免映射冲突，管理员操作统一加 `record` 段：
`/api/enrollments/record/{id}`。学生退课保持 `/api/enrollments/{courseId}`。
新增管理端接口时沿用这个约定。

本控制器的 prefix 是 `/api` 而非 `/api/enrollments`，因为教师/管理员查学生名单的
`/api/courses/{courseId}/students` 也归它管（与参考项目一致）。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..common.result import ok
from ..schemas.enrollment import AdminEnrollDTO, ScoreDTO, SelectCourseDTO
from ..security import UserContext, require_role
from ..service import enrollment_service

router = APIRouter(prefix="/api", tags=["选课"])

StudentDep = Depends(require_role("STUDENT"))
AdminDep = Depends(require_role("ADMIN"))
TeacherOrAdminDep = Depends(require_role("TEACHER", "ADMIN"))


# ---------------------------- 学生自助 ----------------------------

@router.post("/enrollments", summary="选课")
def select_course(dto: SelectCourseDTO, user: UserContext = StudentDep) -> dict:
    enrollment_service.select_course(user.require_student_id(), dto.courseId)
    return ok()


@router.get("/enrollments/my", summary="我的课程（含成绩）")
def my_courses(
    semester: str | None = Query(None),
    user: UserContext = StudentDep,
) -> dict:
    return ok(enrollment_service.my_courses(user.require_student_id(), semester))


@router.get("/enrollments/my/timetable", summary="我的课表")
def my_timetable(
    semester: str | None = Query(None),
    user: UserContext = StudentDep,
) -> dict:
    return ok(enrollment_service.my_timetable(user.require_student_id(), semester))


@router.get("/enrollments/available", summary="可选课程（已排除已选与冲突）")
def available_courses(
    semester: str | None = Query(None),
    user: UserContext = StudentDep,
) -> dict:
    return ok(enrollment_service.available_courses(user.require_student_id(), semester))


@router.get("/enrollments/conflicts", summary="与我已选课程冲突的课程")
def conflicting_courses(
    semester: str | None = Query(None),
    user: UserContext = StudentDep,
) -> dict:
    return ok(enrollment_service.conflicting_courses(user.require_student_id(), semester))


@router.delete("/enrollments/{course_id}", summary="退课（软退课）")
def withdraw_course(course_id: int, user: UserContext = StudentDep) -> dict:
    enrollment_service.withdraw_course(user.require_student_id(), course_id)
    return ok()


# ---------------------------- 教师 / 管理员 ----------------------------

@router.get("/courses/{course_id}/students", summary="课程学生名单")
def course_students(course_id: int, _: UserContext = TeacherOrAdminDep) -> dict:
    return ok(enrollment_service.course_students(course_id))


@router.patch("/enrollments/score", summary="录入成绩")
def record_score(dto: ScoreDTO, _: UserContext = TeacherOrAdminDep) -> dict:
    enrollment_service.record_score(dto.enrollmentId, dto.score)
    return ok()


# ---------------------------- 管理员 ----------------------------

@router.get("/enrollments", summary="选课记录分页查询")
def search_enrollments(
    keyword: str | None = Query(None),
    courseId: int | None = Query(None),
    status: str | None = Query(None),
    page: int | None = Query(1),
    size: int | None = Query(10),
    _: UserContext = AdminDep,
) -> dict:
    return ok(enrollment_service.search_enrollments(
        keyword=keyword, course_id=courseId, status=status, page_no=page, size=size
    ))


@router.post("/enrollments/admin", summary="管理员代学生选课")
def admin_enroll(dto: AdminEnrollDTO, _: UserContext = AdminDep) -> dict:
    enrollment_service.admin_enroll(dto.studentId, dto.courseId)
    return ok()


@router.patch("/enrollments/record/{enrollment_id}/withdraw", summary="管理员软退课")
def admin_withdraw(enrollment_id: int, _: UserContext = AdminDep) -> dict:
    enrollment_service.admin_withdraw(enrollment_id)
    return ok()


@router.delete("/enrollments/record/{enrollment_id}", summary="管理员删除选课记录")
def admin_delete(enrollment_id: int, _: UserContext = AdminDep) -> dict:
    enrollment_service.admin_delete(enrollment_id)
    return ok()
