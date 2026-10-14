"""选课服务 —— 本项目的核心。对标参考项目的 `service/EnrollmentService`。

=====================================================================
 并发选课：把「判断 + 扣减」压进一条原子 UPDATE
=====================================================================

    UPDATE course SET enrolled_count = enrolled_count + 1
     WHERE id = ? AND status = 'OPEN' AND enrolled_count < capacity

调用方**只看影响行数**（1 = 抢到，0 = 已满）。

**不要改回「先 SELECT 查余量再 UPDATE」**，那样会有多个事务读到同一余量值而超卖。
SQLite 侧的配套措施：写事务从 `BEGIN IMMEDIATE` 开始（见 `db.transaction`），
在事务起点就取写锁，配合 `busy_timeout` 让并发写串行化 ——
这正是参考项目靠 InnoDB 行锁拿到的效果。

配套约束，改动时不能丢：
  * 退课归还容量返回 0 时**抛异常回滚**，避免留下「退课成功但计数没还」的脏状态
  * 退课是置 `WITHDRAWN` 而非删行；因为 `uk_student_course` 唯一索引的存在，
    重新选课**必须复用原记录**，否则撞索引（`existing` 分支就是干这个的）

=====================================================================
 时间冲突：区间重叠
=====================================================================

判定公式 `A.start <= B.end AND B.start <= A.end`，节次与周次两个维度都要判。
三处使用，逻辑必须保持一致：

    ==============================================  ==========================
    位置                                             用途
    ==============================================  ==========================
    `course_repo.find_selectable_courses`            可选课程列表（已排除）
    `course_repo.find_conflicting_courses`           反查冲突，供前端提示
    `enrollment_repo.count_time_conflict`            选课时校验
    ==============================================  ==========================
"""

from __future__ import annotations

from .. import db
from ..common.errors import BusinessException, ErrorCode
from ..common.result import normalize_page, page
from ..repository import course_repo, enrollment_repo, student_repo
from ..schemas.course import CourseVO
from ..schemas.enrollment import (
    CourseStudentVO,
    EnrollmentRecordVO,
    MyCourseVO,
    TimetableVO,
)
from . import semester_resolver

# --------------------------------------------------------------------------
# 选课 / 退课
# --------------------------------------------------------------------------

def select_course(student_id: int, course_id: int) -> None:
    """学生选课。管理员代选课复用本函数（见 `admin_enroll`）。"""
    with db.transaction() as conn:
        course = course_repo.find_by_id(conn, course_id)
        if course is None:
            raise BusinessException(ErrorCode.NOT_FOUND, "课程不存在")
        if str(course["status"]) != "OPEN":
            raise BusinessException(ErrorCode.COURSE_CLOSED, "该课程未开放选课")

        existing = enrollment_repo.find_by_student_and_course(conn, student_id, course_id)
        if existing is not None and str(existing["status"]) == "SELECTED":
            raise BusinessException(ErrorCode.ALREADY_SELECTED, "已选过该课程，请勿重复选课")

        if enrollment_repo.count_time_conflict(conn, student_id, course_id) > 0:
            raise BusinessException(
                ErrorCode.TIME_CONFLICT, "该课程与已选课程上课时间冲突，无法选课"
            )

        # 原子占位：这一条 UPDATE 同时承担了「还有没有名额」和「扣减」两件事
        if course_repo.increase_enrolled_count(conn, course_id) == 0:
            raise BusinessException(ErrorCode.COURSE_FULL, "课程容量已满或已关闭，选课失败")

        if existing is not None:
            # 退课过又重选：复用原记录（唯一索引不允许插新行），并清空旧成绩
            enrollment_repo.reactivate(conn, int(existing["id"]))
        else:
            enrollment_repo.insert(conn, student_id, course_id)


def withdraw_course(student_id: int, course_id: int) -> None:
    """学生退课（软退课）。"""
    with db.transaction() as conn:
        row = enrollment_repo.find_by_student_and_course(conn, student_id, course_id)
        if row is None or str(row["status"]) != "SELECTED":
            raise BusinessException(ErrorCode.NOT_SELECTED, "未选该课程或已退课")

        enrollment_repo.withdraw(conn, int(row["id"]))
        # 归还失败说明计数已经乱了；抛异常让整个事务回滚，
        # 宁可退课失败，也不要留下「退了课但名额没还」的脏状态
        if course_repo.decrease_enrolled_count(conn, course_id) == 0:
            raise BusinessException(ErrorCode.SYSTEM_ERROR, "课程容量计数异常，退课已回滚")


# --------------------------------------------------------------------------
# 学生端查询
# --------------------------------------------------------------------------

def my_courses(student_id: int, semester: str | None = None) -> list[MyCourseVO]:
    conn = db.connection()
    rows = enrollment_repo.find_my_courses(conn, student_id, (semester or "").strip())
    return [MyCourseVO.of_row(r) for r in rows]


