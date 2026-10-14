"""默认提供方注册表。

顺序是关键（对应参考项目的 `@Order`）：

====  ========================  ==========================  ==============================
顺序   提供方                     可用条件                     定位
====  ========================  ==========================  ==============================
 1    `KnowledgeBaseProvider`   始终                         答案与系统实际行为逐条核对过
 2    `ClaudeProvider`          配置了 `AI_API_KEY`          知识库没命中时才兜底
====  ========================  ==========================  ==============================

**为什么知识库排前面**：模型会泛泛而谈甚至编造不存在的菜单。
能用确定答案就不用生成式答案。改动顺序前先想清楚这一点。
"""

from __future__ import annotations

from .kb_provider import KnowledgeBaseProvider
from .llm_provider import ClaudeProvider
from .provider import AiAnswerProvider, AiProviderRegistry

ORDER_KNOWLEDGE_BASE = 1
ORDER_LLM = 2


def build_default_registry() -> AiProviderRegistry:
    """构造进程级的默认注册表。

    这是一个**工厂**而不是模块级单例：测试可以在自己的 fixture 里建一个独立实例
    （并往里注册假提供方），不会污染其它测试。
    """
    registry = AiProviderRegistry()
    registry.register(KnowledgeBaseProvider(), ORDER_KNOWLEDGE_BASE)
    registry.register(ClaudeProvider(), ORDER_LLM)
    return registry


#: 应用运行时使用的注册表
registry = build_default_registry()

__all__: list[str] = [
    "registry",
    "build_default_registry",
    "AiAnswerProvider",
    "AiProviderRegistry",
    "KnowledgeBaseProvider",
    "ClaudeProvider",
    "ORDER_KNOWLEDGE_BASE",
    "ORDER_LLM",
]
