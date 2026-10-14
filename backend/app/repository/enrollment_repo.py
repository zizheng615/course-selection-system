"""选课记录仓储。SQL 逐条对标参考项目的 `EnrollmentRepository`。

三处「区间重叠」判定中的一处在这里（`count_time_conflict`），
另外两处在 `course_repo.find_selectable_courses` / `find_conflicting_courses`。
**三处逻辑必须保持一致**，改动时一起改。
"""

from __future__ import annotations

import sqlite3

_SEARCH_FILTER = """(:keyword = ''
        OR s.name        LIKE '%' || :keyword || '%'
        OR s.student_no  LIKE '%' || :keyword || '%'
        OR c.name        LIKE '%' || :keyword || '%'
        OR c.course_code LIKE '%' || :keyword || '%')
   AND (:course_id = 0 OR c.id = :course_id)
   AND (:status = '' OR e.status = :status)"""


def find_by_id(conn: sqlite3.Connection, enrollment_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM enrollment WHERE id = ?", (enrollment_id,)).fetchone()


def find_by_student_and_course(
    conn: sqlite3.Connection, student_id: int, course_id: int
) -> sqlite3.Row | None:
    """因为 uk_student_course 唯一索引，这个组合最多只会有一行（可能是 WITHDRAWN）。"""
    return conn.execute(
        "SELECT * FROM enrollment WHERE student_id = ? AND course_id = ?",
        (student_id, course_id),
    ).fetchone()


def count_by_course(conn: sqlite3.Connection, course_id: int) -> int:
    """该课程全部记录数（含已退课）—— 删除前的引用检查。"""
    return int(conn.execute("SELECT COUNT(*) FROM enrollment WHERE course_id = ?", (course_id,)).fetchone()[0])


def count_by_student(conn: sqlite3.Connection, student_id: int) -> int:
    """该学生全部记录数（含已退课）—— 保留修读记录，所以退课也算引用。"""
    return int(conn.execute("SELECT COUNT(*) FROM enrollment WHERE student_id = ?", (student_id,)).fetchone()[0])


# --------------------------------------------------------------------------
# 时间冲突（核心）
# --------------------------------------------------------------------------

def count_time_conflict(conn: sqlite3.Connection, student_id: int, course_id: int) -> int:
    """该学生已选课程中是否存在与目标课程时间重叠的课程。1 = 冲突。

    `cs_old.course_id <> :course_id` 用于自我排除：重复选课的判定由调用方
    单独负责（错误码 4002），不能混进冲突判定（否则会误报 4003）。
    """
    row = conn.execute(
        """SELECT EXISTS (
               SELECT 1
                 FROM course_schedule cs_new
                 JOIN course_schedule cs_old ON cs_old.weekday = cs_new.weekday
                 JOIN enrollment e2
                      ON e2.course_id  = cs_old.course_id
                     AND e2.student_id = :student_id
                     AND e2.status     = 'SELECTED'
                WHERE cs_new.course_id = :course_id
                  AND cs_old.course_id <> :course_id
                  AND cs_new.start_section <= cs_old.end_section
                  AND cs_old.start_section <= cs_new.end_section
                  AND cs_new.start_week    <= cs_old.end_week
                  AND cs_old.start_week    <= cs_new.end_week
           )""",
        {"student_id": student_id, "course_id": course_id},
    ).fetchone()
    return int(row[0])


# --------------------------------------------------------------------------
# 查询
# --------------------------------------------------------------------------

def find_timetable(conn: sqlite3.Connection, student_id: int, semester: str) -> list[sqlite3.Row]:
    """个人课表（12 列）：选课记录 + 课程 + 教师 + 上课时间四表连接。"""
    return conn.execute(
        """SELECT c.id            AS course_id,
                  c.course_code,
                  c.name          AS course_name,
                  c.credit,
                  c.course_type,
                  t.name          AS teacher_name,
                  cs.weekday,
                  cs.start_section,
                  cs.end_section,
                  cs.start_week,
                  cs.end_week,
                  cs.classroom
             FROM enrollment e
             JOIN course c           ON c.id  = e.course_id
             JOIN teacher t          ON t.id  = c.teacher_id
             JOIN course_schedule cs ON cs.course_id = c.id
            WHERE e.student_id = :student_id
              AND e.status     = 'SELECTED'
              AND c.semester   = :semester
            ORDER BY cs.weekday, cs.start_section""",
        {"student_id": student_id, "semester": semester},
    ).fetchall()


def find_my_courses(conn: sqlite3.Connection, student_id: int, semester: str) -> list[sqlite3.Row]:
    """我的课程（11 列，含成绩）。"""
    return conn.execute(
        """SELECT e.id            AS enrollment_id,
                  c.id            AS course_id,
                  c.course_code,
                  c.name          AS course_name,
                  c.credit,
                  c.course_type,
                  c.semester,
                  t.name          AS teacher_name,
                  e.status,
                  e.score,
                  e.selected_at
             FROM enrollment e
             JOIN course c  ON c.id = e.course_id
             JOIN teacher t ON t.id = c.teacher_id
            WHERE e.student_id = :student_id
              AND e.status     = 'SELECTED'
              AND (:semester = '' OR c.semester = :semester)
            ORDER BY c.id""",
        {"student_id": student_id, "semester": semester},
    ).fetchall()


def find_course_students(conn: sqlite3.Connection, course_id: int) -> list[sqlite3.Row]:
    """课程学生名单（7 列）。score 用 -1 作「未录入」哨兵（chk_score 保证真成绩 >= 0）。"""
    return conn.execute(
        """SELECT e.id AS enrollment_id,
                  s.id AS student_id,
                  s.student_no,
                  s.name AS student_name,
                  s.major,
                  s.grade,
                  IFNULL(e.score, -1) AS score
             FROM enrollment e
             JOIN student s ON s.id = e.student_id
            WHERE e.course_id = :course_id
              AND e.status    = 'SELECTED'
            ORDER BY s.student_no""",
        {"course_id": course_id},
    ).fetchall()


def search_enrollments(
    conn: sqlite3.Connection,
    *,
    keyword: str = "",
    course_id: int = 0,
    status: str = "",
    page: int = 1,
    size: int = 10,
) -> tuple[list[sqlite3.Row], int]:
    """选课记录管理（13 列）。

    score **不做 IFNULL** —— 保持 null 语义，前端据此显示「未录入」。
    """
    params = {"keyword": keyword, "course_id": course_id, "status": status}
    total = int(
        conn.execute(
            f"""SELECT COUNT(*)
                  FROM enrollment e
                  JOIN student s ON s.id = e.student_id
                  JOIN course  c ON c.id = e.course_id
                 WHERE {_SEARCH_FILTER}""",
            params,
        ).fetchone()[0]
    )
    rows = conn.execute(
        f"""SELECT e.id,
                   s.id,
                   s.student_no,
                   s.name AS student_name,
                   s.major,
                   c.id,
                   c.course_code,
                   c.name AS course_name,
                   t.name AS teacher_name,
                   c.semester,
                   e.status,
                   e.score,
                   e.selected_at
              FROM enrollment e
              JOIN student s ON s.id = e.student_id
              JOIN course  c ON c.id = e.course_id
              JOIN teacher t ON t.id = c.teacher_id
             WHERE {_SEARCH_FILTER}
             ORDER BY e.id DESC
             LIMIT :size OFFSET :offset""",
        {**params, "size": size, "offset": (page - 1) * size},
    ).fetchall()
    return rows, total


# --------------------------------------------------------------------------
# 写操作
# --------------------------------------------------------------------------

def insert(conn: sqlite3.Connection, student_id: int, course_id: int) -> int:
    cur = conn.execute(
        "INSERT INTO enrollment (student_id, course_id, status) VALUES (?, ?, 'SELECTED')",
        (student_id, course_id),
    )
    return int(cur.lastrowid)


def reactivate(conn: sqlite3.Connection, enrollment_id: int) -> int:
    """复用原记录重新选课，并清空旧成绩。

    退课是「置 WITHDRAWN 而非删行」，加上 uk_student_course 唯一索引的存在，
    重新选课**必须复用原记录**，否则会撞唯一索引。
    """
    return conn.execute(
        "UPDATE enrollment SET status = 'SELECTED', score = NULL, selected_at = datetime('now','localtime') WHERE id = ?",
        (enrollment_id,),
    ).rowcount


def withdraw(conn: sqlite3.Connection, enrollment_id: int) -> int:
    """软退课：保留修读历史。"""
    return conn.execute(
        "UPDATE enrollment SET status = 'WITHDRAWN' WHERE id = ?", (enrollment_id,)
    ).rowcount


def update_score(conn: sqlite3.Connection, enrollment_id: int, score: float) -> int:
    return conn.execute(
        "UPDATE enrollment SET score = ? WHERE id = ?", (score, enrollment_id)
    ).rowcount


def delete(conn: sqlite3.Connection, enrollment_id: int) -> int:
    return conn.execute("DELETE FROM enrollment WHERE id = ?", (enrollment_id,)).rowcount
