"""AI 问答编排。对标参考项目的 `service/AiService`。

**本模块不含任何回答逻辑**，只负责「按顺序问一遍可用的提供方，谁先答上来就用谁」。
新增回答来源不需要改这里 —— 实现 `AiAnswerProvider` 并注册进注册表即可，
顺序由注册时的 `order` 决定。这是本项目「开闭原则」最主要的落地点：
本文件不认识任何具体提供方，因此永远不会因为新增提供方而被修改。
"""

from __future__ import annotations

import logging

from ..ai.answer import AiAnswer
from ..ai.context import AiContext
from ..ai.provider import AiProviderRegistry
from ..ai.registry import registry as default_registry
from ..schemas.ai import AiChatVO

logger = logging.getLogger("app.ai")

SOURCE_UNMATCHED = "未匹配"

#: 兜底话术刻意**不举具体菜单例子**：不同角色能看到的菜单不一样，
#: 举「课程管理」这种管理端菜单会把学生和教师引到他们根本没有的页面上。
FALLBACK_ANSWER = """这个问题我没把握给出准确答案 🤔

我的职责是解答**本选课系统的使用方法**，可以先换个说法再问一次，
或者从下面这些问题里挑一个 👇"""

#: 按角色给出推荐的快捷问题，前端在对话框空态和兜底回答里都会用到
SUGGESTIONS: dict[str, list[str]] = {
    "STUDENT": ["怎么选课", "为什么有的课选不了", "在哪看课表和成绩", "怎么退课"],
    "TEACHER": ["怎么查看学生名单", "怎么录入成绩", "系统有哪些功能"],
    "ADMIN": ["怎么新增课程", "怎么排课", "怎么重置学生密码", "怎么管理选课记录", "统计报表在哪里"],
    "DEFAULT": ["系统有哪些功能"],
}


def suggestions_for(role: str) -> list[str]:
    return list(SUGGESTIONS.get(role, SUGGESTIONS["DEFAULT"]))


def ask(question: str, context: AiContext, provider_registry: AiProviderRegistry | None = None) -> AiChatVO:
    """依次询问所有可用的提供方，返回第一个给出的答案。

    `provider_registry` 可注入，便于测试注册假提供方而不污染全局注册表。
    """
    active = provider_registry or default_registry

    for provider in active.available():
        answer = provider.try_answer(question, context)
        if answer is not None:
            return AiChatVO(
                answer=answer.answer,
                source=answer.source,
                suggestions=answer.suggestions or suggestions_for(context.role),
            )

    logger.info("所有提供方均未给出回答：question=%s role=%s", question, context.role)
    # 来源标记为「未匹配」而不是「本地知识库」：知识库命中与「所有提供方都没答上来」
    # 是完全不同的两种情况，用同一个标签会让用户误以为这是知识库给出的答案，
    # 也会让测试无法区分「角色隔离生效」和「知识库条目写错了」。
    return AiChatVO(answer=FALLBACK_ANSWER, source=SOURCE_UNMATCHED, suggestions=suggestions_for(context.role))


def suggest(role: str) -> list[str]:
    return suggestions_for(role)


__all__ = ["ask", "suggest", "suggestions_for", "AiAnswer", "FALLBACK_ANSWER", "SOURCE_UNMATCHED"]
