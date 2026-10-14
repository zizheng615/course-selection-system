"""AI 助手 DTO / VO。对标参考项目的 `dto/AiChatDTO`、`vo/AiChatVO`。"""

from __future__ import annotations

from pydantic import Field

from ._base import DTO, VO


class AiChatDTO(DTO):
    question: str = Field(..., min_length=1, max_length=500)


class AiChatVO(VO):
    answer: str
    #: 三值，**不要合并**：`本地知识库` / `未匹配` / 配置的服务名
    source: str
    suggestions: list[str] = Field(default_factory=list)
