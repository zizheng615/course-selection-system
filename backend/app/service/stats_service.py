"""统计报表服务。对标参考项目的 `service/StatsService`。"""

from __future__ import annotations

from .. import db
from ..repository import stats_repo
from ..schemas.stats import MajorStatVO, PopularCourseVO, TeacherWorkloadVO
from . import semester_resolver

DEFAULT_LIMIT = 10
MAX_LIMIT = 100


def _normalize_limit(limit: int | None) -> int:
    """非法或越界的 limit 一律收敛到默认值。

    不这么做的话，前端传个 limit=100000 会把整张表连同 LEFT JOIN 一起捞出来。
    """
    if limit is None or limit <= 0 or limit > MAX_LIMIT:
        return DEFAULT_LIMIT
    return int(limit)


def popular_courses(semester: str | None = None, limit: int | None = None) -> list[PopularCourseVO]:
    conn = db.connection()
    rows = stats_repo.find_popular_courses(
        conn, semester_resolver.resolve(conn, semester), _normalize_limit(limit)
    )
    return [PopularCourseVO.of_row(r) for r in rows]


def major_distribution() -> list[MajorStatVO]:
    return [MajorStatVO.of_row(r) for r in stats_repo.find_major_distribution(db.connection())]


def teacher_workload(semester: str | None = None) -> list[TeacherWorkloadVO]:
    conn = db.connection()
    rows = stats_repo.find_teacher_workload(conn, semester_resolver.resolve(conn, semester))
    return [TeacherWorkloadVO.of_row(r) for r in rows]
