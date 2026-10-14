"""教师管理接口。对标参考项目的 `controller/TeacherController`（类级 ADMIN）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..common.result import ok
from ..schemas.person import TeacherDTO
from ..security import UserContext, require_role
from ..service import teacher_service

router = APIRouter(prefix="/api/teachers", tags=["教师管理"])

AdminDep = Depends(require_role("ADMIN"))


@router.get("", summary="教师分页列表")
def list_teachers(
    keyword: str | None = Query(None),
    dept: str | None = Query(None),
    page: int | None = Query(1),
    size: int | None = Query(10),
    _: UserContext = AdminDep,
) -> dict:
    return ok(teacher_service.list_teachers(
        keyword=keyword, dept=dept, page_no=page, size=size
    ))


@router.get("/all", summary="全部教师（下拉框用）")
def list_all_teachers(_: UserContext = AdminDep) -> dict:
    return ok(teacher_service.list_all())


@router.post("", summary="新增教师（自动创建登录账号）")
def create_teacher(dto: TeacherDTO, _: UserContext = AdminDep) -> dict:
    return ok(teacher_service.create_teacher(dto))


@router.put("/{teacher_id}", summary="修改教师")
def update_teacher(teacher_id: int, dto: TeacherDTO, _: UserContext = AdminDep) -> dict:
    return ok(teacher_service.update_teacher(teacher_id, dto))


@router.delete("/{teacher_id}", summary="删除教师")
def delete_teacher(teacher_id: int, _: UserContext = AdminDep) -> dict:
    teacher_service.delete_teacher(teacher_id)
    return ok()
