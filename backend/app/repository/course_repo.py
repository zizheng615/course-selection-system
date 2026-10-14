"""课程仓储。SQL 逐条对标参考项目的 `CourseRepository`。

**条件参数统一由 Service 归一化为「空字符串」而非 None**，于是 SQL 里可以写
`:semester = '' OR c.semester = :semester` 这种简单比较，避开 NULL 的三值逻辑陷阱。
（`courseId` 用 `0` 表示「不限」，同理。）

MySQL -> SQLite 的方言改动只有两处：
`CONCAT('%', x, '%')` -> `'%' || :x || '%'`。
"""

from __future__ import annotations

import sqlite3
from typing import Any, Sequence

# 课程列表的 16 列，顺序必须与 CourseVO.of_list_row 的下标一致
LIST_COLUMNS = """c.id,
       c.course_code,
       c.name,
       c.credit,
       c.hours,
       c.course_type,
       c.dept,
       c.semester,
       c.teacher_id,
       t.name  AS teacher_name,
       t.title AS teacher_title,
       c.capacity,
       c.enrolled_count,
       (c.capacity - c.enrolled_count) AS remaining,
       c.status,
       c.intro"""

# 可选课程的 11 列，顺序必须与 CourseVO.of_selectable_row 的下标一致
SELECTABLE_COLUMNS = """c.id,
       c.course_code,
       c.name,
       c.credit,
       c.course_type,
       c.dept,
       t.name  AS teacher_name,
       t.title AS teacher_title,
       c.capacity,
       c.enrolled_count,
       (c.capacity - c.enrolled_count) AS remaining"""

_SEARCH_FILTER = """(:semester = '' OR c.semester = :semester)
   AND (:status   = '' OR c.status   = :status)
   AND (:keyword  = '' OR c.name LIKE '%' || :keyword || '%'
                       OR c.course_code LIKE '%' || :keyword || '%')"""


# --------------------------------------------------------------------------
# 单条读写
# --------------------------------------------------------------------------

