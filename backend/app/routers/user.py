"""账号管理接口。对标参考项目的 `controller/UserController`（类级 ADMIN）。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..common.result import ok
from ..schemas.user import UserCredentialDTO
from ..security import UserContext, require_role
from ..service import user_service

router = APIRouter(prefix="/api/users", tags=["账号管理"])

AdminDep = Depends(require_role("ADMIN"))


@router.get("", summary="账号分页列表")
def list_users(
    keyword: str | None = Query(None),
    role: str | None = Query(None),
    page: int | None = Query(1),
    size: int | None = Query(10),
    _: UserContext = AdminDep,
) -> dict:
    return ok(user_service.list_users(
        keyword=keyword, role=role, page_no=page, size=size
    ))


@router.put("/{user_id}/credentials", summary="改登录账号 / 重置密码")
def update_credentials(user_id: int, dto: UserCredentialDTO, _: UserContext = AdminDep) -> dict:
    user_service.update_credentials(user_id, dto)
    return ok()


@router.patch("/{user_id}/status", summary="启用 / 禁用账号")
def update_status(user_id: int, status: int = Query(...), user: UserContext = AdminDep) -> dict:
    user_service.update_status(user_id, status, user)
    return ok()


@router.delete("/{user_id}", summary="删除账号")
def delete_user(user_id: int, user: UserContext = AdminDep) -> dict:
    user_service.delete_user(user_id, user)
    return ok()
