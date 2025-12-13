"""
biliandout 构建脚本（强制临时 Spec，彻底不受历史构建干扰）

保证：
- 不使用项目目录内任何 .spec（即使存在也不读取）
- 每次构建都生成临时 spec，显式写入 datas（logo）与 biliffm4s 完整收集
- onefile + windowed
- 自动生成 ico
- 输出 _release exe + zip

运行：
    python build.py
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
LOGO_PNG = "biliandout/logo.png"

PROJECT_ROOT = Path(__file__).resolve().parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
RELEASE_DIR = PROJECT_ROOT / "_release"


# ============================================================
# PNG -> ICO
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
# 生成临时 spec（关键）
# ============================================================

def write_temp_spec(spec_path: Path, *, entry: Path, logo: Path, icon_ico: Path | None) -> None:
    """
    生成临时 spec：
    - 显式 datas: 把 logo.png 放到 _MEIPASS 根目录（dest='.'），匹配代码 sys._MEIPASS/'logo.png'
    - collect_all('biliffm4s') 收集 binaries/datas/hiddenimports
    """
    # PyInstaller spec 是 Python 文件，路径请用原始字符串形式避免转义问题
    entry_s = str(entry)
    logo_s = str(logo)
    icon_s = str(icon_ico) if icon_ico else ""

    # icon 用 EXE(icon=...)；logo 用 Analysis(datas=...)
    spec_text = f"""
# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

block_cipher = None

# 1) 运行时资源：logo 放到 _MEIPASS 根目录
extra_datas = [
    (r"{logo_s}", "."),
]

# 2) 完整收集 biliffm4s（二进制/数据/隐式导入）
binaries = []
datas = []
hiddenimports = []

b_bili, d_bili, h_bili = collect_all("biliffm4s")
binaries += b_bili
datas += d_bili
hiddenimports += h_bili

datas += extra_datas

a = Analysis(
    [r"{entry_s}"],
    pathex=[r"{str(PROJECT_ROOT)}"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="{APP_NAME}",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon=r"{icon_s}" if r"{icon_s}" else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="{APP_NAME}",
)
"""
    spec_path.write_text(spec_text, encoding="utf-8")


# ============================================================
# 构建
# ============================================================

def build() -> None:
    entry = PROJECT_ROOT / ENTRY_SCRIPT
    logo = PROJECT_ROOT / LOGO_PNG

    if not entry.exists():
        raise SystemExit(f"[ERROR] 找不到入口脚本: {entry}")
    if not logo.exists():
        raise SystemExit(f"[ERROR] 找不到 logo.png: {logo}")

    print("=" * 72)
    print(" biliandout PyInstaller 构建（临时 Spec，彻底隔离）")
    print("=" * 72)

    # ---------- 强制清理 dist/build（不动你的项目内 spec，但也不会读取它） ----------
    for d in (DIST_DIR, BUILD_DIR):
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
            print(f"[CLEAN] 删除 {d}")

    RELEASE_DIR.mkdir(exist_ok=True)

    # ---------- 临时目录：放 ico + 临时 spec ----------
    temp_dir = Path(tempfile.mkdtemp(prefix="biliandout-build-"))
    try:
        icon_ico = temp_dir / "app.ico"
        if not convert_png_to_ico(logo, icon_ico):
            icon_ico = None

        temp_spec = temp_dir / "temp_build.spec"
        write_temp_spec(temp_spec, entry=entry, logo=logo, icon_ico=icon_ico)

        # ---------- 用 spec 构建（关键：此处只传 spec，彻底避开 CLI 合并规则） ----------
        cmd = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            f"--distpath={DIST_DIR}",
            f"--workpath={BUILD_DIR}",
            str(temp_spec),
        ]

        print("\n[CMD]")
        for a in cmd:
            print(" ", a)
        print()

        subprocess.run(cmd, cwd=PROJECT_ROOT, check=True)

    except subprocess.CalledProcessError as e:
        raise SystemExit(f"[ERROR] PyInstaller 构建失败: {e}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    # ---------- 校验输出 ----------
    exe_path = DIST_DIR / f"{APP_NAME}.exe"
    if not exe_path.exists():
        # spec 走的是 COLLECT，onefile 时 EXE 会在 dist 根；若没生成说明构建失败或名称不一致
        raise SystemExit(f"[ERROR] 未生成 exe: {exe_path}")

    size_mb = exe_path.stat().st_size / 1024 / 1024
    print(f"[OK] 构建成功: {exe_path} ({size_mb:.2f} MB)")

    # ---------- 发布 ----------
    release_exe = RELEASE_DIR / exe_path.name
    shutil.copy2(exe_path, release_exe)

    readme_text = f"""Android哔哩哔哩视频导出器 (biliandout)

作者: WaterRun
项目: https://github.com/Water-Run/biliandout
构建时间: {datetime.now():%Y-%m-%d %H:%M:%S}

说明:
- Windows 64 位单文件可执行程序
- 已完整打包 biliffm4s（含 ffmpeg / dll）
- 已打包运行时 logo.png
"""

    zip_path = RELEASE_DIR / "biliandout.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(release_exe, release_exe.name)
        zf.writestr("README.txt", readme_text)

    print(f"[OK] 发布目录: {RELEASE_DIR}")
    for f in RELEASE_DIR.iterdir():
        print(f"  - {f.name}")


if __name__ == "__main__":
    build()