def my_timetable(student_id: int, semester: str | None = None) -> list[TimetableVO]:
    conn = db.connection()
    rows = enrollment_repo.find_timetable(conn, student_id, semester_resolver.resolve(conn, semester))
    return [TimetableVO.of_row(r) for r in rows]


def available_courses(student_id: int, semester: str | None = None) -> list[CourseVO]:
    """可选课程：SQL 内已排除「已选过」与「时间冲突」两类。"""
    conn = db.connection()
    rows = course_repo.find_selectable_courses(conn, student_id, semester_resolver.resolve(conn, semester))
    return [CourseVO.of_selectable_row(r) for r in rows]


def conflicting_courses(student_id: int, semester: str | None = None) -> list[CourseVO]:
    """反查与该学生已选课程真正冲突的课程，供前端解释「为什么这门课选不了」。"""
    conn = db.connection()
    rows = course_repo.find_conflicting_courses(conn, student_id, semester_resolver.resolve(conn, semester))
    return [CourseVO.of_conflict_row(r) for r in rows]


# --------------------------------------------------------------------------
# 教师 / 管理员：名单与成绩
# --------------------------------------------------------------------------

def course_students(course_id: int) -> list[CourseStudentVO]:
    if course_repo.find_by_id(db.connection(), course_id) is None:
        raise BusinessException(ErrorCode.NOT_FOUND, "课程不存在")
    rows = enrollment_repo.find_course_students(db.connection(), course_id)
    return [CourseStudentVO.of_row(r) for r in rows]


def record_score(enrollment_id: int, score: float) -> None:
    with db.transaction() as conn:
        row = enrollment_repo.find_by_id(conn, enrollment_id)
        if row is None:
            raise BusinessException(ErrorCode.NOT_FOUND, "选课记录不存在")
        if str(row["status"]) != "SELECTED":
            raise BusinessException(ErrorCode.NOT_SELECTED, "该学生已退课，无法录入成绩")
        enrollment_repo.update_score(conn, enrollment_id, score)


# --------------------------------------------------------------------------
# 管理员：选课记录管理
# --------------------------------------------------------------------------

def search_enrollments(
    *, keyword: str | None = None, course_id: int | None = None, status: str | None = None,
    page_no: int | None = None, size: int | None = None,
) -> dict:
    p, s = normalize_page(page_no, size)
    rows, total = enrollment_repo.search_enrollments(
        db.connection(),
        keyword=(keyword or "").strip(),
        # courseId 用 0 表示「不限」，与文本参数的空串归一化同一套约定
        course_id=course_id or 0,
        status=(status or "").strip(),
        page=p,
        size=s,
    )
    return page([EnrollmentRecordVO.of_row(r) for r in rows], total, p, s)


def admin_enroll(student_id: int, course_id: int) -> None:
    """管理员代学生选课。

    **刻意复用 `select_course`，不另写一套「管理员专用」校验** ——
    容量、时间冲突、重复选课这三类不变式必须只有一处实现，
    否则两个入口的规则会逐渐漂移。
    这里只多一步：确认学生确实存在。
    """
    if student_repo.find_by_id(db.connection(), student_id) is None:
        raise BusinessException(ErrorCode.NOT_FOUND, "学生不存在")
    select_course(student_id, course_id)


def admin_withdraw(enrollment_id: int) -> None:
    """管理员软退课：保留修读历史。"""
    with db.transaction() as conn:
        row = enrollment_repo.find_by_id(conn, enrollment_id)
        if row is None:
            raise BusinessException(ErrorCode.NOT_FOUND, "选课记录不存在")
        if str(row["status"]) != "SELECTED":
            raise BusinessException(ErrorCode.NOT_SELECTED, "该记录已是退课状态")

        enrollment_repo.withdraw(conn, enrollment_id)
        if course_repo.decrease_enrolled_count(conn, int(row["course_id"])) == 0:
            raise BusinessException(ErrorCode.SYSTEM_ERROR, "课程容量计数异常，退课已回滚")


def admin_delete(enrollment_id: int) -> None:
    """管理员硬删记录。若原本是已选状态，必须同步归还容量。"""
    with db.transaction() as conn:
        row = enrollment_repo.find_by_id(conn, enrollment_id)
        if row is None:
            raise BusinessException(ErrorCode.NOT_FOUND, "选课记录不存在")

        was_selected = str(row["status"]) == "SELECTED"
        enrollment_repo.delete(conn, enrollment_id)
        if was_selected and course_repo.decrease_enrolled_count(conn, int(row["course_id"])) == 0:
            raise BusinessException(ErrorCode.SYSTEM_ERROR, "课程容量计数异常，删除已回滚")
