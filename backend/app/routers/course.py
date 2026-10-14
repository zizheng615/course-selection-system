"""课程接口。对标参考项目的 `controller/CourseController`。

**路由声明顺序有意义**：`/semesters`、`/my` 必须写在 `/{course_id}` 之前，
否则它们会被当成 `course_id` 的值去匹配路径参数。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..common.result import ok
from ..schemas.course import CourseDTO
from ..security import UserContext, authenticate, require_role
from ..service import course_service

router = APIRouter(prefix="/api/courses", tags=["课程"])

AdminDep = Depends(require_role("ADMIN"))


@router.get("", summary="课程分页列表")
def list_courses(
    keyword: str | None = Query(None),
    semester: str | None = Query(None),
    status: str | None = Query(None),
    page: int | None = Query(1),
    size: int | None = Query(10),
    _: UserContext = Depends(authenticate),
) -> dict:
    return ok(course_service.list_courses(
        keyword=keyword, semester=semester, status=status, page_no=page, size=size
    ))


@router.get("/semesters", summary="学期选项")
def list_semesters(_: UserContext = Depends(authenticate)) -> dict:
    return ok(course_service.list_semesters())


@router.get("/my", summary="我任教的课程（教师）")
def my_courses(
    semester: str | None = Query(None),
    user: UserContext = Depends(require_role("TEACHER")),
) -> dict:
    teacher_id = user.require_teacher_id()
    return ok(course_service.list_by_teacher(teacher_id, semester))


@router.get("/{course_id}", summary="课程详情")
def get_course(course_id: int, _: UserContext = Depends(authenticate)) -> dict:
    return ok(course_service.get_course(course_id))


@router.post("", summary="新增课程")
def create_course(dto: CourseDTO, _: UserContext = AdminDep) -> dict:
    return ok(course_service.create_course(dto))


@router.put("/{course_id}", summary="修改课程")
def update_course(course_id: int, dto: CourseDTO, _: UserContext = AdminDep) -> dict:
    return ok(course_service.update_course(course_id, dto))


@router.patch("/{course_id}/status", summary="开放 / 关闭选课")
def update_status(course_id: int, status: str = Query(...), _: UserContext = AdminDep) -> dict:
    course_service.update_status(course_id, status)
    return ok()


@router.delete("/{course_id}", summary="删除课程")
def delete_course(course_id: int, _: UserContext = AdminDep) -> dict:
    course_service.delete_course(course_id)
    return ok()
