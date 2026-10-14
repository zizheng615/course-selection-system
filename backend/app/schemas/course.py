"""课程 DTO / VO。对标参考项目的 `dto/CourseDTO`、`vo/CourseVO`。

`CourseVO` 有三种来源，列集不同，用**具名工厂方法**区分（与参考项目一致）：

============================  ====  ==========================================
工厂                           列数  来源
============================  ====  ==========================================
`of_list_row`                  16   `course_repo.search_courses` / `find_by_teacher`
`of_selectable_row`            11   `course_repo.find_selectable_courses`
`of_conflict_row`               4   `course_repo.find_conflicting_courses`
============================  ====  ==========================================

**改原生查询的 SELECT 列表时，必须同步改这里的下标。**
"""

from __future__ import annotations

import sqlite3

from pydantic import Field

from ..common.convert import to_float, to_int
from ._base import DTO, VO


class CourseDTO(DTO):
    courseCode: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=100)
    credit: float = Field(..., ge=0.5, le=20)
    hours: int = Field(..., ge=1)
    courseType: str = Field(..., min_length=1, max_length=20)
    dept: str = Field(..., min_length=1, max_length=50)
    semester: str = Field(..., min_length=1, max_length=20)
    teacherId: int = Field(..., ge=1)
    capacity: int = Field(..., ge=1)
    #: 缺省 OPEN；Service 侧只接受 OPEN / CLOSED
    status: str = "OPEN"
    intro: str | None = Field(None, max_length=500)


class CourseVO(VO):
    id: int
    courseCode: str
    name: str
    credit: float | None = None
    hours: int | None = None
    courseType: str | None = None
    dept: str | None = None
    semester: str | None = None
    teacherId: int | None = None
    teacherName: str | None = None
    teacherTitle: str | None = None
    capacity: int | None = None
    enrolledCount: int | None = None
    remaining: int | None = None
    status: str | None = None
    intro: str | None = None
    #: 仅 `/enrollments/conflicts` 填充（值为冲突的那门已选课程名），其余场景为 null
    conflictWith: str | None = None

    @classmethod
    def of_list_row(cls, row: sqlite3.Row) -> "CourseVO":
        """16 列：id, course_code, name, credit, hours, course_type, dept, semester,
        teacher_id, teacher_name, teacher_title, capacity, enrolled_count,
        remaining, status, intro"""
        return cls(
            id=row[0],
            courseCode=row[1],
            name=row[2],
            credit=to_float(row[3]),
            hours=to_int(row[4]),
            courseType=row[5],
            dept=row[6],
            semester=row[7],
            teacherId=to_int(row[8]),
            teacherName=row[9],
            teacherTitle=row[10],
            capacity=to_int(row[11]),
            enrolledCount=to_int(row[12]),
            remaining=to_int(row[13]),
            status=row[14],
            intro=row[15],
        )

    @classmethod
    def of_selectable_row(cls, row: sqlite3.Row) -> "CourseVO":
        """11 列：id, course_code, name, credit, course_type, dept,
        teacher_name, teacher_title, capacity, enrolled_count, remaining

        这一列集没有 hours / semester / teacher_id / intro，
        `status` 由 Service 强制为 `OPEN`（SQL 里已按 OPEN 过滤）。
        """
        return cls(
            id=row[0],
            courseCode=row[1],
            name=row[2],
            credit=to_float(row[3]),
            courseType=row[4],
            dept=row[5],
            teacherName=row[6],
            teacherTitle=row[7],
            capacity=to_int(row[8]),
            enrolledCount=to_int(row[9]),
            remaining=to_int(row[10]),
            status="OPEN",
        )

    @classmethod
    def of_conflict_row(cls, row: sqlite3.Row) -> "CourseVO":
        """4 列：id, course_code, name, conflict_with"""
        return cls(
            id=row[0],
            courseCode=row[1],
            name=row[2],
            conflictWith=row[3],
        )
