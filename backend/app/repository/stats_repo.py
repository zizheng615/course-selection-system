"""统计报表仓储。对标参考项目的 `StatsRepository` —— 只承载查询，不含增删改。

**SQLite 方言适配（关键）**：MySQL 的 `COUNT(x) / c.capacity` 会自动做小数除法，
SQLite 对两个 INTEGER 做的是**整除**（`5/60 = 0`），满座率会全变 0。
因此这里把分子乘上 `100.0` / `1.0` 强制提升为浮点，语义与 MySQL 一致。
"""

from __future__ import annotations

import sqlite3


def find_popular_courses(conn: sqlite3.Connection, semester: str, limit: int) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT c.course_code,
                  c.name       AS course_name,
                  t.name       AS teacher_name,
                  c.capacity,
                  COUNT(e.id)  AS selected_count,
                  ROUND(COUNT(e.id) * 100.0 / c.capacity, 1) AS fill_rate
             FROM course c
             JOIN teacher t         ON t.id = c.teacher_id
             LEFT JOIN enrollment e ON e.course_id = c.id AND e.status = 'SELECTED'
            WHERE c.semester = :semester
            GROUP BY c.id, c.course_code, c.name, t.name, c.capacity
            ORDER BY selected_count DESC, c.id
            LIMIT :limit""",
        {"semester": semester, "limit": limit},
    ).fetchall()


def find_major_distribution(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """LEFT JOIN 保证「没有选课记录的专业」也出现在结果里，避免统计口径漏项。"""
    return conn.execute(
        """SELECT s.major,
                  COUNT(DISTINCT s.id) AS student_count,
                  COUNT(e.id)          AS enrollment_count,
                  ROUND(COUNT(e.id) * 1.0 / COUNT(DISTINCT s.id), 2) AS avg_courses_per_student
             FROM student s
             LEFT JOIN enrollment e ON e.student_id = s.id AND e.status = 'SELECTED'
            GROUP BY s.major
            ORDER BY enrollment_count DESC"""
    ).fetchall()


def find_teacher_workload(conn: sqlite3.Connection, semester: str) -> list[sqlite3.Row]:
    """LEFT JOIN 保证「没有课的教师」也会出现（显示为 0）。"""
    return conn.execute(
        """SELECT t.name,
                  t.title,
                  t.dept,
                  COUNT(DISTINCT c.id)             AS course_count,
                  IFNULL(SUM(c.enrolled_count), 0) AS total_students,
                  IFNULL(SUM(c.credit), 0)         AS total_credit
             FROM teacher t
             LEFT JOIN course c ON c.teacher_id = t.id AND c.semester = :semester
            GROUP BY t.id, t.name, t.title, t.dept
            ORDER BY total_students DESC""",
        {"semester": semester},
    ).fetchall()
