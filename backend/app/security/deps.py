"""FastAPI 依赖：认证与声明式角色校验。

对标参考项目的 `JwtInterceptor` + `@RequireRole(…)`。

用法（权限写在路由签名上，而不是散落进 Service 的 if-else）：::

    @router.get("")
    def list_courses(user: CurrentUser = Depends(require_role(ROLE_ADMIN))):
        ...

    @router.get("")            # 任意已登录用户
    def list_courses(user: CurrentUser = Depends(authenticate)):
        ...

`require_role()` 是本项目「开闭原则」的一个扩展点：新增角色或调整权限
只需改路由上的声明，不必碰任何 Service。
"""

from __future__ import annotations

from typing import Annotated, Callable

from fastapi import Depends, Header

from ..common.errors import BusinessException, ErrorCode
from .context import UserContext
from .jwt_util import extract_bearer, parse_token


def authenticate(authorization: Annotated[str | None, Header()] = None) -> UserContext:
    """解析 `Authorization` 头，返回当前用户。缺失/非法/过期 -> 1001 或 1002。"""
    token = extract_bearer(authorization)
    return UserContext.from_claims(parse_token(token))


#: 语义别名：路由签名上写 `user: CurrentUser = Depends(authenticate)` 更易读
CurrentUser = UserContext


def require_role(*roles: str) -> Callable[..., UserContext]:
    """依赖工厂：要求当前用户具备指定角色之一。

    错误码用 1003（已登录但无权），与参考项目一致 —— 未登录是 1001，两者不能混。
    """

    def dependency(user: UserContext = Depends(authenticate)) -> UserContext:
        if roles and user.role not in roles:
            raise BusinessException(
                ErrorCode.NO_PERMISSION,
                f"无权访问该资源，需要角色：{'/'.join(roles)}",
            )
        return user

    return dependency


#: 常用组合，省掉在路由里重复拼字符串
AdminOnly = Depends(require_role("ADMIN"))
TeacherOnly = Depends(require_role("TEACHER"))
StudentOnly = Depends(require_role("STUDENT"))
TeacherOrAdmin = Depends(require_role("TEACHER", "ADMIN"))
