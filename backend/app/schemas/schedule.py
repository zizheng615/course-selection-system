"""上课时间 DTO / VO。对标参考项目的 `dto/ScheduleDTO`、`vo/ScheduleVO`。"""

from __future__ import annotations

import sqlite3

from pydantic import Field

from ..common.convert import to_int, weekday_name
from ._base import DTO, VO


class ScheduleDTO(DTO):
    courseId: int = Field(..., ge=1)
    weekday: int = Field(..., ge=1, le=7)
    startSection: int = Field(..., ge=1, le=12)
    endSection: int = Field(..., ge=1, le=12)
    startWeek: int = Field(..., ge=1, le=30)
    endWeek: int = Field(..., ge=1, le=30)
    classroom: str | None = Field(None, max_length=50)


class ScheduleVO(VO):
    id: int
    courseId: int | None = None
    courseName: str | None = None
    weekday: int | None = None
    weekdayName: str | None = None
    startSection: int | None = None
    endSection: int | None = None
    startWeek: int | None = None
    endWeek: int | None = None
    classroom: str | None = None

    @classmethod
    def of_row(cls, row: sqlite3.Row) -> "ScheduleVO":
        """9 列：id, course_id, course_name, weekday, start_section, end_section,
        start_week, end_week, classroom
        """
        return cls(
            id=row[0],
            courseId=to_int(row[1]),
            courseName=row[2],
            weekday=to_int(row[3]),
            weekdayName=weekday_name(row[3]),
            startSection=to_int(row[4]),
            endSection=to_int(row[5]),
            startWeek=to_int(row[6]),
            endWeek=to_int(row[7]),
            classroom=row[8],
        )

    @classmethod
    def of_detail(
        cls, *, schedule_id: int, course_id: int, course_name: str, weekday: int,
        start_section: int, end_section: int, start_week: int, end_week: int,
        classroom: str | None,
    ) -> "ScheduleVO":
        """写操作后按已知字段直接构造，省一次查询。"""
        return cls(
            id=schedule_id, courseId=course_id, courseName=course_name, weekday=weekday,
            weekdayName=weekday_name(weekday), startSection=start_section, endSection=end_section,
            startWeek=start_week, endWeek=end_week, classroom=classroom,
        )
