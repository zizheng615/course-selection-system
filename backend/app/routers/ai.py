"""AI 助手接口。对标参考项目的 `controller/AiController`。

角色取自 JWT，**不读请求体** —— 否则学生可以自称管理员，
拿到管理端的菜单与操作说明。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..ai.context import AiContext
from ..common.result import ok
from ..schemas.ai import AiChatDTO
from ..security import UserContext, authenticate
from ..service import ai_service

router = APIRouter(prefix="/api/ai", tags=["AI 助手"])


@router.post("/chat", summary="提问")
def chat(dto: AiChatDTO, user: UserContext = Depends(authenticate)) -> dict:
    context = AiContext(role=user.role, real_name=user.real_name, user_id=user.user_id)
    return ok(ai_service.ask(dto.question, context))


@router.get("/suggestions", summary="当前角色的推荐问题")
def suggestions(user: UserContext = Depends(authenticate)) -> dict:
    return ok(ai_service.suggest(user.role))
