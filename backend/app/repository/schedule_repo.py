"""上课时间仓储。对标参考项目的 `CourseScheduleRepository`。"""

from __future__ import annotations

import sqlite3
from typing import Any


def find_by_course(conn: sqlite3.Connection, course_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT cs.id, cs.course_id, c.name AS course_name,
                  cs.weekday, cs.start_section, cs.end_section,
                  cs.start_week, cs.end_week, cs.classroom
             FROM course_schedule cs
             JOIN course c ON c.id = cs.course_id
            WHERE cs.course_id = ?
            ORDER BY cs.weekday, cs.start_section""",
        (course_id,),
    ).fetchall()


def find_by_id(conn: sqlite3.Connection, schedule_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM course_schedule WHERE id = ?", (schedule_id,)).fetchone()


def count_teacher_conflict(
    conn: sqlite3.Connection,
    *,
    teacher_id: int,
    semester: str,
    weekday: int,
    start_section: int,
    end_section: int,
    exclude_id: int = 0,
) -> int:
    """同一教师、同一学期、同一星期，是否已存在节次区间重叠的排班。

    区间重叠公式 `A.start <= B.end AND B.start <= A.end`。
    新增时 `exclude_id` 传 0，修改时传自身 id 以排除自己。
    """
    row = conn.execute(
        """SELECT EXISTS (
               SELECT 1
                 FROM course_schedule cs
                 JOIN course c ON c.id = cs.course_id
                WHERE c.teacher_id = :teacher_id
                  AND c.semester   = :semester
                  AND cs.weekday   = :weekday
                  AND cs.id       <> :exclude_id
                  AND cs.start_section <= :end_section
                  AND :start_section   <= cs.end_section
           )""",
        {
            "teacher_id": teacher_id,
            "semester": semester,
            "weekday": weekday,
            "start_section": start_section,
            "end_section": end_section,
            "exclude_id": exclude_id,
        },
    ).fetchone()
    return int(row[0])


def insert(conn: sqlite3.Connection, data: dict[str, Any]) -> int:
    cur = conn.execute(
        """INSERT INTO course_schedule
               (course_id, weekday, start_section, end_section, start_week, end_week, classroom)
           VALUES (:course_id, :weekday, :start_section, :end_section,
                   :start_week, :end_week, :classroom)""",
        data,
    )
    return int(cur.lastrowid)


def update(conn: sqlite3.Connection, schedule_id: int, data: dict[str, Any]) -> int:
    return conn.execute(
        """UPDATE course_schedule
              SET course_id = :course_id, weekday = :weekday,
                  start_section = :start_section, end_section = :end_section,
                  start_week = :start_week, end_week = :end_week, classroom = :classroom
            WHERE id = :id""",
        {**data, "id": schedule_id},
    ).rowcount


def delete(conn: sqlite3.Connection, schedule_id: int) -> int:
    return conn.execute("DELETE FROM course_schedule WHERE id = ?", (schedule_id,)).rowcount


def delete_by_course(conn: sqlite3.Connection, course_id: int) -> int:
    """删课程前必须先删它的上课时间（外键 RESTRICT）。"""
    return conn.execute("DELETE FROM course_schedule WHERE course_id = ?", (course_id,)).rowcount
