"""
biliandout 构建脚本（修正资源文件打包）

修复内容：
- 正确打包 logo.png 供 PyQt 运行时使用
"""

from __future__ import annotations

import subprocess
import sys
import shutil
import tempfile
import zipfile
from pathlib import Path
from datetime import datetime


# ============================================================
# 基础配置
# ============================================================

APP_NAME = "Android哔哩哔哩视频导出器"
ENTRY_SCRIPT = "biliandout/biliandout.py"
ICON_PNG = "biliandout/logo.png"

PROJECT_ROOT = Path(__file__).parent.resolve()
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
RELEASE_DIR = PROJECT_ROOT / "_release"


# ============================================================
# 工具：PNG -> ICO
# ============================================================

def convert_png_to_ico(png_path: Path, ico_path: Path) -> bool:
    try:
        from PIL import Image

        img = Image.open(png_path).convert("RGBA")
        size = min(img.width, img.height)
        left = (img.width - size) // 2
        top = (img.height - size) // 2
        img = img.crop((left, top, left + size, top + size))

        sizes = [256, 128, 64, 48, 32, 24, 16]
        img.save(ico_path, format="ICO", sizes=[(s, s) for s in sizes])

        print(f"[OK] 图标生成: {ico_path}")
        return True
    except Exception as e:
        print(f"[WARN] 图标生成失败: {e}")
        return False


# ============================================================
# 构建主逻辑
# ============================================================

def build() -> None:
    entry = PROJECT_ROOT / ENTRY_SCRIPT
    icon_png = PROJECT_ROOT / ICON_PNG

    if not entry.exists():
        raise SystemExit(f"[ERROR] 找不到入口脚本: {entry}")

    print("=" * 60)
    print(" biliandout PyInstaller 构建开始")
    print("=" * 60)

    # ---------- 清理 ----------
    for d in (DIST_DIR, BUILD_DIR):
        if d.exists():
            shutil.rmtree(d)
            print(f"[CLEAN] 删除 {d}")

    RELEASE_DIR.mkdir(exist_ok=True)

    # ---------- 图标 ----------
    temp_dir = Path(tempfile.mkdtemp(prefix="biliandout-build-"))
    icon_ico = temp_dir / "app.ico"

    if not (icon_png.exists() and convert_png_to_ico(icon_png, icon_ico)):
        icon_ico = None
        print("[WARN] 将不设置 EXE 图标")

    # ---------- PyInstaller 参数 ----------
    pyinstaller_cmd = [
        sys.executable,
        "-m",
        "PyInstaller",

        "--onefile",
        "--windowed",
        "--clean",
        "--noconfirm",

        f"--name={APP_NAME}",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        f"--specpath={PROJECT_ROOT}",

        # 关键：运行时资源（logo.png）
        f"--add-data={ICON_PNG};biliandout",

        # 关键：完整收集 biliffm4s（包含 ffmpeg / dll）
        "--collect-all",
        "biliffm4s",
    ]

    if icon_ico:
        pyinstaller_cmd += ["--icon", str(icon_ico)]

    pyinstaller_cmd.append(str(entry))

    print("\n[CMD] PyInstaller 构建命令：\n")
    for i, arg in enumerate(pyinstaller_cmd):
        print(f"  {arg}")
    print()

    # ---------- 执行 ----------
    try:
        subprocess.run(pyinstaller_cmd, cwd=PROJECT_ROOT, check=True)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    exe_path = DIST_DIR / f"{APP_NAME}.exe"
    if not exe_path.exists():
        raise SystemExit("[ERROR] 未生成 exe")

    size_mb = exe_path.stat().st_size / 1024 / 1024
    print(f"[OK] 构建成功: {exe_path} ({size_mb:.2f} MB)")

    # ---------- 发布 ----------
    release_exe = RELEASE_DIR / exe_path.name
    shutil.copy2(exe_path, release_exe)

    zip_path = RELEASE_DIR / "biliandout.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(release_exe, release_exe.name)

    print("[OK] 发布完成")


if __name__ == "__main__":
    build()
