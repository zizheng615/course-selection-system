"""全局配置。

设计原则（对标参考项目的 `application.yml`）：

* **敏感信息一律只从环境变量读取**，仓库内不保存任何真实凭据。
  本地开发时把变量写进项目根目录的 `.env`（已被 .gitignore 忽略），
  部署时由运行环境注入。
* 所有配置项都有**可安全公开的默认值**，因此「什么都不配」也能把系统跑起来 ——
  只是 AI 助手退化为纯本地知识库模式。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# backend/app/config.py -> backend/app -> backend -> <项目根>
BASE_DIR = Path(__file__).resolve().parent.parent.parent


def _load_dotenv(path: Path) -> None:
    """极简 .env 解析器。

    不引入 python-dotenv 依赖，只支持最常见的 `KEY=VALUE` 形式。
    已存在的环境变量优先，不会被文件覆盖。
    """
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv(BASE_DIR / ".env")


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# HS256 要求密钥长度 >= 32 字节。
# 这里的默认值是**公开的演示占位符**，仅供本地/答辩环境使用；
# 生产部署必须通过环境变量 JWT_SECRET 覆盖。
_DEV_JWT_SECRET = "course-selection-py-dev-only-secret-change-me-in-production"

DEFAULT_SEMESTER = "2026-2027-1"


@dataclass(frozen=True)
class Settings:
    # ---- 数据库 ----
    db_path: Path = field(
        default_factory=lambda: Path(os.getenv("DB_PATH") or (BASE_DIR / "data" / "course_selection.db"))
    )

    # ---- JWT ----
    jwt_secret: str = field(default_factory=lambda: os.getenv("JWT_SECRET") or _DEV_JWT_SECRET)
    jwt_expire_hours: int = field(default_factory=lambda: _env_int("JWT_EXPIRE_HOURS", 24))

    # ---- AI 助手 ----
    # enabled=false 或 api_key 为空 -> 大模型提供方不可用，系统只走本地知识库。
    ai_enabled: bool = field(default_factory=lambda: _env_bool("AI_ENABLED", True))
    ai_api_key: str = field(default_factory=lambda: os.getenv("AI_API_KEY") or "")
    ai_base_url: str = field(
        default_factory=lambda: os.getenv("AI_BASE_URL") or "https://api.anthropic.com"
    )
    ai_model: str = field(default_factory=lambda: os.getenv("AI_MODEL") or "claude-sonnet-5-5")
    # 前端「来源」标签显示的服务商名称
    ai_provider_name: str = field(default_factory=lambda: os.getenv("AI_PROVIDER_NAME") or "Claude")
    ai_max_tokens: int = field(default_factory=lambda: _env_int("AI_MAX_TOKENS", 2048))
    ai_timeout_seconds: int = field(default_factory=lambda: _env_int("AI_TIMEOUT_SECONDS", 30))

    # ---- 其它 ----
    default_semester: str = field(default_factory=lambda: os.getenv("DEFAULT_SEMESTER") or DEFAULT_SEMESTER)
    default_password: str = field(default_factory=lambda: os.getenv("DEFAULT_PASSWORD") or "123456")

    @property
    def static_dir(self) -> Path:
        return BASE_DIR / "backend" / "static"

    @property
    def sql_dir(self) -> Path:
        return BASE_DIR / "sql"


settings = Settings()
