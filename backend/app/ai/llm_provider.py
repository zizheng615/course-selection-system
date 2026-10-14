"""大模型提供方（Anthropic 协议兼容端点）。对标参考项目的 `ai/ClaudeProvider`。

它排在知识库**之后**（order=2），只在知识库没命中时兜底。

三条硬性约束，改动前请先理解：

1. **API Key 只从环境变量 `AI_API_KEY` 读取**，仓库内不保存任何真实凭据。
   未配置时 `is_available()` 返回 False，系统退化为纯知识库模式 ——
   也就是说「什么都不配」也能正常跑，只是少了大模型兜底。
2. **`base_url` 必须显式使用**。参考项目踩过的坑：Anthropic 的 Java SDK 不读取
   `ANTHROPIC_BASE_URL`，只设环境变量会让请求打到官方端点、第三方 Key 被 403 拒绝，
   然后静默降级回知识库 —— 表现为「对话正常但模型从未被调用」，极难排查。
   这里直接把它当作请求 URL 的前缀拼，不存在这个隐患。
3. **任何异常都必须捕获并返回 None**。外部依赖不可用时不能让异常冒到用户面前，
   AI 功能整体仍要能用。这条由 `tests/test_ai.py` 断言。

接的是「Anthropic 协议兼容」接口，所以官方 Claude、DeepSeek、OpenRouter、
自建网关都能用，换服务商只需改 `AI_BASE_URL` / `AI_MODEL` / `AI_PROVIDER_NAME`。
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ..config import settings
from .answer import AiAnswer
from .context import AiContext

logger = logging.getLogger("app.ai.llm")

ANTHROPIC_VERSION = "2023-06-01"

SYSTEM_PROMPT = """你是「高校选课管理系统」内置的智能助手，只回答与本系统使用相关的问题。

关于本系统的确定事实（回答时必须与此一致，不要编造不存在的功能）：
- 三种角色：管理员（ADMIN）、教师（TEACHER）、学生（STUDENT），能看到的菜单不同。
- 学生可以：浏览可选课程、选课、退课、查看我的课程与成绩、查看我的课表。
- 教师可以：查看自己任教课程的学生名单、为学生录入成绩（0-100，已退课的学生不能录入）。
- 管理员可以：课程管理、排课管理、学生管理、教师管理、账号管理、选课记录管理、统计报表。
- 选课有三类限制：课程未开放选课、容量已满、与已选课程上课时间冲突。重复选课会被拒绝。
- 退课是「软退课」：保留修读记录，容量归还；退课后可以重新选同一门课。
- 学生/教师的新账号由管理员创建，初始密码统一为 123456，登录账号就是学号或工号。
- 一门课可能有多段上课时间（例如理论课 + 实验课），它们都会出现在课表里。

回答要求：
1. 用简体中文，口语化、简洁，控制在 200 字以内。
2. 只讲本系统的操作，不要扩展到通用编程或与选课无关的话题。
3. 不要罗列不存在的菜单名或按钮；不确定时直接说「这个我不太确定」。
4. 不要复述用户的问题，直接给答案。
5. 可以用少量 Markdown 加粗，但不要用表格、标题和代码块。"""


class ClaudeProvider:
    """名字沿用参考项目的 `ClaudeProvider`；它接的是协议兼容端点，不限于官方 Claude。"""

    def __init__(
        self,
        *,
        enabled: bool | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        provider_name: str | None = None,
        max_tokens: int | None = None,
        timeout: int | None = None,
    ) -> None:
        self._enabled = settings.ai_enabled if enabled is None else enabled
        self._api_key = (settings.ai_api_key if api_key is None else api_key).strip()
        self._base_url = (settings.ai_base_url if base_url is None else base_url).rstrip("/")
        self._model = settings.ai_model if model is None else model
        self._provider_name = settings.ai_provider_name if provider_name is None else provider_name
        self._max_tokens = settings.ai_max_tokens if max_tokens is None else max_tokens
        self._timeout = settings.ai_timeout_seconds if timeout is None else timeout

    @property
    def name(self) -> str:
        return self._provider_name

    def is_available(self) -> bool:
        return bool(self._enabled and self._api_key)

    def try_answer(self, question: str, context: AiContext) -> AiAnswer | None:
        if not self.is_available():
            return None
        try:
            text = self._request(question, context)
        except Exception as exc:  # noqa: BLE001 —— 兜底降级，见模块 docstring 第 3 条
            logger.warning("大模型提供方调用失败，降级为知识库：%s", exc)
            return None
        if not text:
            return None
        return AiAnswer(answer=text, source=self._provider_name, suggestions=[])

    # ------------------------------------------------------------------

    def _request(self, question: str, context: AiContext) -> str:
        payload: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": self._user_message(question, context)}],
        }
        # 同时带 x-api-key 与 Authorization：官方端点认前者，多数第三方网关认后者
        headers = {
            "content-type": "application/json",
            "x-api-key": self._api_key,
            "Authorization": f"Bearer {self._api_key}",
            "anthropic-version": ANTHROPIC_VERSION,
        }
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(f"{self._base_url}/v1/messages", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
        return self._extract_text(data)

    @staticmethod
    def _user_message(question: str, context: AiContext) -> str:
        role_hint = {
            "STUDENT": "当前提问者是一名学生。",
            "TEACHER": "当前提问者是一名教师。",
            "ADMIN": "当前提问者是一名系统管理员。",
        }.get(context.role, "")
        return f"{role_hint}用户的问题：{question}"

    @staticmethod
    def _extract_text(data: dict[str, Any]) -> str:
        """从 Anthropic 协议的响应里取出文本。

        兼容两种形状：`content: [{type:"text", text:"..."}]`（Anthropic 官方格式），
        以及部分网关直接返回的 `content: "..."`。
        """
        content = data.get("content")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = [
                block.get("text", "")
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            return "\n".join(p for p in parts if p).strip()
        return ""
