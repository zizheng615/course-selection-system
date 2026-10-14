"""密码哈希。对标参考项目的 BCryptPasswordEncoder。

用 bcrypt 而不是 SHA-256：bcrypt 自带随机盐且计算代价可调，
即使库被拖走也无法用彩虹表批量反查，这正是参考项目选它的原因。

种子数据里存的是 cost=10 的 BCrypt 摘要，与这里 `gensalt(rounds=10)` 产出的
格式一致（`$2b$` 与 `$2a$` 前缀在校验时互相兼容），所以种子账号可以直接登录。
"""

from __future__ import annotations

import bcrypt

#: bcrypt 的输入上限是 72 字节，超长密码会被静默截断 —— 显式截断避免误用
_MAX_BYTES = 72


def _encode(raw: str) -> bytes:
    return raw.encode("utf-8")[:_MAX_BYTES]


def hash_password(raw: str) -> str:
    return bcrypt.hashpw(_encode(raw), bcrypt.gensalt(rounds=10)).decode("ascii")


def verify_password(raw: str, hashed: str) -> bool:
    """校验密码。摘要格式不合法时返回 False，不抛异常 —— 坏数据不应该变成 500。"""
    if not raw or not hashed:
        return False
    try:
        return bcrypt.checkpw(_encode(raw), hashed.encode("ascii"))
    except (ValueError, TypeError):
        return False
