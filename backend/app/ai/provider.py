"""AI 回答提供方接口 —— **本项目「开闭原则」最主要的落地处**。

对标参考项目的 `ai/AiAnswerProvider` + Spring 按 `@Order` 注入 `List<AiAnswerProvider>`。

Java 侧靠 Spring 的依赖注入自动收集实现类；Python 侧没有容器，
改成一个显式的注册表（`registry.py`）。**扩展方式是一样的**：

    新增一个回答来源 = 实现本 Protocol + 注册进注册表

`AiService` 只做编排（依次询问、谁先答上来就用谁），不含任何回答逻辑，
也永远不会因为新增提供方而被修改。判断一个改动是否守住了这条线，标准很实际：
**加一个新的回答来源，需要改动几个已有文件？答案是 0。**
"""

from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

from .answer import AiAnswer
from .context import AiContext


@runtime_checkable
class AiAnswerProvider(Protocol):
    """回答提供方。

    实现者只需满足这三个成员，无需继承任何基类（结构化子类型）。
    """

    #: 展示名，用于日志与调试
    name: str

    def is_available(self) -> bool:
        """当前是否可用。不可用的提供方会被编排器直接跳过。

        例：大模型提供方在未配置 API Key 时返回 False，系统退化为纯知识库模式。
        """
        ...

    def try_answer(self, question: str, context: AiContext) -> AiAnswer | None:
        """尝试作答。答不上来返回 None，由编排器询问下一个提供方。

        **实现必须自己兜住所有异常**：外部依赖（网络、模型服务）不可用时
        不能让异常冒到用户面前，AI 功能整体仍要能用。
        """
        ...


class AiProviderRegistry:
    """有序的提供方注册表。

    顺序即优先级：靠前的先被询问。注册时按 `order` 升序稳定排序，
    相同 order 保持注册先后（因此内置的知识库提供方 order=1 永远排第一）。
    """

    def __init__(self, providers: Sequence[AiAnswerProvider] = (), orders: Sequence[int] = ()) -> None:
        self._entries: list[tuple[int, int, AiAnswerProvider]] = []
        self._seq = 0
        for provider, order in zip(providers, orders or [0] * len(providers)):
            self.register(provider, order)

    def register(self, provider: AiAnswerProvider, order: int = 0) -> None:
        self._seq += 1
        self._entries.append((order, self._seq, provider))
        self._entries.sort(key=lambda item: (item[0], item[1]))

    def unregister(self, provider: AiAnswerProvider) -> None:
        self._entries = [e for e in self._entries if e[2] is not provider]

    def providers(self) -> list[AiAnswerProvider]:
        return [entry[2] for entry in self._entries]

    def available(self) -> list[AiAnswerProvider]:
        return [p for p in self.providers() if p.is_available()]

    def clear(self) -> None:
        self._entries.clear()
