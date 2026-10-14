"""排课接口。对标参考项目的 `controller/ScheduleController`。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..common.result import ok
from ..schemas.schedule import ScheduleDTO
from ..security import UserContext, authenticate, require_role
from ..service import schedule_service

router = APIRouter(prefix="/api/schedules", tags=["排课"])

AdminDep = Depends(require_role("ADMIN"))


@router.get("", summary="查询某门课程的上课时间")
def list_schedules(
    courseId: int = Query(...),
    _: UserContext = Depends(authenticate),
) -> dict:
    return ok(schedule_service.list_by_course(courseId))


@router.post("", summary="新增上课时间")
def create_schedule(dto: ScheduleDTO, _: UserContext = AdminDep) -> dict:
    return ok(schedule_service.create_schedule(dto))


@router.put("/{schedule_id}", summary="修改上课时间")
def update_schedule(schedule_id: int, dto: ScheduleDTO, _: UserContext = AdminDep) -> dict:
    return ok(schedule_service.update_schedule(schedule_id, dto))


@router.delete("/{schedule_id}", summary="删除上课时间")
def delete_schedule(schedule_id: int, _: UserContext = AdminDep) -> dict:
    schedule_service.delete_schedule(schedule_id)
    return ok()
