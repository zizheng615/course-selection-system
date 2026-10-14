"""学生管理接口。对标参考项目的 `controller/StudentController`（类级 ADMIN）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..common.result import ok
from ..schemas.person import StudentDTO
from ..security import UserContext, require_role
from ..service import student_service

router = APIRouter(prefix="/api/students", tags=["学生管理"])

AdminDep = Depends(require_role("ADMIN"))


@router.get("", summary="学生分页列表")
def list_students(
    keyword: str | None = Query(None),
    major: str | None = Query(None),
    page: int | None = Query(1),
    size: int | None = Query(10),
    _: UserContext = AdminDep,
) -> dict:
    return ok(student_service.list_students(
        keyword=keyword, major=major, page_no=page, size=size
    ))


@router.get("/majors", summary="专业选项")
def list_majors(_: UserContext = AdminDep) -> dict:
    return ok(student_service.list_majors())


@router.post("", summary="新增学生（自动创建登录账号）")
def create_student(dto: StudentDTO, _: UserContext = AdminDep) -> dict:
    return ok(student_service.create_student(dto))


@router.put("/{student_id}", summary="修改学生")
def update_student(student_id: int, dto: StudentDTO, _: UserContext = AdminDep) -> dict:
    return ok(student_service.update_student(student_id, dto))


@router.delete("/{student_id}", summary="删除学生")
def delete_student(student_id: int, _: UserContext = AdminDep) -> dict:
    student_service.delete_student(student_id)
    return ok()
