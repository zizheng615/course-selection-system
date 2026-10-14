"""认证接口。对标参考项目的 `controller/AuthController`。"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..common.result import ok
from ..schemas.auth import LoginDTO
from ..security import UserContext, authenticate
from ..service import auth_service

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/login", summary="登录（公开）")
def login(dto: LoginDTO) -> dict:
    return ok(auth_service.login(dto))


@router.get("/me", summary="当前登录用户")
def me(user: UserContext = Depends(authenticate)) -> dict:
    return ok(auth_service.current_user(user))
