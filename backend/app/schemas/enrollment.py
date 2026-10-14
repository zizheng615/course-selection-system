"""选课相关 DTO / VO。对标参考项目的 `dto/SelectCourseDTO`、`AdminEnrollDTO`、
`ScoreDTO` 与 `vo/MyCourseVO`、`TimetableVO`、`CourseStudentVO`、`EnrollmentRecordVO`。
"""

from __future__ import annotations

import sqlite3

from pydantic import Field

from ..common.convert import to_float, to_int, weekday_name
from ._base import DTO, VO


class SelectCourseDTO(DTO):
    """学生自助选课。

    学生身份一律取自 JWT，**绝不从请求体读** —— 否则任何人改个 body 就能替别人选课。
    """

    courseId: int = Field(..., ge=1)


class AdminEnrollDTO(DTO):
    studentId: int = Field(..., ge=1)
    courseId: int = Field(..., ge=1)


class ScoreDTO(DTO):
    enrollmentId: int = Field(..., ge=1)
    score: float = Field(..., ge=0, le=100)


class MyCourseVO(VO):
    enrollmentId: int
    courseId: int
    courseCode: str | None = None
    courseName: str | None = None
    credit: float | None = None
    courseType: str | None = None
    semester: str | None = None
    teacherName: str | None = None
    status: str | None = None
    #: null = 未录入成绩（不能变成 0）
    score: float | None = None
    selectedAt: str | None = None

    @classmethod
    def of_row(cls, row: sqlite3.Row) -> "MyCourseVO":
        """11 列：enrollment_id, course_id, course_code, course_name, credit,
        course_type, semester, teacher_name, status, score, selected_at"""
        return cls(
            enrollmentId=row[0], courseId=to_int(row[1]), courseCode=row[2], courseName=row[3],
            credit=to_float(row[4]), courseType=row[5], semester=row[6], teacherName=row[7],
            status=row[8], score=to_float(row[9]), selectedAt=row[10],
        )


class TimetableVO(VO):
    courseId: int
    courseCode: str | None = None
    courseName: str | None = None
    credit: float | None = None
    courseType: str | None = None
    teacherName: str | None = None
    weekday: int | None = None
    weekdayName: str | None = None
    startSection: int | None = None
    endSection: int | None = None
    startWeek: int | None = None
    endWeek: int | None = None
    classroom: str | None = None

    @classmethod
    def of_row(cls, row: sqlite3.Row) -> "TimetableVO":
        """12 列：course_id, course_code, course_name, credit, course_type,
        teacher_name, weekday, start_section, end_section, start_week, end_week, classroom"""
        return cls(
            courseId=to_int(row[0]), courseCode=row[1], courseName=row[2], credit=to_float(row[3]),
            courseType=row[4], teacherName=row[5], weekday=to_int(row[6]),
            weekdayName=weekday_name(row[6]), startSection=to_int(row[7]), endSection=to_int(row[8]),
            startWeek=to_int(row[9]), endWeek=to_int(row[10]), classroom=row[11],
        )


class CourseStudentVO(VO):
    enrollmentId: int
    studentId: int
    studentNo: str | None = None
    studentName: str | None = None
    major: str | None = None
    grade: str | None = None
    score: float | None = None

    @classmethod
    def of_row(cls, row: sqlite3.Row) -> "CourseStudentVO":
        """7 列：enrollment_id, student_id, student_no, student_name, major, grade, score

        score 用 `-1` 作「未录入」哨兵（`chk_score` 保证真成绩 >= 0），
        这里翻译回 `null`，前端据 null 显示「未录入」。
        """
        raw_score = to_float(row[6], -1.0)
        return cls(
            enrollmentId=row[0], studentId=to_int(row[1]), studentNo=row[2],
            studentName=row[3], major=row[4], grade=row[5],
            score=None if raw_score is not None and raw_score < 0 else raw_score,
        )


class EnrollmentRecordVO(VO):
    id: int
    studentId: int
    studentNo: str | None = None
    studentName: str | None = None
    major: str | None = None
    courseId: int
    courseCode: str | None = None
    courseName: str | None = None
    teacherName: str | None = None
    semester: str | None = None
    status: str | None = None
    score: float | None = None
    selectedAt: str | None = None

    @classmethod
    def of_row(cls, row: sqlite3.Row) -> "EnrollmentRecordVO":
        """13 列：e.id, s.id, s.student_no, s.student_name, s.major, c.id,
        c.course_code, c.course_name, t.teacher_name, c.semester,
        e.status, e.score, e.selected_at"""
        return cls(
            id=row[0], studentId=to_int(row[1]), studentNo=row[2], studentName=row[3],
            major=row[4], courseId=to_int(row[5]), courseCode=row[6], courseName=row[7],
            teacherName=row[8], semester=row[9], status=row[10],
            score=to_float(row[11]), selectedAt=row[12],
        )
