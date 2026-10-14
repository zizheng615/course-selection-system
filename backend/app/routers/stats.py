"""统计报表接口。对标参考项目的 `controller/StatsController`（类级 ADMIN）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..common.result import ok
from ..security import UserContext, require_role
from ..service import stats_service

router = APIRouter(prefix="/api/stats", tags=["统计报表"])

AdminDep = Depends(require_role("ADMIN"))


@router.get("/popular-courses", summary="热门课程 Top-N")
def popular_courses(
    semester: str | None = Query(None),
    limit: int | None = Query(10),
    _: UserContext = AdminDep,
) -> dict:
    return ok(stats_service.popular_courses(semester, limit))


@router.get("/major-distribution", summary="各专业选课分布")
def major_distribution(_: UserContext = AdminDep) -> dict:
    return ok(stats_service.major_distribution())


@router.get("/teacher-workload", summary="教师工作量")
def teacher_workload(
    semester: str | None = Query(None),
    _: UserContext = AdminDep,
) -> dict:
    return ok(stats_service.teacher_workload(semester))
