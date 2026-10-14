"""AI 回答的数据载体。对标参考项目的 `ai/AiAnswer`。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AiAnswer:
    answer: str
    #: 回答来源标签。三种取值**不要合并**：
    #: `本地知识库`（知识库命中）/ `未匹配`（都没答上来）/ 配置的服务名（大模型作答）。
    #: 回归测试靠区分这三个来定位问题 —— 合并后无法分辨
    #: 「角色隔离生效」和「知识库条目写错了」。
    source: str
    suggestions: list[str] = field(default_factory=list)
