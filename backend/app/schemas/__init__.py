"""DTO（入参校验）与 VO（出参映射）。

命名刻意使用 camelCase：字段名就是对前端的契约，与参考项目的 Java 字段名逐字一致。
"""

from ._base import DTO, VO
from .ai import AiChatDTO, AiChatVO
from .auth import LoginDTO, LoginVO
from .course import CourseDTO, CourseVO
from .enrollment import (
    AdminEnrollDTO,
    CourseStudentVO,
    EnrollmentRecordVO,
    MyCourseVO,
    ScoreDTO,
    SelectCourseDTO,
    TimetableVO,
)
from .person import StudentDTO, StudentVO, TeacherDTO, TeacherVO
from .schedule import ScheduleDTO, ScheduleVO
from .stats import MajorStatVO, PopularCourseVO, TeacherWorkloadVO
from .user import UserCredentialDTO, UserVO

__all__ = [
    "DTO",
    "VO",
    "AiChatDTO",
    "AiChatVO",
    "LoginDTO",
    "LoginVO",
    "CourseDTO",
    "CourseVO",
    "ScheduleDTO",
    "ScheduleVO",
    "StudentDTO",
    "StudentVO",
    "TeacherDTO",
    "TeacherVO",
    "UserCredentialDTO",
    "UserVO",
    "SelectCourseDTO",
    "AdminEnrollDTO",
    "ScoreDTO",
    "MyCourseVO",
    "TimetableVO",
    "CourseStudentVO",
    "EnrollmentRecordVO",
    "PopularCourseVO",
    "MajorStatVO",
    "TeacherWorkloadVO",
]
