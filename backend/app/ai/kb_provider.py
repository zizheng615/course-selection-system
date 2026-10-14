"""内置知识库提供方。对标参考项目的 `ai/KnowledgeBaseProvider`。

它排在大模型前面（order=1），因为**知识库的答案与系统实际行为逐条核对过，
属于确定信息**；模型会泛泛而谈甚至编造不存在的菜单。能用确定答案就不用生成式答案。

**关键词长度加权**：匹配得分 = 命中关键词的**长度之和**，而不是命中个数。
这不是随意定的 —— 「怎么管理选课记录」同时命中「选课记录」(4) 和「选课」(2)，
不按长度加权会落到泛泛的「怎么选课」条目上。

`MIN_SCORE = 2`：单字命中（长度 1）不足以判定，避免「课」字把任何问题都吸到某条目上。
"""

from __future__ import annotations

from .answer import AiAnswer
from .context import AiContext
from .knowledge_base import ENTRIES, KBEntry

#: 命中得分低于该值视为未命中
MIN_SCORE = 2

SOURCE_LABEL = "本地知识库"


def _normalize(text: str) -> str:
    """小写化并去掉**所有**空白字符。

    中文提问里空格位置很随意（「怎么 选课」/「怎么选课」），
    统一去掉空白后关键词匹配才稳定。
    """
    return "".join(text.lower().split())


def _score(entry: KBEntry, normalized_question: str) -> int:
    """命中关键词的长度之和。"""
    return sum(len(k) for k in entry.keywords if _normalize(k) in normalized_question)


def _role_allows(entry: KBEntry, role: str) -> bool:
    """条目未限定角色（空集合）时对所有角色生效，否则要求角色在集合内。"""
    return not entry.roles or role in entry.roles


class KnowledgeBaseProvider:
    """关键词检索式问答。始终可用（不依赖任何外部服务）。"""

    name = "本地知识库"

    def __init__(self, entries: tuple[KBEntry, ...] = ENTRIES, min_score: int = MIN_SCORE) -> None:
        self._entries = entries
        self._min_score = min_score

    def is_available(self) -> bool:
        return True

    def try_answer(self, question: str, context: AiContext) -> AiAnswer | None:
        if not question or not question.strip():
            return None

        normalized = _normalize(question)

        best: KBEntry | None = None
        best_score = 0
        for entry in self._entries:
            # 角色过滤：条目限定了角色且不含当前角色 -> 跳过。
            # 这是「学生看不到管理端操作说明」的实现处。
            if not _role_allows(entry, context.role):
                continue
            score = _score(entry, normalized)
            # 严格大于：同分时保留先注册的条目，保证结果稳定可复现
            if score > best_score:
                best, best_score = entry, score

        if best is None or best_score < self._min_score:
            return None
        return AiAnswer(answer=best.answer, source=SOURCE_LABEL, suggestions=list(best.suggestions))

    def match_entry(self, question: str, role: str) -> KBEntry | None:
        """返回命中的条目本身（供测试断言「推荐问题必须命中对应条目」用）。"""
        normalized = _normalize(question)
        best: KBEntry | None = None
        best_score = 0
        for entry in self._entries:
            if not _role_allows(entry, role):
                continue
            score = _score(entry, normalized)
            if score > best_score:
                best, best_score = entry, score
        return best if best_score >= self._min_score else None
