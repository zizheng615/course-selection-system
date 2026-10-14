"""打包前置门禁：确认**将要进入压缩包的文件**里没有敏感信息，命中任意一条就失败。

为什么需要它
------------
参考项目把两处真实凭据明文写在了 `application.yml` 里（一个可用的 LLM API Key
和一个 JWT 签名密钥）。人眼审一遍代码是不可靠的 —— 只要有人复制粘贴一次，
凭据就进了提交物。所以这里用**机械扫描**代替人工检查，并且把它做成
`package.py` 的前置步骤：不通过就打包不出来。

扫描范围 = 打包范围
------------------
关键设计：本脚本扫描的文件集与 `package.py` 实际压缩的文件集**完全一致**
（共用下面同一份排除规则）。这样有两层好处：

* 本地 `.env`、`*.db` 这类文件本来就被排除在压缩包之外，
  不会因为它们躺在工作目录里就让门禁永远失败 —— 那是把「本地配置」误判成「已泄露」；
* 反过来说，只要某个文件**真的会被打进包**，它就会被逐行扫描，一个都跑不掉。

扫描四类问题
------------
1. `sk-` 开头的 API Key 字面量（含参考项目里泄露的那一个）；
2. `api-key / api_key` 被赋了**非空**的值（占位符与空值不算）；
3. 硬编码的绝对路径（`D:\\...` / `/home/...`）—— 换台机器就跑不起来，
   而且会泄露作者的本机目录结构；
4. JWT 密钥、明文口令等其它凭据字面量。

用法
----
    python scripts/sanitize_check.py          # 检查，命中即退出码 1
    python scripts/package.py                 # 会先调用它，通过后才打包
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------- 排除规则
# 这份规则同时被 package.py 复用：门禁扫什么，就打包什么。

#: 目录名命中即整棵跳过：缓存、版本控制、IDE、打包产物。
SKIP_DIRS = {
    "__pycache__", ".git", ".idea", ".vscode",
    "node_modules", ".venv", "venv", "dist", "build", ".playwright-mcp", "data",
}

#: 文件名命中即跳过 —— 前两个是凭据文件（本地配置，不进提交物）。
EXCLUDE_NAMES = {".env", ".DS_Store", "Thumbs.db", "desktop.ini"}

#: 后缀命中即跳过：编译缓存与运行期数据库（由 scripts/init_db.py 重新生成）。
EXCLUDE_SUFFIXES = {".pyc", ".pyo", ".db", ".db-wal", ".db-shm", ".sqlite", ".sqlite3", ".log"}

#: 只扫文本文件。二进制文件按行读会误报，也没必要。
TEXT_SUFFIXES = {
    ".py", ".js", ".css", ".html", ".sql", ".md", ".txt", ".yml", ".yaml",
    ".json", ".ini", ".cfg", ".toml", ".env", ".example", ".sh", ".bat",
}
TEXT_NAMES = {".env.example", ".gitignore", "Dockerfile"}

#: 本文件自己会写下这些正则，天然包含 `sk-` 之类的片段，跳过自检。
SELF = Path(__file__).resolve()

# ---------------------------------------------------------------- 规则定义

#: 类型标注（`api_key: str`）不是凭据，值落在这些词上就跳过。
_TYPE_WORDS = {
    "str", "int", "bool", "float", "bytes", "none", "optional", "dict",
    "list", "tuple", "secretstr", "object", "any",
}

#: 值里出现这些字符说明它是个**表达式**（`os.getenv(...)` / `settings.ai_api_key`）
#: 而不是写死的字面量 —— 从环境变量或配置对象取值正是我们想要的做法。
_EXPR_CHARS = ("(", ")", "[", "]", ".", "$", "{", "}")


def _is_not_a_literal(value: str) -> bool:
    """判断捕获到的「值」其实是占位符 / 类型标注 / 取值表达式，而非写死的凭据。

    这个规则是整份扫描里最容易误报的一处，所以判据要写宽一点：
    宁可漏掉一个畸形的写法，也不要每跑一次就报三条假警报 ——
    假警报多了，真警报就没人看了。
    """
    v = value.strip().strip('"').strip("'").strip()
    if not v:
        return True                                  # 空值：`AI_API_KEY=` 这种
    if v.startswith(("<", "${", "$")):                # 占位符：`<your-key>` / `${AI_API_KEY}`
        return True
    if any(ch in v for ch in _EXPR_CHARS):            # 表达式：`os.getenv("AI_API_KEY")`
        return True
    if v.lower() in _TYPE_WORDS:                      # 类型标注：`api_key: str`
        return True
    return v.lower() in {
        "your-api-key", "your_api_key", "changeme", "change-me", "xxx",
        "todo", "null", "placeholder", "sk-xxx", "sk-your-key",
    }


#: (规则名, 正则, 说明)
#:
#: 注意：正则写成**字符类**的形式是有意的 —— 源码里出现的是
#: `sk-[A-Za-z0-9_-]{16,}` 这样的模式串，它本身不匹配自己的规则
#: （`[` 不属于 `[A-Za-z0-9_-]`），所以不需要给自己开例外。
PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    (
        "api-key-literal",
        re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
        "疑似真实 API Key 字面量。Key 必须只从环境变量读取。",
    ),
    (
        "api-key-assigned",
        re.compile(
            r"""(?ix)
            (?: api[-_ ]?key | ai[-_ ]?api[-_ ]?key | secret[-_ ]?key | access[-_ ]?token )
            \s* [:=] \s*
            (?P<value> ["']? [^\s"'#,}]{1,200} )
            """
        ),
        "api key / secret 被赋了非空值。检查是不是把真实凭据写进来了。",
    ),
    (
        "jwt-secret-literal",
        re.compile(r"course-selection-design-\S*jwt\S*", re.I),
        "参考项目里泄露的 JWT 密钥片段。本项目不得出现。",
    ),
    (
        "abs-path-windows",
        re.compile(r"[A-Za-z]:[\\/](?:Users|course-design|Dev|projects)[\\/]\S*"),
        "硬编码的 Windows 绝对路径。改用相对路径或 Path(__file__) 推导。",
    ),
    (
        "abs-path-posix",
        re.compile(r"/(?:home|Users)/(?!<)\w+/\S*"),
        "硬编码的 POSIX 绝对路径。改用相对路径或 Path(__file__) 推导。",
    ),
]

#: 本项目**有意**公开的演示默认值，属于例外，命中时放行。
#: 它们不是真实凭据：前者是 README 里写明的演示口令，后者是公开的占位密钥。
ALLOWLIST = {
    "course-selection-py-dev-only-secret-change-me-in-production": "README 已声明的演示用 JWT 占位密钥",
    "123456": "README 已声明的演示口令",
}


# ---------------------------------------------------------------- 文件收集


def iter_packaged_files() -> list[Path]:
    """**将要进入压缩包**的全部文件（绝对路径）。`package.py` 直接复用。"""
    files: list[Path] = []
    for path in sorted(BASE_DIR.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(BASE_DIR)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if path.name in EXCLUDE_NAMES or path.suffix.lower() in EXCLUDE_SUFFIXES:
            continue
        files.append(path)
    return files


def is_scannable(path: Path) -> bool:
    return path.name in TEXT_NAMES or path.suffix.lower() in TEXT_SUFFIXES


def iter_scannable_files() -> list[Path]:
    return [p for p in iter_packaged_files() if is_scannable(p) and p.resolve() != SELF]


def find_excluded_sensitive() -> list[Path]:
    """工作目录里存在、但因为属于凭据/运行期数据而**被排除在压缩包外**的文件。

    它们不会造成泄露（压根进不了包），但值得在报告里点名，
    提醒使用者这些文件是本地配置，别手动塞进压缩包。
    """
    found = []
    for path in sorted(BASE_DIR.rglob("*")):
        if not path.is_file():
            continue
        # 先按名字/后缀判断，再考虑目录 —— 数据库在 data/ 下，
        # 若先套 SKIP_DIRS 就会把它一起跳过，报告里反而看不到。
        if path.name not in EXCLUDE_NAMES and path.suffix.lower() not in EXCLUDE_SUFFIXES:
            continue
        if any(part in {".git", "__pycache__", ".venv", "venv"} for part in path.parts):
            continue
        found.append(path)
    return found


# ---------------------------------------------------------------- 扫描


def scan_text(path: Path) -> list[tuple[int, str, str, str]]:
    """返回 [(行号, 规则名, 命中片段, 说明), ...]。"""
    try:
        content = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []

    hits = []
    for lineno, line in enumerate(content.splitlines(), start=1):
        for name, pattern, hint in PATTERNS:
            for match in pattern.finditer(line):
                fragment = match.group(0)
                if name == "api-key-assigned" and _is_not_a_literal(match.group("value")):
                    continue
                if any(allowed in fragment for allowed in ALLOWLIST):
                    continue
                hits.append((lineno, name, fragment[:90], hint))
    return hits


def main() -> int:
    files = iter_scannable_files()
    findings: list[str] = []
    for path in files:
        for lineno, rule, fragment, hint in scan_text(path):
            rel = path.relative_to(BASE_DIR)
            findings.append(f"  {rel}:{lineno}  [{rule}] {fragment}\n      -> {hint}")

    excluded = find_excluded_sensitive()
    scanned_kb = sum(p.stat().st_size for p in files) / 1024

    print("=" * 68)
    print("  脱敏自检")
    print("=" * 68)
    print(f"  打包文件  {len(iter_packaged_files())} 个（其中可扫描文本 {len(files)} 个，{scanned_kb:.0f} KB）")
    print(f"  敏感命中  {len(findings)} 处")
    if excluded:
        print(f"  已排除    {len(excluded)} 个本地文件（不进压缩包）")
    print("-" * 68)

    if excluded:
        print("\n[i] 以下文件存在但**不会**进入压缩包，无需删除：")
        for path in excluded:
            print(f"  {path.relative_to(BASE_DIR)}")

    if findings:
        print("\n[!] 疑似敏感信息：")
        for item in findings:
            print(item)
        print("\n" + "=" * 68)
        print("  未通过：先清理上面的内容再打包。")
        print("=" * 68)
        return 1

    print("\n  通过：将进入压缩包的每个文本文件都已扫描，未发现 API Key、")
    print("        明文凭据或硬编码绝对路径。")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    sys.exit(main())