def find_by_id(conn: sqlite3.Connection, course_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM course WHERE id = ?", (course_id,)).fetchone()


def find_detail_by_id(conn: sqlite3.Connection, course_id: int) -> sqlite3.Row | None:
    """课程详情（带教师姓名/职称与剩余容量），走 v_course_detail 视图。"""
    return conn.execute(
        """SELECT id, course_code, name, credit, hours, course_type, dept, semester,
                  teacher_id, teacher_name, teacher_title, capacity, enrolled_count,
                  remaining, status, intro
             FROM v_course_detail WHERE id = ?""",
        (course_id,),
    ).fetchone()


def find_by_code_and_semester(conn: sqlite3.Connection, course_code: str, semester: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM course WHERE course_code = ? AND semester = ?",
        (course_code, semester),
    ).fetchone()


def exists_by_code_and_semester(conn: sqlite3.Connection, course_code: str, semester: str) -> bool:
    return find_by_code_and_semester(conn, course_code, semester) is not None


def find_distinct_semesters(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT DISTINCT semester FROM course ORDER BY semester DESC").fetchall()
    return [r["semester"] for r in rows]


def find_by_teacher(conn: sqlite3.Connection, teacher_id: int, semester: str = "") -> list[sqlite3.Row]:
    return conn.execute(
        f"""SELECT {LIST_COLUMNS}
              FROM course c
              JOIN teacher t ON t.id = c.teacher_id
             WHERE c.teacher_id = :teacher_id
               AND (:semester = '' OR c.semester = :semester)
             ORDER BY c.id""",
        {"teacher_id": teacher_id, "semester": semester},
    ).fetchall()


def count_by_teacher(conn: sqlite3.Connection, teacher_id: int) -> int:
    row = conn.execute("SELECT COUNT(*) FROM course WHERE teacher_id = ?", (teacher_id,)).fetchone()
    return int(row[0])


# --------------------------------------------------------------------------
# 分页查询
# --------------------------------------------------------------------------

def search_courses(
    conn: sqlite3.Connection,
    *,
    keyword: str = "",
    semester: str = "",
    status: str = "",
    page: int = 1,
    size: int = 10,
) -> tuple[list[sqlite3.Row], int]:
    params = {"keyword": keyword, "semester": semester, "status": status}
    total = int(
        conn.execute(f"SELECT COUNT(*) FROM course c WHERE {_SEARCH_FILTER}", params).fetchone()[0]
    )
    rows = conn.execute(
        f"""SELECT {LIST_COLUMNS}
              FROM course c
              JOIN teacher t ON t.id = c.teacher_id
             WHERE {_SEARCH_FILTER}
             ORDER BY c.id
             LIMIT :size OFFSET :offset""",
        {**params, "size": size, "offset": (page - 1) * size},
    ).fetchall()
    return rows, total


# --------------------------------------------------------------------------
# 可选课程 / 冲突课程（时间冲突核心，逻辑必须与 enrollment_repo.count_time_conflict 一致）
# --------------------------------------------------------------------------

def find_selectable_courses(conn: sqlite3.Connection, student_id: int, semester: str) -> list[sqlite3.Row]:
    """可选课程：排除已选过的、且与已选课程时间不冲突的课程。

    时间冲突判定采用区间重叠公式 `A.start <= B.end AND B.start <= A.end`，
    节次与周次两个维度都要满足。整个判定在 SQL 内完成，
    不把学生课表捞到应用内存里循环比较。
    """
    return conn.execute(
        f"""SELECT {SELECTABLE_COLUMNS}
              FROM course c
              JOIN teacher t ON t.id = c.teacher_id
             WHERE c.semester = :semester
               AND c.status   = 'OPEN'
               AND c.enrolled_count < c.capacity
               AND NOT EXISTS (
                     SELECT 1 FROM enrollment e
                      WHERE e.student_id = :student_id
                        AND e.course_id  = c.id
                        AND e.status     = 'SELECTED'
                   )
               AND NOT EXISTS (
                     SELECT 1
                       FROM course_schedule cs_new
                       JOIN course_schedule cs_old ON cs_old.weekday = cs_new.weekday
                       JOIN enrollment e2
                            ON e2.course_id  = cs_old.course_id
                           AND e2.student_id = :student_id
                           AND e2.status     = 'SELECTED'
                      WHERE cs_new.course_id = c.id
                        AND cs_new.start_section <= cs_old.end_section
                        AND cs_old.start_section <= cs_new.end_section
                        AND cs_new.start_week    <= cs_old.end_week
                        AND cs_old.start_week    <= cs_new.end_week
                   )
             ORDER BY remaining DESC, c.id""",
        {"student_id": student_id, "semester": semester},
    ).fetchall()


def find_conflicting_courses(conn: sqlite3.Connection, student_id: int, semester: str) -> list[sqlite3.Row]:
    """反查与该学生已选课程真正冲突的课程（前端据此解释「为什么这门课选不了」）。

    必须排除「学生已选中的课程本身」：区间重叠判定中，一门课的课表与它自己的课表
    必然满足重叠公式，不排除的话每门已选课都会作为「与自己冲突」出现在结果里。
    """
    return conn.execute(
        """SELECT DISTINCT
                  c.id,
                  c.course_code,
                  c.name,
                  old_c.name AS conflict_with
             FROM course c
             JOIN course_schedule cs_new ON cs_new.course_id = c.id
             JOIN course_schedule cs_old ON cs_old.weekday    = cs_new.weekday
             JOIN enrollment e2
                  ON e2.course_id  = cs_old.course_id
                 AND e2.student_id = :student_id
                 AND e2.status     = 'SELECTED'
             JOIN course old_c ON old_c.id = cs_old.course_id
            WHERE c.semester = :semester
              AND cs_new.start_section <= cs_old.end_section
              AND cs_old.start_section <= cs_new.end_section
              AND cs_new.start_week    <= cs_old.end_week
              AND cs_old.start_week    <= cs_new.end_week
              AND NOT EXISTS (
                    SELECT 1 FROM enrollment e3
                     WHERE e3.student_id = :student_id
                       AND e3.course_id  = c.id
                       AND e3.status     = 'SELECTED'
                  )""",
        {"student_id": student_id, "semester": semester},
    ).fetchall()


# --------------------------------------------------------------------------
# 容量增减：项目核心，改动前务必理解
# --------------------------------------------------------------------------

def increase_enrolled_count(conn: sqlite3.Connection, course_id: int) -> int:
    """原子占用一个名额，返回影响行数（1 = 抢到，0 = 已满/已关闭）。

    把「判断 + 扣减」压进一条 UPDATE。**不要改回「先 SELECT 查余量再 UPDATE」**，
    那样并发下会有多个事务读到同一余量值而超卖。
    """
    cur = conn.execute(
        """UPDATE course
              SET enrolled_count = enrolled_count + 1
            WHERE id = :id AND status = 'OPEN' AND enrolled_count < capacity""",
        {"id": course_id},
    )
    return cur.rowcount


def decrease_enrolled_count(conn: sqlite3.Connection, course_id: int) -> int:
    """原子归还一个名额，返回影响行数（0 表示计数已为 0，调用方必须回滚）。"""
    cur = conn.execute(
        "UPDATE course SET enrolled_count = enrolled_count - 1 WHERE id = :id AND enrolled_count > 0",
        {"id": course_id},
    )
    return cur.rowcount


# --------------------------------------------------------------------------
# 写操作
# --------------------------------------------------------------------------

def insert(conn: sqlite3.Connection, data: dict[str, Any]) -> int:
    cur = conn.execute(
        """INSERT INTO course (course_code, name, credit, hours, course_type, dept, semester,
                               teacher_id, capacity, enrolled_count, status, intro)
           VALUES (:course_code, :name, :credit, :hours, :course_type, :dept, :semester,
                   :teacher_id, :capacity, 0, :status, :intro)""",
        data,
    )
    return int(cur.lastrowid)


def update(conn: sqlite3.Connection, course_id: int, data: dict[str, Any]) -> int:
    cur = conn.execute(
        """UPDATE course
              SET course_code = :course_code, name = :name, credit = :credit, hours = :hours,
                  course_type = :course_type, dept = :dept, semester = :semester,
                  teacher_id = :teacher_id, capacity = :capacity, status = :status,
                  intro = :intro
            WHERE id = :id""",
        {**data, "id": course_id},
    )
    return cur.rowcount


def update_status(conn: sqlite3.Connection, course_id: int, status: str) -> int:
    return conn.execute(
        "UPDATE course SET status = ? WHERE id = ?", (status, course_id)
    ).rowcount


def delete(conn: sqlite3.Connection, course_id: int) -> int:
    return conn.execute("DELETE FROM course WHERE id = ?", (course_id,)).rowcount


def count_enrollments(conn: sqlite3.Connection, course_id: int) -> int:
    """该课程的全部选课记录数（**含已退课**）。删课程前的引用检查就靠它。"""
    return int(conn.execute("SELECT COUNT(*) FROM enrollment WHERE course_id = ?", (course_id,)).fetchone()[0])
