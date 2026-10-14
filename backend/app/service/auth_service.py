"""认证服务。对标参考项目的 `service/AuthService`。"""

from __future__ import annotations

import sqlite3

from .. import db
from ..common.errors import BusinessException, ErrorCode
from ..repository import student_repo, teacher_repo, user_repo
from ..schemas.auth import LoginDTO, LoginVO
from ..security.context import ROLE_STUDENT, ROLE_TEACHER, UserContext
from ..security.jwt_util import create_token
from ..security.password import verify_password

#: 账号不存在与密码错误**必须返回同一句话**，否则接口变成账号枚举器：
#: 攻击者可以据此判断某个学号是否已注册，进而针对性爆破。
_LOGIN_FAILED = "账号或密码错误"


def _resolve_ref_id(conn: sqlite3.Connection, user_id: int, role: str) -> int | None:
    """把账号映射到业务主键，塞进 JWT。

    学生 -> student.id；教师 -> teacher.id；管理员无业务主键。
    Service 层拿学生身份时因此不必再查库。
    """
    if role == ROLE_STUDENT:
        row = student_repo.find_by_user_id(conn, user_id)
        return int(row["id"]) if row else None
    if role == ROLE_TEACHER:
        row = teacher_repo.find_by_user_id(conn, user_id)
        return int(row["id"]) if row else None
    return None


def login(dto: LoginDTO) -> LoginVO:
    conn = db.connection()
    user = user_repo.find_by_username(conn, dto.username)

    # 先判存在、再判密码，但两条路径抛同一个错误 —— 见 _LOGIN_FAILED 的注释
    if user is None:
        raise BusinessException(ErrorCode.LOGIN_FAILED, _LOGIN_FAILED)
    if not verify_password(dto.password, user["password_hash"]):
        raise BusinessException(ErrorCode.LOGIN_FAILED, _LOGIN_FAILED)
    if int(user["status"]) != 1:
        raise BusinessException(ErrorCode.LOGIN_FAILED, "该账号已被禁用，请联系管理员")

    user_id = int(user["id"])
    role = str(user["role"])
    ref_id = _resolve_ref_id(conn, user_id, role)

    token, expire_hours = create_token(
        user_id=user_id,
        username=str(user["username"]),
        role=role,
        real_name=str(user["real_name"]),
        ref_id=ref_id,
    )
    return LoginVO.of_login(
        token=token, user_id=user_id, username=str(user["username"]),
        role=role, real_name=str(user["real_name"]), ref_id=ref_id,
        expire_hours=expire_hours,
    )


def current_user(user: UserContext) -> LoginVO:
    return LoginVO.of_user(
        user_id=user.user_id, username=user.username, role=user.role,
        real_name=user.real_name, ref_id=user.ref_id,
    )
