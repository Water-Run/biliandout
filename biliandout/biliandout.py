"""
Android哔哩哔哩视频导出器 (biliandout)
一个PyQT Windows桌面端图形应用，可自动读取连接至计算机的安卓设备上的哔哩哔哩缓存视频，并导出为.mp4
"""

import sys
import os
import json
import subprocess
import ctypes
from ctypes import wintypes
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox, QProgressBar, QGroupBox, QFrame,
    QDialog, QTextBrowser, QStatusBar, QSplitter, QToolBar,
    QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread, QSize
from PyQt6.QtGui import QIcon, QPixmap, QFont, QPalette, QColor, QAction

import biliffm4s

# ============================================================
# 配置: 哔哩哔哩源模板 (字典结构, 便于扩展)
# ============================================================
BILI_SOURCES: dict[str, dict] = {
    "default": {
        "package": "tv.danmaku.bili",
        "name": "哔哩哔哩",
        "description": "官方正式版"
    },
    "concept": {
        "package": "com.bilibili.app.blue",
        "name": "哔哩哔哩概念版",
        "description": "概念测试版"
    },
    # 可继续添加更多版本
    # "hd": {
    #     "package": "tv.danmaku.bilibilihd",
    #     "name": "哔哩哔哩HD",
    #     "description": "平板HD版"
    # },
    # "international": {
    #     "package": "com.bilibili.app.in",
    #     "name": "bilibili国际版",
    #     "description": "海外版本"
    # },
}

# ============================================================
# 样式配置
# ============================================================
COLORS = {
    "bili_pink": "#fb7299",
    "bili_pink_light": "#fc8bab",
    "bili_pink_dark": "#e85c7a",
    "ffmpeg_green": "#5cb85c",
    "ffmpeg_green_light": "#7cc67c",
    "ffmpeg_green_dark": "#4a9a4a",
    "background": "#f5f5f5",
    "card_bg": "#ffffff",
    "text_primary": "#222222",
    "text_secondary": "#666666",
    "border": "#dddddd",
}

STYLESHEET = f"""
QMainWindow {{
    background-color: {COLORS["background"]};
}}

QGroupBox {{
    font-weight: bold;
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 10px;
    background-color: {COLORS["card_bg"]};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 8px;
    color: {COLORS["text_primary"]};
}}

QPushButton {{
    background-color: {COLORS["card_bg"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 6px 16px;
    color: {COLORS["text_primary"]};
}}

QPushButton:hover {{
    background-color: #e8e8e8;
    border-color: #cccccc;
}}

QPushButton:pressed {{
    background-color: #d8d8d8;
}}

QPushButton:disabled {{
    background-color: #f0f0f0;
    color: #aaaaaa;
}}

QPushButton#primaryBtn {{
    background-color: {COLORS["bili_pink"]};
    color: white;
    border: none;
    font-weight: bold;
    padding: 8px 24px;
}}

QPushButton#primaryBtn:hover {{
    background-color: {COLORS["bili_pink_light"]};
}}

QPushButton#primaryBtn:pressed {{
    background-color: {COLORS["bili_pink_dark"]};
}}

QPushButton#primaryBtn:disabled {{
    background-color: #cccccc;
}}

QPushButton#successBtn {{
    background-color: {COLORS["ffmpeg_green"]};
    color: white;
    border: none;
    font-weight: bold;
}}

QPushButton#successBtn:hover {{
    background-color: {COLORS["ffmpeg_green_light"]};
}}

QPushButton#successBtn:pressed {{
    background-color: {COLORS["ffmpeg_green_dark"]};
}}

QComboBox {{
    background-color: {COLORS["card_bg"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 4px 8px;
    min-width: 120px;
}}

QComboBox:hover {{
    border-color: {COLORS["bili_pink"]};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QListWidget {{
    background-color: {COLORS["card_bg"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    outline: none;
}}

QListWidget::item {{
    padding: 8px;
    border-bottom: 1px solid #eeeeee;
}}

QListWidget::item:selected {{
    background-color: #fff0f5;
    color: {COLORS["text_primary"]};
}}

QListWidget::item:hover {{
    background-color: #fafafa;
}}

QProgressBar {{
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    text-align: center;
    background-color: #e0e0e0;
}}

QProgressBar::chunk {{
    background-color: {COLORS["ffmpeg_green"]};
    border-radius: 3px;
}}

QStatusBar {{
    background-color: {COLORS["card_bg"]};
    border-top: 1px solid {COLORS["border"]};
}}

QLabel#pathLabel {{
    color: {COLORS["bili_pink"]};
    padding: 4px;
}}

QLabel#titleLabel {{
    font-size: 14px;
    font-weight: bold;
    color: {COLORS["text_primary"]};
}}

QLabel#subtitleLabel {{
    font-size: 11px;
    color: {COLORS["text_secondary"]};
}}

QToolBar {{
    background-color: {COLORS["card_bg"]};
    border-bottom: 1px solid {COLORS["border"]};
    spacing: 8px;
    padding: 4px;
}}

QFrame#separator {{
    background-color: {COLORS["border"]};
}}
"""


