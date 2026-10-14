"""AI 问答的上下文。对标参考项目的 `ai/AiContext`。

**角色来自 JWT，不来自请求体** —— 否则学生可以自称管理员，
拿到管理端的菜单与操作说明，进而被引导去点根本没有权限的页面。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AiContext:
    role: str
    real_name: str = ""
    user_id: int = 0

    @property
    def display_name(self) -> str:
        return self.real_name or "同学"
