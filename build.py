# build.py
"""
biliandout 构建脚本
使用 PyInstaller 将应用打包为单文件可执行程序
"""

import subprocess
import sys
import shutil
import tempfile
from pathlib import Path


def convert_png_to_ico(png_path: Path, ico_path: Path) -> bool:
    """
    将PNG图标转换为ICO格式
    生成高质量多尺寸图标
    """
    try:
        from PIL import Image

        img = Image.open(png_path)
        
        # 确保源图像是RGBA模式
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # 取最大正方形区域
        size = min(img.width, img.height)
        left = (img.width - size) // 2
        top = (img.height - size) // 2
        img = img.crop((left, top, left + size, top + size))
        
        # 放大到足够大的尺寸以保证质量
        if img.width < 256:
            img = img.resize((256, 256), Image.Resampling.LANCZOS)

        # ICO文件需要的所有标准尺寸
        sizes = [256, 128, 64, 48, 32, 24, 16]
        
        # 创建多尺寸图标列表
        icons = []
        for s in sizes:
            resized = img.resize((s, s), Image.Resampling.LANCZOS)
            icons.append(resized)

        # 保存为ICO格式
        icons[0].save(
            ico_path,
            format='ICO',
            sizes=[(s, s) for s in sizes],
            append_images=icons[1:]
        )

        print(f"图标转换成功: {ico_path}")
        return True

    except ImportError:
        print("错误: 未安装Pillow库")
        print("安装方法: pip install Pillow")
        return False
    except Exception as e:
        print(f"图标转换失败: {e}")
        return False


def build():
    """执行构建"""
    # 路径设置
    project_root = Path(__file__).parent
    source_dir = project_root / "biliandout"
    main_script = source_dir / "biliandout.py"
    icon_png = source_dir / "logo.png"

    # 输出目录
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"
    release_dir = project_root / "_release"

    # 应用名称
    app_name = "Android哔哩哔哩视频导出器"

    # 检查源文件
    if not main_script.exists():
        print(f"错误: 找不到主脚本 {main_script}")
        sys.exit(1)

    if not icon_png.exists():
        print(f"错误: 找不到图标文件 {icon_png}")
        sys.exit(1)

    # 清理旧的构建文件
    print("=" * 50)
    print("清理旧的构建文件...")
    print("=" * 50)

    for dir_path in [dist_dir, build_dir]:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"已删除: {dir_path}")

    # 转换图标
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

    # 构建 PyInstaller 命令
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

    # 添加数据文件
    if icon_png.exists():
        pyinstaller_args.extend([
            "--add-data", f"{icon_png};."
        ])

    # 添加EXE图标
    if icon_ico and icon_ico.exists():
        pyinstaller_args.extend([
            "--icon", str(icon_ico)
        ])

    # 隐式导入
    hidden_imports = [
        "biliffm4s",
        "PyQt6",
        "PyQt6.QtWidgets",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
    ]

    for module in hidden_imports:
        pyinstaller_args.extend(["--hidden-import", module])

    # 添加主脚本
    pyinstaller_args.append(str(main_script))

    # 打印构建命令
    print("\n构建命令:")
    for i, arg in enumerate(pyinstaller_args):
        if i == 0:
            print(f"  {arg} \\")
        elif i == len(pyinstaller_args) - 1:
            print(f"    {arg}")
        else:
            print(f"    {arg} \\")
    print()

    # 执行构建
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
        # 清理临时ICO文件
        if temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

    # 验证输出
    exe_file = dist_dir / f"{app_name}.exe"
    if not exe_file.exists():
        print(f"\n错误: 未找到输出文件 {exe_file}")
        sys.exit(1)

    exe_size_mb = exe_file.stat().st_size / (1024 * 1024)
    print(f"\n输出文件: {exe_file}")
    print(f"文件大小: {exe_size_mb:.2f} MB")

    # 创建发布包
    print("\n" + "=" * 50)
    print("创建发布包...")
    print("=" * 50)

    release_dir.mkdir(exist_ok=True)

    # 复制EXE到发布目录
    release_exe = release_dir / f"{app_name}.exe"
    shutil.copy2(exe_file, release_exe)
    print(f"已复制: {release_exe}")

    # 创建ZIP压缩包
    try:
        import zipfile
        zip_file = release_dir / "biliandout.zip"

        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.write(release_exe, release_exe.name)

        zip_size_mb = zip_file.stat().st_size / (1024 * 1024)
        print(f"已创建: {zip_file} ({zip_size_mb:.2f} MB)")

    except Exception as e:
        print(f"无法创建ZIP压缩包: {e}")

    # 完成
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