# ============================================================
# 数据结构
# ============================================================
@dataclass
class CachedVideo:
    """缓存视频信息"""
    folder_path: Path
    video_path: Path
    audio_path: Path
    title: str = "未知标题"
    part_title: str = ""
    size_mb: float = 0.0
    bvid: str = ""
    quality: str = ""

    @property
    def display_title(self) -> str:
        if self.part_title and self.part_title != self.title:
            return f"{self.title} - {self.part_title}"
        return self.title

    @property
    def size_display(self) -> str:
        if self.size_mb >= 1024:
            return f"{self.size_mb / 1024:.2f} GB"
        return f"{self.size_mb:.2f} MB"


# ============================================================
# Windows MTP 设备访问
# ============================================================
class MTPDeviceScanner:
    """MTP设备扫描器 - 通过Windows Shell访问便携设备"""

    @staticmethod
    def get_connected_devices() -> list[tuple[str, str]]:
        """
        获取已连接的便携设备列表
        返回: [(device_path, device_name), ...]
        """
        devices = []

        try:
            import win32com.client
            shell = win32com.client.Dispatch("Shell.Application")
            namespace = shell.NameSpace(17)  # 17 = My Computer

            for item in namespace.Items():
                # 检查是否是便携设备 (通过路径特征判断)
                item_path = item.Path

                # MTP设备路径通常以 "::" 开头或包含特殊标识
                if "::{" in item_path or item.IsFolder:
                    # 尝试访问设备内容
                    try:
                        folder = shell.NameSpace(item_path)
                        if folder:
                            # 检查是否有Android目录结构
                            for sub_item in folder.Items():
                                if sub_item.Name.lower() in ["内部存储", "internal storage", "内部共享存储", "内置存储"]:
                                    android_path = f"{item_path}\\{sub_item.Name}\\Android\\data"
                                    # 验证是否有哔哩哔哩目录
                                    for source_key, source_info in BILI_SOURCES.items():
                                        bili_check = f"{android_path}\\{source_info['package']}"
                                        try:
                                            test_folder = shell.NameSpace(bili_check)
                                            if test_folder:
                                                devices.append((item_path, item.Name))
                                                break
                                        except:
                                            continue
                                    break
                    except:
                        continue
        except ImportError:
            # 如果win32com不可用,回退到驱动器扫描
            devices = MTPDeviceScanner._scan_drive_letters()

        # 同时扫描传统驱动器盘符(USB调试模式)
        drive_devices = MTPDeviceScanner._scan_drive_letters()
        for dev in drive_devices:
            if dev not in devices:
                devices.append(dev)

        return devices

    @staticmethod
    def _scan_drive_letters() -> list[tuple[str, str]]:
        """扫描驱动器盘符(用于USB调试模式或文件传输模式)"""
        devices = []

        for drive_letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
            drive_path = Path(f"{drive_letter}:/")
            if not drive_path.exists():
                continue

            android_path = drive_path / "Android" / "data"
            if android_path.exists():
                for source_key, source_info in BILI_SOURCES.items():
                    bili_path = android_path / source_info["package"] / "download"
                    if bili_path.exists():
                        device_name = f"存储设备 ({drive_letter}:)"
                        device_tuple = (f"{drive_letter}:", device_name)
                        if device_tuple not in devices:
                            devices.append(device_tuple)
                        break

        return devices

    @staticmethod
    def scan_cached_videos(device_path: str, source_key: str) -> list[CachedVideo]:
        """扫描指定设备和源的缓存视频"""
        videos = []
        source_info = BILI_SOURCES.get(source_key)
        if not source_info:
            return videos

        # 判断是MTP路径还是驱动器路径
        if len(device_path) == 2 and device_path[1] == ":":
            # 驱动器盘符
            download_path = Path(f"{device_path}/Android/data/{source_info['package']}/download")
            if download_path.exists():
                videos = MTPDeviceScanner._scan_directory(download_path)
        else:
            # MTP路径 - 使用Shell API
            try:
                import win32com.client
                shell = win32com.client.Dispatch("Shell.Application")

                # 构建完整路径
                for storage_name in ["内部存储", "Internal storage", "内部共享存储", "内置存储"]:
                    full_path = f"{device_path}\\{storage_name}\\Android\\data\\{source_info['package']}\\download"
                    try:
                        folder = shell.NameSpace(full_path)
                        if folder:
                            videos = MTPDeviceScanner._scan_mtp_folder(shell, folder, full_path)
                            break
                    except:
                        continue
            except ImportError:
                pass

        return videos

    @staticmethod
    def _scan_directory(download_path: Path) -> list[CachedVideo]:
        """扫描本地目录中的缓存视频"""
        videos = []

        if not download_path.exists():
            return videos

        for video_folder in download_path.iterdir():
            if not video_folder.is_dir():
                continue

            found_videos = MTPDeviceScanner._find_m4s_pairs(video_folder)

            for folder_path, video_path, audio_path in found_videos:
                title, part_title, bvid, quality = MTPDeviceScanner._read_video_info(folder_path)
                size_mb = (video_path.stat().st_size + audio_path.stat().st_size) / (1024 * 1024)

                videos.append(CachedVideo(
                    folder_path=folder_path,
                    video_path=video_path,
                    audio_path=audio_path,
                    title=title,
                    part_title=part_title,
                    size_mb=size_mb,
                    bvid=bvid,
                    quality=quality
                ))

        return videos

    @staticmethod
    def _scan_mtp_folder(shell, folder, base_path: str) -> list[CachedVideo]:
        """扫描MTP文件夹中的缓存视频"""
        videos = []

        try:
            for item in folder.Items():
                if item.IsFolder:
                    subfolder_path = f"{base_path}\\{item.Name}"
                    # 递归查找m4s文件
                    found = MTPDeviceScanner._find_mtp_m4s_pairs(shell, subfolder_path, item)
                    videos.extend(found)
        except:
            pass

        return videos

    @staticmethod
    def _find_mtp_m4s_pairs(shell, path: str, folder_item) -> list[CachedVideo]:
        """在MTP文件夹中递归查找m4s文件对"""
        videos = []

        try:
            folder = shell.NameSpace(path)
            if not folder:
                return videos

            has_video = False
            has_audio = False

            for item in folder.Items():
                if item.Name == "video.m4s":
                    has_video = True
                elif item.Name == "audio.m4s":
                    has_audio = True
                elif item.IsFolder:
                    # 递归子文件夹
                    sub_path = f"{path}\\{item.Name}"
                    videos.extend(MTPDeviceScanner._find_mtp_m4s_pairs(shell, sub_path, item))

            if has_video and has_audio:
                # 读取视频信息
                title, part_title, bvid, quality = MTPDeviceScanner._read_mtp_video_info(shell, path)

                # 这里需要将MTP路径转换为可用路径
                # 注意: MTP文件需要复制到本地才能处理
                videos.append(CachedVideo(
                    folder_path=Path(path),  # MTP路径
                    video_path=Path(f"{path}\\video.m4s"),
                    audio_path=Path(f"{path}\\audio.m4s"),
                    title=title,
                    part_title=part_title,
                    size_mb=0,  # MTP难以直接获取大小
                    bvid=bvid,
                    quality=quality
                ))
        except:
            pass

        return videos

    @staticmethod
    def _find_m4s_pairs(folder: Path) -> list[tuple[Path, Path, Path]]:
        """递归查找文件夹中的m4s文件对"""
        pairs = []

        video_m4s = folder / "video.m4s"
        audio_m4s = folder / "audio.m4s"

        if video_m4s.exists() and audio_m4s.exists():
            pairs.append((folder, video_m4s, audio_m4s))

        try:
            for subfolder in folder.iterdir():
                if subfolder.is_dir():
                    pairs.extend(MTPDeviceScanner._find_m4s_pairs(subfolder))
        except PermissionError:
            pass

        return pairs

    @staticmethod
    def _read_video_info(folder: Path) -> tuple[str, str, str, str]:
        """从entry.json读取视频信息"""
        title = "未知标题"
        part_title = ""
        bvid = ""
        quality = ""

        current = folder
        for _ in range(5):
            entry_json = current / "entry.json"
            if entry_json.exists():
                try:
                    with open(entry_json, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        title = data.get("title", title)
                        bvid = data.get("bvid", "")

                        page_data = data.get("page_data", {})
                        part_title = page_data.get("part", "")

                        # 获取画质信息
                        quality_id = data.get("quality", 0)
                        quality_map = {
                            120: "4K",
                            116: "1080P60",
                            112: "1080P+",
                            80: "1080P",
                            64: "720P",
                            32: "480P",
                            16: "360P",
                        }
                        quality = quality_map.get(quality_id, f"{quality_id}P" if quality_id else "")
                        break
                except (json.JSONDecodeError, IOError):
                    pass

            parent = current.parent
            if parent == current:
                break
            current = parent

        return title, part_title, bvid, quality

    @staticmethod
    def _read_mtp_video_info(shell, path: str) -> tuple[str, str, str, str]:
        """从MTP路径读取视频信息"""
        title = "未知标题"
        part_title = ""
        bvid = ""
        quality = ""

        # 向上查找entry.json
        current_path = path
        for _ in range(5):
            try:
                folder = shell.NameSpace(current_path)
                if folder:
                    for item in folder.Items():
                        if item.Name == "entry.json":
                            # MTP文件需要复制到临时目录读取
                            # 这里简化处理,实际使用时需要实现文件复制
                            pass
                current_path = "\\".join(current_path.split("\\")[:-1])
            except:
                break

        return title, part_title, bvid, quality


# ============================================================
# 转换工作线程
# ============================================================
class ConvertWorker(QObject):
    """视频转换工作线程"""
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(int, int)
    error = pyqtSignal(str)

    def __init__(self, videos: list[CachedVideo], output_dir: Path):
        super().__init__()
        self.videos = videos
        self.output_dir = output_dir
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        success_count = 0
        total = len(self.videos)

        for i, video in enumerate(self.videos):
            if self._cancelled:
                break

            self.progress.emit(i + 1, total, f"正在转换: {video.display_title}")

            safe_title = self._sanitize_filename(video.display_title)
            output_path = self.output_dir / f"{safe_title}.mp4"

            counter = 1
            while output_path.exists():
                output_path = self.output_dir / f"{safe_title}_{counter}.mp4"
                counter += 1

            try:
                result = biliffm4s.combine(str(video.folder_path), str(output_path))
                if result:
                    success_count += 1
            except Exception as e:
                self.error.emit(f"转换失败: {video.display_title} - {str(e)}")

        self.finished.emit(success_count, total)

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """清理文件名中的非法字符"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, "_")
        return filename[:200]


# ============================================================
# 视频列表项组件
# ============================================================
class VideoListItem(QWidget):
    """视频列表项自定义组件"""

    def __init__(self, video: CachedVideo, parent=None):
        super().__init__(parent)
        self.video = video
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        # 标题行
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)

        title_label = QLabel(self.video.display_title)
        title_label.setObjectName("titleLabel")
        title_label.setWordWrap(True)
        title_layout.addWidget(title_label, 1)

        # 画质标签
        if self.video.quality:
            quality_label = QLabel(self.video.quality)
            quality_label.setStyleSheet(f"""
                background-color: {COLORS["ffmpeg_green"]};
                color: white;
                padding: 2px 6px;
                border-radius: 3px;
                font-size: 10px;
            """)
            title_layout.addWidget(quality_label)

        layout.addLayout(title_layout)

        # 信息行
        info_layout = QHBoxLayout()
        info_layout.setSpacing(16)

        size_label = QLabel(f"大小: {self.video.size_display}")
        size_label.setObjectName("subtitleLabel")
        info_layout.addWidget(size_label)

        if self.video.bvid:
            bvid_label = QLabel(f"BV号: {self.video.bvid}")
            bvid_label.setObjectName("subtitleLabel")
            info_layout.addWidget(bvid_label)

        info_layout.addStretch()
        layout.addLayout(info_layout)


# ============================================================
# 关于对话框
# ============================================================
class AboutDialog(QDialog):
    """关于对话框"""

    def __init__(self, parent=None, icon_path: Path = None):
        super().__init__(parent)
        self.setWindowTitle("关于")
        self.setFixedSize(480, 420)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # 头部区域
        header_layout = QHBoxLayout()

        if icon_path and icon_path.exists():
            logo_label = QLabel()
            pixmap = QPixmap(str(icon_path))
            scaled_pixmap = pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
            header_layout.addWidget(logo_label)

        title_layout = QVBoxLayout()
        title_label = QLabel("Android哔哩哔哩视频导出器")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_layout.addWidget(title_label)

        version_label = QLabel("版本 1.0.0")
        version_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        title_layout.addWidget(version_label)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("separator")
        layout.addWidget(separator)

        # 信息区域
        info_html = f"""
        <style>
            body {{ font-family: "Microsoft YaHei", sans-serif; }}
            .label {{ color: {COLORS["text_secondary"]}; }}
            .value {{ color: {COLORS["text_primary"]}; }}
            a {{ color: {COLORS["bili_pink"]}; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
        </style>
        <table cellspacing="8">
            <tr>
                <td class="label">作者:</td>
                <td class="value">WaterRun</td>
            </tr>
            <tr>
                <td class="label">协助:</td>
                <td class="value">Claude Opus 4.5, Nano-Banana-Pro</td>
            </tr>
            <tr>
                <td class="label">技术栈:</td>
                <td class="value">Python + PyQt6 + PyInstaller</td>
            </tr>
            <tr>
                <td class="label">许可证:</td>
                <td class="value">GNU General Public License v3.0</td>
            </tr>
        </table>
        <br>
        <p><b>项目链接</b></p>
        <p>
            <a href="https://github.com/Water-Run/biliandout">GitHub仓库</a> · 
            <a href="https://github.com/Water-Run/biliandout/releases">下载发布</a>
        </p>
        <br>
        <p><b>依赖项目</b></p>
        <p>
            <a href="https://github.com/Water-Run/-m4s-Python-biliffm4s">biliffm4s</a> · 
            <a href="https://github.com/FFmpeg/FFmpeg">FFmpeg</a>
        </p>
        """

        info_browser = QTextBrowser()
        info_browser.setHtml(info_html)
        info_browser.setOpenExternalLinks(True)
        info_browser.setStyleSheet("""
            QTextBrowser {
                background-color: transparent;
                border: none;
            }
        """)
        layout.addWidget(info_browser, 1)

        # 关闭按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        close_btn = QPushButton("关闭")
        close_btn.setFixedWidth(100)
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)


# ============================================================
# 主窗口
# ============================================================
class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()

        self.videos: list[CachedVideo] = []
        self.output_dir: Path = Path.home() / "Desktop"
        self.convert_thread: Optional[QThread] = None
        self.convert_worker: Optional[ConvertWorker] = None
        self.current_device: Optional[str] = None

        # 获取图标路径
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS)
        else:
            base_path = Path(__file__).parent

        self.icon_path = base_path / "logo.png"

        self._setup_ui()
        self._connect_signals()
        self._refresh_devices()

    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("Android哔哩哔哩视频导出器")
        self.setFixedSize(512, 512)

        if self.icon_path.exists():
            self.setWindowIcon(QIcon(str(self.icon_path)))

        # 应用样式
        self.setStyleSheet(STYLESHEET)

        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # ========== 工具栏区域 ==========
        toolbar_group = QGroupBox("设备与数据源")
        toolbar_layout = QVBoxLayout(toolbar_group)
        toolbar_layout.setSpacing(8)

        # 设备行
        device_row = QHBoxLayout()
        device_row.addWidget(QLabel("设备:"))

        self.device_combo = QComboBox()
        self.device_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        device_row.addWidget(self.device_combo)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setFixedWidth(60)
        device_row.addWidget(self.refresh_btn)

        toolbar_layout.addLayout(device_row)

        # 源行
        source_row = QHBoxLayout()
        source_row.addWidget(QLabel("数据源:"))

        self.source_combo = QComboBox()
        for key, info in BILI_SOURCES.items():
            self.source_combo.addItem(f"{info['name']} ({info['description']})", key)
        self.source_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        source_row.addWidget(self.source_combo)

        self.scan_btn = QPushButton("扫描")
        self.scan_btn.setObjectName("successBtn")
        self.scan_btn.setFixedWidth(60)
        source_row.addWidget(self.scan_btn)

        toolbar_layout.addLayout(source_row)
        main_layout.addWidget(toolbar_group)

        # ========== 视频列表区域 ==========
        list_group = QGroupBox("缓存视频")
        list_layout = QVBoxLayout(list_group)

        self.video_list = QListWidget()
        self.video_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.video_list.setMinimumHeight(180)
        list_layout.addWidget(self.video_list)

        # 列表操作栏
        list_actions = QHBoxLayout()

        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.setFixedWidth(60)
        list_actions.addWidget(self.select_all_btn)

        self.deselect_all_btn = QPushButton("取消全选")
        self.deselect_all_btn.setFixedWidth(80)
        list_actions.addWidget(self.deselect_all_btn)

        list_actions.addStretch()

        self.video_count_label = QLabel("共 0 个视频")
        self.video_count_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        list_actions.addWidget(self.video_count_label)

        list_layout.addLayout(list_actions)
        main_layout.addWidget(list_group, 1)

        # ========== 输出设置区域 ==========
        output_group = QGroupBox("输出设置")
        output_layout = QHBoxLayout(output_group)

        output_layout.addWidget(QLabel("输出目录:"))

        self.output_path_label = QLabel(str(self.output_dir))
        self.output_path_label.setObjectName("pathLabel")
        self.output_path_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        output_layout.addWidget(self.output_path_label)

        self.browse_btn = QPushButton("浏览...")
        self.browse_btn.setFixedWidth(70)
        output_layout.addWidget(self.browse_btn)

        main_layout.addWidget(output_group)

        # ========== 进度条 ==========
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        main_layout.addWidget(self.progress_bar)

        # ========== 操作按钮 ==========
        action_layout = QHBoxLayout()

        self.about_btn = QPushButton("关于")
        self.about_btn.setFixedWidth(70)
        action_layout.addWidget(self.about_btn)

        action_layout.addStretch()

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setFixedWidth(70)
        action_layout.addWidget(self.cancel_btn)

        self.convert_btn = QPushButton("导出选中视频")
        self.convert_btn.setObjectName("primaryBtn")
        self.convert_btn.setFixedWidth(140)
        action_layout.addWidget(self.convert_btn)

        main_layout.addLayout(action_layout)

        # ========== 状态栏 ==========
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪 - 连接Android设备后点击刷新")

    def _connect_signals(self):
        """连接信号"""
        self.refresh_btn.clicked.connect(self._refresh_devices)
        self.scan_btn.clicked.connect(self._scan_videos)
        self.about_btn.clicked.connect(self._show_about)
        self.browse_btn.clicked.connect(self._browse_output_dir)
        self.convert_btn.clicked.connect(self._start_convert)
        self.cancel_btn.clicked.connect(self._cancel_convert)
        self.select_all_btn.clicked.connect(self._select_all)
        self.deselect_all_btn.clicked.connect(self._deselect_all)
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)

    def _refresh_devices(self):
        """刷新设备列表"""
        self.device_combo.clear()
        self.videos.clear()
        self.video_list.clear()
        self.video_count_label.setText("共 0 个视频")

        devices = MTPDeviceScanner.get_connected_devices()

        if not devices:
            self.device_combo.addItem("未检测到设备", None)
            self.status_bar.showMessage("未检测到已连接的Android设备 - 请确保设备已开启USB调试或文件传输模式")
            self.scan_btn.setEnabled(False)
        else:
            for device_path, device_name in devices:
                self.device_combo.addItem(device_name, device_path)
            self.status_bar.showMessage(f"检测到 {len(devices)} 个设备")
            self.scan_btn.setEnabled(True)

    def _on_device_changed(self, index: int):
        """设备切换回调"""
        self.current_device = self.device_combo.currentData()
        self.videos.clear()
        self.video_list.clear()
        self.video_count_label.setText("共 0 个视频")

    def _scan_videos(self):
        """扫描缓存视频"""
        device_path = self.device_combo.currentData()
        if not device_path:
            QMessageBox.warning(self, "提示", "未选择有效设备")
            return

        source_key = self.source_combo.currentData()

        self.status_bar.showMessage("正在扫描...")
        self.scan_btn.setEnabled(False)
        QApplication.processEvents()

        try:
            self.videos = MTPDeviceScanner.scan_cached_videos(device_path, source_key)
            self._update_video_list()

            if self.videos:
                self.status_bar.showMessage(f"扫描完成 - 找到 {len(self.videos)} 个缓存视频")
            else:
                self.status_bar.showMessage("扫描完成 - 未找到缓存视频")
        except Exception as e:
            self.status_bar.showMessage(f"扫描出错: {str(e)}")
        finally:
            self.scan_btn.setEnabled(True)

    def _update_video_list(self):
        """更新视频列表"""
        self.video_list.clear()

        for video in self.videos:
            item = QListWidgetItem()
            widget = VideoListItem(video)
            item.setSizeHint(widget.sizeHint())
            self.video_list.addItem(item)
            self.video_list.setItemWidget(item, widget)

        self.video_count_label.setText(f"共 {len(self.videos)} 个视频")

    def _get_selected_videos(self) -> list[CachedVideo]:
        """获取选中的视频"""
        selected = []
        for i in range(self.video_list.count()):
            item = self.video_list.item(i)
            if item.isSelected():
                selected.append(self.videos[i])
        return selected

    def _select_all(self):
        """全选"""
        for i in range(self.video_list.count()):
            self.video_list.item(i).setSelected(True)

    def _deselect_all(self):
        """取消全选"""
        for i in range(self.video_list.count()):
            self.video_list.item(i).setSelected(False)

    def _browse_output_dir(self):
        """浏览输出目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择输出目录", str(self.output_dir)
        )
        if dir_path:
            self.output_dir = Path(dir_path)
            self.output_path_label.setText(str(self.output_dir))

    def _start_convert(self):
        """开始转换"""
        selected_videos = self._get_selected_videos()

        if not selected_videos:
            QMessageBox.warning(self, "提示", "请至少选择一个视频")
            return

        if not self.output_dir.exists():
            QMessageBox.warning(self, "提示", "输出目录不存在")
            return

        self._set_ui_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(selected_videos))
        self.progress_bar.setValue(0)
        self.cancel_btn.setVisible(True)

        self.convert_thread = QThread()
        self.convert_worker = ConvertWorker(selected_videos, self.output_dir)
        self.convert_worker.moveToThread(self.convert_thread)

        self.convert_thread.started.connect(self.convert_worker.run)
        self.convert_worker.progress.connect(self._on_convert_progress)
        self.convert_worker.finished.connect(self._on_convert_finished)
        self.convert_worker.error.connect(self._on_convert_error)

        self.convert_thread.start()

    def _cancel_convert(self):
        """取消转换"""
        if self.convert_worker:
            self.convert_worker.cancel()

    def _on_convert_progress(self, current: int, total: int, message: str):
        """转换进度回调"""
        self.progress_bar.setValue(current)
        self.progress_bar.setFormat(f"{current}/{total}")
        self.status_bar.showMessage(message)

    def _on_convert_finished(self, success_count: int, total_count: int):
        """转换完成回调"""
        self._cleanup_convert_thread()
        self._set_ui_enabled(True)
        self.progress_bar.setVisible(False)
        self.cancel_btn.setVisible(False)

        QMessageBox.information(
            self, "完成",
            f"转换完成\n成功: {success_count}/{total_count}"
        )
        self.status_bar.showMessage(f"转换完成: {success_count}/{total_count}")

    def _on_convert_error(self, error_msg: str):
        """转换错误回调"""
        self.status_bar.showMessage(f"错误: {error_msg}")

    def _cleanup_convert_thread(self):
        """清理转换线程"""
        if self.convert_thread:
            self.convert_thread.quit()
            self.convert_thread.wait()
            self.convert_thread = None
            self.convert_worker = None

    def _set_ui_enabled(self, enabled: bool):
        """设置UI启用状态"""
        self.device_combo.setEnabled(enabled)
        self.source_combo.setEnabled(enabled)
        self.refresh_btn.setEnabled(enabled)
        self.scan_btn.setEnabled(enabled)
        self.browse_btn.setEnabled(enabled)
        self.convert_btn.setEnabled(enabled)
        self.select_all_btn.setEnabled(enabled)
        self.deselect_all_btn.setEnabled(enabled)
        self.video_list.setEnabled(enabled)
        self.about_btn.setEnabled(enabled)

    def _show_about(self):
        """显示关于对话框"""
        dialog = AboutDialog(self, self.icon_path)
        dialog.exec()

    def closeEvent(self, event):
        """关闭事件"""
        if self.convert_thread and self.convert_thread.isRunning():
            reply = QMessageBox.question(
                self, "确认",
                "正在转换中，确定要退出吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return

            self._cancel_convert()
            self._cleanup_convert_thread()

        event.accept()


# ============================================================
# 程序入口
# ============================================================
def main():
    """主函数"""
    # 禁用自动深色模式
    os.environ["QT_QPA_PLATFORM"] = "windows:darkmode=0"

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 强制使用浅色主题
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(COLORS["background"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(COLORS["text_primary"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(COLORS["card_bg"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(COLORS["background"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(COLORS["text_primary"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(COLORS["card_bg"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(COLORS["text_primary"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(COLORS["bili_pink"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("white"))
    app.setPalette(palette)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()