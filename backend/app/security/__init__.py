"""认证与授权：JWT 签发解析、身份载体、声明式角色依赖。"""

from .context import ROLE_ADMIN, ROLE_NAMES, ROLE_STUDENT, ROLE_TEACHER, UserContext
from .deps import (
    AdminOnly,
    CurrentUser,
    StudentOnly,
    TeacherOnly,
    TeacherOrAdmin,
    authenticate,
    require_role,
)
from .jwt_util import TokenError, create_token, extract_bearer, parse_token

__all__ = [
    "UserContext",
    "ROLE_ADMIN",
    "ROLE_TEACHER",
    "ROLE_STUDENT",
    "ROLE_NAMES",
    "create_token",
    "parse_token",
    "extract_bearer",
    "TokenError",
    "authenticate",
    "require_role",
    "CurrentUser",
    "AdminOnly",
    "TeacherOnly",
    "StudentOnly",
    "TeacherOrAdmin",
]
