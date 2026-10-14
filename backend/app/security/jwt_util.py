"""JWT 签发与解析（HS256）。

对标参考项目的 `security/JwtUtil`。载荷与参考项目保持一致：

    subject = userId
    username / role / realName
    refId   = 学生为 student.id，教师为 teacher.id，管理员为 null

**为什么把 refId 放进 Token**：Service 层拿学生身份时不必再查一次库，
`UserContext.require_student_id()` 直接给出业务主键 —— 与参考项目的取舍一致。

密钥来源见 `config.py`：只从环境变量 `JWT_SECRET` 读取，仓库内不保存真实凭据。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from ..common.errors import BusinessException, ErrorCode
from ..config import settings

ALGORITHM = "HS256"

# HS256 的安全性依赖密钥长度，RFC 7518 要求 >= 32 字节
_MIN_SECRET_BYTES = 32


class TokenError(BusinessException):
    def __init__(self, message: str = "登录已过期，请重新登录") -> None:
        super().__init__(ErrorCode.TOKEN_INVALID, message)


def _secret() -> str:
    secret = settings.jwt_secret
    if len(secret.encode("utf-8")) < _MIN_SECRET_BYTES:
        raise RuntimeError(
            f"JWT_SECRET 长度不足 {_MIN_SECRET_BYTES} 字节，HS256 无法安全使用。"
            "请通过环境变量设置一个更长的密钥。"
        )
    return secret


def create_token(
    *,
    user_id: int,
    username: str,
    role: str,
    real_name: str,
    ref_id: int | None = None,
    expire_hours: int | None = None,
) -> tuple[str, int]:
    """签发 Token，返回 `(token, 有效期小时数)`。"""
    hours = expire_hours or settings.jwt_expire_hours
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "realName": real_name,
        "refId": ref_id,
        "iat": now,
        "exp": now + timedelta(hours=hours),
    }
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM), hours


def _validate_claims(claims: dict[str, Any]) -> dict[str, Any]:
    """校验载荷结构。

    签名有效不等于载荷可用：`sub` 必须能转成用户主键，`username` 不能为空，
    `role` 必须是已知角色。少任何一项都应判 1002 而不是让
    `UserContext` 拿着空角色继续往下走（那会变成「认证通过但身份为空」的漏洞）。
    """
    from .context import ROLE_NAMES  # 局部导入：避免 security 包内的导入顺序问题

    try:
        user_id = int(claims.get("sub"))
    except (TypeError, ValueError) as exc:
        raise TokenError() from exc
    if user_id <= 0:
        raise TokenError()
    if not str(claims.get("username") or "").strip():
        raise TokenError()
    if str(claims.get("role") or "") not in ROLE_NAMES:
        raise TokenError()
    if "realName" not in claims:
        raise TokenError()
    return claims


def parse_token(token: str) -> dict[str, Any]:
    """解析并校验 Token。任何问题一律归一成 1002，不向调用方泄露细节。"""
    if not token:
        raise TokenError("未登录，请先登录")
    try:
        claims = jwt.decode(token, _secret(), algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("登录已过期，请重新登录") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("登录已过期，请重新登录") from exc
    return _validate_claims(claims)


def extract_bearer(authorization: str | None) -> str:
    """从 `Authorization: Bearer <token>` 头里取出 Token。"""
    if not authorization:
        raise TokenError("未登录，请先登录")
    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise TokenError("未登录，请先登录")
    return parts[1].strip()
