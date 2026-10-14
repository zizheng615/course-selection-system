"""AI 助手：知识库 + 大模型兜底，由注册表编排。

扩展方式：实现 `AiAnswerProvider` 协议并注册进 `AiProviderRegistry`，
不需要修改任何既有代码 —— 见 `provider.py` 的模块 docstring。
"""

from .answer import AiAnswer
from .context import AiContext
from .kb_provider import KnowledgeBaseProvider
from .llm_provider import ClaudeProvider
from .provider import AiAnswerProvider, AiProviderRegistry
from .registry import build_default_registry, registry

__all__ = [
    "AiAnswer",
    "AiContext",
    "AiAnswerProvider",
    "AiProviderRegistry",
    "KnowledgeBaseProvider",
    "ClaudeProvider",
    "build_default_registry",
    "registry",
]
