"""账号服务（管理员）。对标参考项目的 `service/UserService`。"""

from __future__ import annotations

from .. import db
from ..common.errors import BusinessException, ErrorCode
from ..common.result import normalize_page, page
from ..repository import student_repo, teacher_repo, user_repo
from ..schemas.user import UserCredentialDTO, UserVO
from ..security.context import UserContext
from ..security.password import hash_password


def list_users(
    *, keyword: str | None = None, role: str | None = None,
    page_no: int | None = None, size: int | None = None,
) -> dict:
    p, s = normalize_page(page_no, size)
    rows, total = user_repo.search(
        db.connection(),
        keyword=(keyword or "").strip(),
        role=(role or "").strip(),
        page=p,
        size=s,
    )
    return page([UserVO.of_row(r) for r in rows], total, p, s)


def update_credentials(user_id: int, dto: UserCredentialDTO) -> None:
    """改登录账号 / 重置密码。

    `password` 留空 = **只改账号，不动密码** —— 这样管理员改个登录名
    不会顺手把用户自己设的密码重置掉。
    """
    with db.transaction() as conn:
        current = user_repo.find_by_id(conn, user_id)
        if current is None:
            raise BusinessException(ErrorCode.NOT_FOUND, "账号不存在")

        if dto.username != current["username"] and user_repo.exists_by_username(conn, dto.username):
            raise BusinessException(ErrorCode.DUPLICATE_KEY, f"登录账号已被占用：{dto.username}")

        new_hash = hash_password(dto.password) if dto.password else None
        user_repo.update_credentials(conn, user_id, dto.username, new_hash)


def update_status(user_id: int, status: int, operator: UserContext) -> None:
    if status not in (0, 1):
        raise BusinessException(ErrorCode.PARAM_ERROR, "状态只能为 1（启用）或 0（禁用）")
    if status == 0 and user_id == operator.user_id:
        # 否则管理员一按就把自己锁在系统外面，且无法自助恢复
        raise BusinessException(ErrorCode.PARAM_ERROR, "不能禁用当前登录的账号")

    with db.transaction() as conn:
        if user_repo.find_by_id(conn, user_id) is None:
            raise BusinessException(ErrorCode.NOT_FOUND, "账号不存在")
        user_repo.update_status(conn, user_id, status)


def delete_user(user_id: int, operator: UserContext) -> None:
    with db.transaction() as conn:
        current = user_repo.find_by_id(conn, user_id)
        if current is None:
            raise BusinessException(ErrorCode.NOT_FOUND, "账号不存在")
        if user_id == operator.user_id:
            raise BusinessException(ErrorCode.PARAM_ERROR, "不能删除当前登录的账号")

        # 账号绑定了业务信息时必须先去对应管理页删除，否则会留下孤儿账号：
        # 学生记录还在、登录入口没了。
        student = student_repo.find_by_user_id(conn, user_id)
        if student is not None:
            raise BusinessException(
                ErrorCode.COURSE_DELETE_FORBIDDEN, "该账号已绑定学生信息，请在「学生管理」中删除对应学生"
            )
        teacher = teacher_repo.find_by_user_id(conn, user_id)
        if teacher is not None:
            raise BusinessException(
                ErrorCode.COURSE_DELETE_FORBIDDEN, "该账号已绑定教师信息，请在「教师管理」中删除对应教师"
            )
        user_repo.delete(conn, user_id)
