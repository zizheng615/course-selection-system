"""打包成可直接提交的 zip。

顺序是刻意的：**先跑脱敏自检，通过了才打包**。
凭据一旦被压进压缩包，后面再怎么清理，它都已经在别人手里了。

排除规则与 `sanitize_check.py` **共用同一份定义** ——
门禁扫描的文件集 = 实际压缩的文件集，两者不会漂移。

    python scripts/package.py

产物默认落在项目**上一级**目录（避免把 zip 装进它自己）：
    <项目目录>/../course-selection-system-py.zip
"""

from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

from sanitize_check import BASE_DIR, SKIP_DIRS, iter_packaged_files

DEFAULT_OUTPUT = BASE_DIR.parent / f"{BASE_DIR.name}.zip"

#: 固定时间戳，让同一个版本重复打包得到**字节一致**的 zip（便于比对与校验）。
FIXED_DATE = (2026, 1, 1, 0, 0, 0)


def run_sanitize_gate() -> bool:
    script = BASE_DIR / "scripts" / "sanitize_check.py"
    print(f"[1/3] 脱敏自检  {script.relative_to(BASE_DIR)}\n")
    result = subprocess.run([sys.executable, str(script)], cwd=BASE_DIR)
    return result.returncode == 0


def build_zip(output: Path) -> tuple[int, int]:
    files = iter_packaged_files()
    output.parent.mkdir(parents=True, exist_ok=True)

    total_bytes = 0
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in files:
            rel = path.relative_to(BASE_DIR)
            info = zipfile.ZipInfo(str(Path(BASE_DIR.name) / rel).replace("\\", "/"), date_time=FIXED_DATE)
            # 压缩包内统一 0644，避免把本机的权限位带出去
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            data = path.read_bytes()
            zf.writestr(info, data)
            total_bytes += len(data)

    return len(files), total_bytes


def main() -> int:
    if not run_sanitize_gate():
        print("\n[中止] 脱敏自检未通过，不生成压缩包。")
        print("       请先按上面的提示清理，再重新执行本脚本。")
        return 1

    files = iter_packaged_files()
    print("\n[2/3] 收集文件")
    print(f"      待打包 {len(files)} 个文件")
    print(f"      已排除 {' / '.join(sorted(SKIP_DIRS))} 等目录，以及 .env、*.db 等本地文件")

    print("\n[3/3] 生成压缩包")
    count, raw_bytes = build_zip(DEFAULT_OUTPUT)
    size_kb = DEFAULT_OUTPUT.stat().st_size / 1024

    print("=" * 68)
    print(f"  完成：{DEFAULT_OUTPUT}")
    print(f"  文件数 {count}    压缩前 {raw_bytes / 1024:.0f} KB    压缩后 {size_kb:.0f} KB")
    print("=" * 68)
    print("  解压后三步跑起来：")
    print("      pip install -r requirements.txt")
    print("      python scripts/init_db.py")
    print("      python run.py            # http://localhost:8000")
    return 0


if __name__ == "__main__":
    sys.exit(main())
