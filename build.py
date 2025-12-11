"""
biliandout 构建脚本
使用 PyInstaller 将应用打包为单文件可执行程序
运行: python build.py
"""

import subprocess
import sys
import shutil
import tempfile
import zipfile
from pathlib import Path
from datetime import datetime


def convert_png_to_ico(png_path: Path, ico_path: Path) -> bool:
    """
    将 PNG 转换为高质量 ICO（多尺寸）
    """
    try:
        from PIL import Image

        img = Image.open(png_path).convert("RGBA")

        size = min(img.width, img.height)
        left = (img.width - size) // 2
        top = (img.height - size) // 2
        img = img.crop((left, top, left + size, top + size))

        sizes = [256, 128, 64, 48, 32, 24, 16]

        icons = [img.resize((s, s), Image.Resampling.LANCZOS) for s in sizes]

        img.save(ico_path, format="ICO", sizes=[(s, s) for s in sizes])

        print(f"图标转换成功: {ico_path}")
        return True

    except Exception as e:
        print(f"图标转换失败: {e}")
        return False


def build():
    """执行构建"""
    project_root = Path(__file__).parent
    source_dir = project_root / "biliandout"
    main_script = source_dir / "biliandout.py"
    icon_png = source_dir / "logo.png"

    dist_dir = project_root / "dist"
    build_dir = project_root / "build"
    release_dir = project_root / "_release"

    app_name = "Android哔哩哔哩视频导出器"

    if not main_script.exists():
        print(f"错误: 找不到主脚本 {main_script}")
        sys.exit(1)

    if not icon_png.exists():
        print(f"错误: 找不到图标文件 {icon_png}")
        sys.exit(1)

    print("=" * 50)
    print("清理旧的构建文件...")
    print("=" * 50)

    for dir_path in [dist_dir, build_dir]:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"已删除: {dir_path}")

    print("\n" + "=" * 50)
    print("转换图标文件...")
    print("=" * 50)

    temp_dir = Path(tempfile.mkdtemp())
    temp_ico_path = temp_dir / "logo.ico"
    icon_ico = None

    if convert_png_to_ico(icon_png, temp_ico_path):
        icon_ico = temp_ico_path
    else:
        print("将继续构建，但不设置EXE图标")

    print("\n" + "=" * 50)
    print("开始PyInstaller构建...")
    print("=" * 50)

    pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", app_name,
        "--clean",
        "--noconfirm",
        f"--distpath={dist_dir}",
        f"--workpath={build_dir}",
        f"--specpath={project_root}",
    ]

    if icon_png.exists():
        pyinstaller_args.extend([
            "--add-data", f"{icon_png};."
        ])

    if icon_ico and icon_ico.exists():
        pyinstaller_args.extend([
            "--icon", str(icon_ico)
        ])

    hidden_imports = [
        "biliffm4s",
        "PyQt6",
        "PyQt6.QtWidgets",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
    ]

    for module in hidden_imports:
        pyinstaller_args.extend(["--hidden-import", module])

    pyinstaller_args.append(str(main_script))

    print("\n构建命令:")
    for i, arg in enumerate(pyinstaller_args):
        if i == 0:
            print(f"  {arg} \\")
        elif i == len(pyinstaller_args) - 1:
            print(f"    {arg}")
        else:
            print(f"    {arg} \\")
    print()

    try:
        result = subprocess.run(
            pyinstaller_args,
            check=True,
            cwd=project_root
        )
        print("\n构建成功!")

    except subprocess.CalledProcessError as e:
        print(f"\n构建失败: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("\n错误: 未找到 PyInstaller")
        print("安装方法: pip install pyinstaller")
        sys.exit(1)
    finally:
        if temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

    exe_file = dist_dir / f"{app_name}.exe"
    if not exe_file.exists():
        print(f"\n错误: 未找到输出文件 {exe_file}")
        sys.exit(1)

    exe_size_mb = exe_file.stat().st_size / (1024 * 1024)
    print(f"\n输出文件: {exe_file}")
    print(f"文件大小: {exe_size_mb:.2f} MB")

    print("\n" + "=" * 50)
    print("创建发布包...")
    print("=" * 50)

    release_dir.mkdir(exist_ok=True)

    release_exe = release_dir / f"{app_name}.exe"
    shutil.copy2(exe_file, release_exe)
    print(f"已复制: {release_exe}")

    # 生成 README.txt 内容
    build_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    readme_content = f"""Android哔哩哔哩视频导出器(biliandout): 双击Android哔哩哔哩视频导出器.exe运行程序
文档: https://github.com/Water-Run/biliandout
作者: WaterRun
时间: {build_time}
"""

    # 创建临时 README.txt 文件
    readme_file = release_dir / "README.txt"
    readme_file.write_text(readme_content, encoding="utf-8")
    print(f"已创建: {readme_file}")

    try:
        zip_file = release_dir / "biliandout.zip"

        # 删除旧的 zip 文件（如果存在）
        if zip_file.exists():
            zip_file.unlink()

        with zipfile.ZipFile(str(zip_file), 'w', zipfile.ZIP_DEFLATED) as zf:
            # 使用 arcname 指定压缩包内的文件名
            zf.write(str(release_exe), arcname=f"{app_name}.exe")
            zf.write(str(readme_file), arcname="README.txt")

        zip_size_mb = zip_file.stat().st_size / (1024 * 1024)
        print(f"已创建: {zip_file} ({zip_size_mb:.2f} MB)")

        # 删除临时 README.txt 文件
        readme_file.unlink()
        print(f"已清理临时文件: {readme_file}")

    except Exception as e:
        print(f"无法创建ZIP压缩包: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 50)
    print("构建完成!")
    print("=" * 50)
    print(f"\n发布文件位于: {release_dir}")
    print("\n文件列表:")
    for f in release_dir.iterdir():
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"  {f.name} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    build()