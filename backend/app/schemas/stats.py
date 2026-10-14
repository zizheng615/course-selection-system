"""统计报表 VO。对标参考项目的 `vo/PopularCourseVO`、`MajorStatVO`、`TeacherWorkloadVO`。"""

from __future__ import annotations

import sqlite3

from ..common.convert import to_float, to_int
from ._base import VO


class PopularCourseVO(VO):
    courseCode: str | None = None
    courseName: str | None = None
    teacherName: str | None = None
    capacity: int | None = None
    selectedCount: int | None = None
    #: 百分比，如 83.3
    fillRate: float | None = None

    @classmethod
    def of_row(cls, row: sqlite3.Row) -> "PopularCourseVO":
        """6 列：course_code, course_name, teacher_name, capacity, selected_count, fill_rate"""
        return cls(
            courseCode=row[0], courseName=row[1], teacherName=row[2],
            capacity=to_int(row[3]), selectedCount=to_int(row[4]), fillRate=to_float(row[5]),
        )


class MajorStatVO(VO):
    major: str | None = None
    studentCount: int | None = None
    enrollmentCount: int | None = None
    avgCoursesPerStudent: float | None = None

    @classmethod
    def of_row(cls, row: sqlite3.Row) -> "MajorStatVO":
        """4 列：major, student_count, enrollment_count, avg_courses_per_student"""
        return cls(
            major=row[0], studentCount=to_int(row[1]),
            enrollmentCount=to_int(row[2]), avgCoursesPerStudent=to_float(row[3]),
        )


class TeacherWorkloadVO(VO):
    teacherName: str | None = None
    title: str | None = None
    dept: str | None = None
    courseCount: int | None = None
    totalStudents: int | None = None
    totalCredit: float | None = None

    @classmethod
    def of_row(cls, row: sqlite3.Row) -> "TeacherWorkloadVO":
        """6 列：name, title, dept, course_count, total_students, total_credit"""
        return cls(
            teacherName=row[0], title=row[1], dept=row[2],
            courseCount=to_int(row[3]), totalStudents=to_int(row[4]), totalCredit=to_float(row[5]),
        )
