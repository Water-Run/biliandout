"""
biliandout 构建脚本
使用 PyInstaller 将应用打包为单文件可执行程序
"""

import subprocess
import sys
import shutil
from pathlib import Path


def build():
    """执行构建"""
    # 路径设置
    project_root = Path(__file__).parent
    source_dir = project_root / "biliandout"
    main_script = source_dir / "biliandout.py"
    icon_file = source_dir / "logo.png"

    # 输出目录
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"

    # 检查源文件
    if not main_script.exists():
        print(f"错误: 找不到主脚本 {main_script}")
        sys.exit(1)

    if not icon_file.exists():
        print(f"警告: 找不到图标文件 {icon_file}")

    # 清理旧的构建文件
    print("清理旧的构建文件...")
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        shutil.rmtree(build_dir)

    # 构建 PyInstaller 命令
    pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",  # 单文件模式
        "--windowed",  # 无控制台窗口
        "--name", "Android哔哩哔哩视频导出器",
        "--add-data", f"{icon_file};.",  # 添加图标文件
        "--hidden-import", "biliffm4s",
        "--clean",  # 清理临时文件
        "--noconfirm",  # 不询问确认
    ]

    # 如果图标存在，设置为窗口图标（需要.ico格式，这里跳过）
    # 如果有.ico文件可以添加: "--icon", str(icon_file.with_suffix('.ico')),

    # 添加主脚本
    pyinstaller_args.append(str(main_script))

    # 执行构建
    print("开始构建...")
    print(f"命令: {' '.join(pyinstaller_args)}")

    try:
        result = subprocess.run(pyinstaller_args, check=True)
        print("\n构建成功!")
        print(f"输出文件: {dist_dir / 'Android哔哩哔哩视频导出器.exe'}")
    except subprocess.CalledProcessError as e:
        print(f"\n构建失败: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("\n错误: 未找到 PyInstaller，请先安装: pip install pyinstaller")
        sys.exit(1)

    # 创建发布包
    print("\n创建发布包...")
    release_dir = project_root / "release"
    release_dir.mkdir(exist_ok=True)

    exe_file = dist_dir / "Android哔哩哔哩视频导出器.exe"
    if exe_file.exists():
        # 复制到 release 目录
        shutil.copy(exe_file, release_dir / "Android哔哩哔哩视频导出器.exe")

        # 创建 RAR 压缩包（如果有 rar 命令）
        try:
            rar_file = release_dir / "biliandout.rar"
            subprocess.run([
                "rar", "a", "-ep1", str(rar_file), str(exe_file)
            ], check=True, capture_output=True)
            print(f"已创建压缩包: {rar_file}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            # 尝试使用 zip
            try:
                import zipfile
                zip_file = release_dir / "biliandout.zip"
                with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
                    zf.write(exe_file, exe_file.name)
                print(f"已创建压缩包: {zip_file}")
            except Exception as e:
                print(f"无法创建压缩包: {e}")

    print("\n构建完成!")


if __name__ == "__main__":
    build()