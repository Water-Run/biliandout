"""
Android哔哩哔哩视频导出器 (biliandout)
PyQt Windows桌面端图形应用，读取Android设备哔哩哔哩缓存视频并导出为.mp4
GitHub: https://github.com/Water-Run/biliandout
"""

import contextlib
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QSize, Qt, QObject, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QPalette, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSizePolicy,
    QStatusBar,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

import biliffm4s

# ============================================================
# 日志配置
# ============================================================
logger = logging.getLogger("biliandout")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# ============================================================
# 配置常量
# ============================================================
BILI_SOURCES: dict[str, dict[str, str]] = {
    "default": {"package": "tv.danmaku.bili", "name": "哔哩哔哩"},
    "concept": {"package": "com.bilibili.app.blue", "name": "哔哩哔哩概念"},
}

VERSION = "1.0"

COVER_CACHE_DIR = Path(tempfile.gettempdir()) / "biliandout_covers"
COVER_CACHE_DIR.mkdir(parents=True, exist_ok=True)

try:
    CREATE_NO_WINDOW = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
except AttributeError:
    CREATE_NO_WINDOW = 0

# ============================================================
# 工具函数
# ============================================================
def safe_json_load(path: Path) -> dict[str, Any]:
    """安全加载JSON文件，失败时返回空字典。"""
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        logger.debug("读取 JSON 失败 %s: %s", path, exc)
        return {}


def remove_file(path: Path) -> None:
    """安全删除文件，忽略所有错误。"""
    with contextlib.suppress(FileNotFoundError, PermissionError, OSError):
        path.unlink()


def run_command(
    command: list[str],
    *,
    timeout: float | None = None,
    capture_output: bool = True,
    text: bool = True,
) -> subprocess.CompletedProcess[str]:
    """执行命令并隐藏控制台窗口。"""
    return subprocess.run(
        command,
        timeout=timeout,
        creationflags=CREATE_NO_WINDOW,
        capture_output=capture_output,
        text=text,
    )


def format_bytes_to_mb(size_bytes: int) -> float:
    """将字节转换为MB。"""
    return size_bytes / (1024 * 1024)


# ============================================================
# 样式定义
# ============================================================
COLORS = {
    "primary": "#fb7299",
    "primary_hover": "#fc8bab",
    "primary_pressed": "#e85c7a",
    "success": "#5cb85c",
    "success_hover": "#6fca6f",
    "background": "#f5f5f5",
    "surface": "#ffffff",
    "text": "#333333",
    "text_secondary": "#666666",
    "text_muted": "#999999",
    "border": "#e0e0e0",
    "border_focus": "#fb7299",
}

STYLESHEET = f"""
QMainWindow {{
    background-color: {COLORS["background"]};
}}

QGroupBox {{
    font-weight: bold;
    font-size: 11px;
    border: 1px solid {COLORS["border"]};
    border-radius: 5px;
    margin-top: 8px;
    padding: 6px;
    background-color: {COLORS["surface"]};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 3px;
    color: {COLORS["text"]};
}}

QLabel {{
    color: {COLORS["text"]};
    font-size: 11px;
}}

QLabel#mutedLabel {{
    color: {COLORS["text_muted"]};
    font-size: 10px;
}}

QLabel#pathLabel {{
    color: {COLORS["primary"]};
    font-size: 10px;
}}

QLabel#emptyHint {{
    color: {COLORS["text_secondary"]};
    font-size: 11px;
    line-height: 1.5;
}}

QLabel#videoTitleLabel {{
    font-size: 11px;
    font-weight: bold;
    color: {COLORS["text"]};
}}

QLabel#videoInfoLabel {{
    font-size: 10px;
    color: {COLORS["text_secondary"]};
}}

QLabel#loadingStatusLabel {{
    font-size: 10px;
    color: {COLORS["text_secondary"]};
}}

QPushButton {{
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 3px;
    padding: 4px 10px;
    font-size: 11px;
    color: {COLORS["text"]};
    min-height: 22px;
}}

QPushButton:hover {{
    background-color: #f0f0f0;
    border-color: #cccccc;
}}

QPushButton:pressed {{
    background-color: #e0e0e0;
}}

QPushButton:disabled {{
    background-color: #f0f0f0;
    color: #aaaaaa;
    border-color: #e0e0e0;
}}

QPushButton#primaryBtn {{
    background-color: {COLORS["primary"]};
    color: white;
    border: none;
    font-weight: bold;
    padding: 5px 14px;
    font-size: 11px;
    min-height: 24px;
}}

QPushButton#primaryBtn:hover {{
    background-color: {COLORS["primary_hover"]};
}}

QPushButton#primaryBtn:pressed {{
    background-color: {COLORS["primary_pressed"]};
}}

QPushButton#primaryBtn:disabled {{
    background-color: #cccccc;
}}

QPushButton#successBtn {{
    background-color: {COLORS["success"]};
    color: white;
    border: none;
    font-weight: bold;
    min-height: 22px;
}}

QPushButton#successBtn:hover {{
    background-color: {COLORS["success_hover"]};
}}

QPushButton#successBtn:disabled {{
    background-color: #cccccc;
}}

QPushButton#pauseBtn {{
    background-color: #f0ad4e;
    color: white;
    border: none;
    font-weight: bold;
    min-height: 22px;
}}

QPushButton#pauseBtn:hover {{
    background-color: #ec971f;
}}

QComboBox {{
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 3px;
    padding: 4px 8px;
    font-size: 11px;
    color: {COLORS["text"]};
    min-height: 22px;
}}

QComboBox:hover {{
    border-color: {COLORS["border_focus"]};
}}

QComboBox:focus {{
    border-color: {COLORS["border_focus"]};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    selection-background-color: #fff0f5;
    selection-color: {COLORS["text"]};
    outline: none;
    padding: 3px;
}}

QListWidget {{
    background-color: {COLORS["background"]};
    border: none;
    outline: none;
}}

QListWidget::item {{
    margin: 3px 0;
    padding: 0;
    border: none;
}}

QWidget#videoItem {{
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
}}

QWidget#videoItem[selected="true"] {{
    border-color: {COLORS["primary"]};
    background-color: #fff6fa;
}}

QLabel#coverLabel {{
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    background-color: #fdfdfd;
}}

QProgressBar {{
    border: none;
    border-radius: 3px;
    text-align: center;
    background-color: #e8e8e8;
    font-size: 9px;
    min-height: 16px;
    max-height: 16px;
}}

QProgressBar::chunk {{
    background-color: {COLORS["success"]};
    border-radius: 3px;
}}

QProgressBar#scanProgress::chunk {{
    background-color: {COLORS["primary"]};
}}

QStatusBar {{
    background-color: {COLORS["surface"]};
    border-top: 1px solid {COLORS["border"]};
    font-size: 10px;
    color: {COLORS["text_secondary"]};
    padding: 2px;
}}

QTextBrowser {{
    background-color: transparent;
    border: none;
    font-size: 11px;
    color: {COLORS["text"]};
}}

#emptyState {{
    background-color: #fafafa;
    border-radius: 6px;
    border: 1px solid #ebebeb;
    padding: 16px;
}}
"""


# ============================================================
# 数据结构
# ============================================================
@dataclass(slots=True)
class CachedVideo:
    """表示一个缓存的视频文件。"""
    
    folder_path: Path
    video_path: Path
    audio_path: Path
    title: str = "未知标题"
    part_title: str = ""
    size_mb: float = 0.0
    bvid: str = ""
    quality: str = ""
    resolution: str = ""
    frame_rate: str = ""
    cover_path: Path | None = None

    @property
    def display_title(self) -> str:
        """返回显示用的标题。"""
        if self.part_title and self.part_title != self.title:
            return f"{self.title} - {self.part_title}"
        return self.title

    @property
    def size_display(self) -> str:
        """返回格式化的文件大小。"""
        if self.size_mb >= 1024:
            return f"{self.size_mb / 1024:.2f} GB"
        return f"{self.size_mb:.1f} MB"

    @property
    def tech_info(self) -> str:
        """返回技术信息字符串。"""
        parts: list[str] = []
        if self.resolution:
            parts.append(self.resolution)
        if self.frame_rate:
            parts.append(f"{self.frame_rate}fps")
        if self.quality:
            parts.append(self.quality)
        return " · ".join(parts)


class ScanState(Enum):
    """扫描状态枚举。"""
    IDLE = auto()
    LOADING = auto()
    PAUSED = auto()


# ============================================================
# 视频列表项组件
# ============================================================
class VideoListItemWidget(QWidget):
    """视频列表项的自定义Widget。"""
    
    COVER_SIZE = QSize(90, 68)

    def __init__(self, video: CachedVideo, parent: QWidget | None = None) -> None:
        """初始化视频列表项。"""
        super().__init__(parent)
        self.video = video
        self.setObjectName("videoItem")
        self.setProperty("selected", False)
        self._cover_pixmap: QPixmap | None = None
        self._setup_ui()
        self.update_content(video)

    def _setup_ui(self) -> None:
        """设置UI组件。"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(8)

        self.cover_label = QLabel()
        self.cover_label.setObjectName("coverLabel")
        self.cover_label.setFixedSize(self.COVER_SIZE)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_label.setVisible(False)
        layout.addWidget(self.cover_label, 0, Qt.AlignmentFlag.AlignTop)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        self.title_label = QLabel()
        self.title_label.setObjectName("videoTitleLabel")
        self.title_label.setWordWrap(True)
        self.title_label.setMinimumWidth(150)

        self.info_label = QLabel()
        self.info_label.setObjectName("videoInfoLabel")
        self.info_label.setWordWrap(True)

        self.path_label = QLabel()
        self.path_label.setObjectName("mutedLabel")
        self.path_label.setWordWrap(True)
        self.path_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.info_label)
        text_layout.addWidget(self.path_label)
        text_layout.addStretch()

        layout.addLayout(text_layout, 1)

    def update_content(self, video: CachedVideo) -> None:
        """更新显示内容。"""
        self.title_label.setText(video.display_title)
        info_parts = [video.size_display]
        if video.tech_info:
            info_parts.append(video.tech_info)
        if video.bvid:
            info_parts.append(video.bvid)
        self.info_label.setText(" | ".join(info_parts))
        self.path_label.setText(str(video.folder_path))
        self._update_cover(video.cover_path)

    def _update_cover(self, cover_path: Path | None) -> None:
        """更新封面图片。"""
        if cover_path and cover_path.exists():
            pixmap = QPixmap(str(cover_path))
            if not pixmap.isNull():
                self._cover_pixmap = pixmap
                self.cover_label.setVisible(True)
                self._render_cover_pixmap()
                return
        self._cover_pixmap = None
        self.cover_label.clear()
        self.cover_label.setVisible(False)

    def _render_cover_pixmap(self) -> None:
        """渲染封面图片（支持高DPI）。"""
        if not self._cover_pixmap:
            return

        target_size = self.cover_label.size()
        if target_size.width() <= 0 or target_size.height() <= 0:
            return

        device_ratio = max(self.devicePixelRatioF(), 1.0)
        scaled = self._cover_pixmap.scaled(
            target_size * device_ratio,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        scaled.setDevicePixelRatio(device_ratio)
        self.cover_label.setPixmap(scaled)

    def resizeEvent(self, event) -> None:
        """处理大小变化事件。"""
        super().resizeEvent(event)
        self._render_cover_pixmap()

    def apply_selection(self, selected: bool) -> None:
        """应用选中状态样式。"""
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)


# ============================================================
# 扫描工作线程
# ============================================================
class ScanWorker(QObject):
    """扫描缓存视频的工作线程。"""
    
    progress = pyqtSignal(int, int)
    found = pyqtSignal(object)
    finished = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(
        self,
        device_id: str,
        device_type: str,
        source_key: str,
        cover_cache_dir: Path | None = None,
    ) -> None:
        """初始化扫描器。"""
        super().__init__()
        self.device_id = device_id
        self.device_type = device_type
        self.source_key = source_key
        self._cancelled = False
        self._paused = False
        self.temp_dir: Path | None = None
        self.cover_cache_dir = cover_cache_dir
        if self.cover_cache_dir:
            self.cover_cache_dir.mkdir(parents=True, exist_ok=True)

    def cancel(self) -> None:
        """取消扫描。"""
        self._cancelled = True

    def pause(self) -> None:
        """暂停扫描。"""
        self._paused = True

    def resume(self) -> None:
        """恢复扫描。"""
        self._paused = False

    def is_paused(self) -> bool:
        """返回是否暂停。"""
        return self._paused

    def run(self) -> None:
        """执行扫描任务。"""
        count = 0
        try:
            self.temp_dir = Path(tempfile.mkdtemp())
            if self.device_type == "adb":
                count = self._scan_adb()
            else:
                count = self._scan_drive()
        except Exception as exc:
            logger.exception("扫描过程中出错")
            self.error.emit(f"扫描错误: {str(exc)[:50]}")
        finally:
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            self.finished.emit(count)

    def _wait_if_paused(self) -> None:
        """如果暂停则等待。"""
        while self._paused and not self._cancelled:
            QThread.msleep(100)

    def _scan_adb(self) -> int:
        """通过ADB扫描设备。"""
        count = 0
        adb = DeviceScanner.find_adb()
        source = BILI_SOURCES.get(self.source_key)
        if not adb or not source:
            return 0

        remote_base = f"/sdcard/Android/data/{source['package']}/download"
        try:
            result = run_command(
                [adb, "-s", self.device_id, "shell", f"ls -1 {remote_base}"],
                timeout=30,
            )
            if result.returncode != 0:
                return 0

            folders = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            total = len(folders)
            for index, folder_name in enumerate(folders):
                self._wait_if_paused()
                if self._cancelled:
                    break

                self.progress.emit(index + 1, total)
                folder_path = f"{remote_base}/{folder_name}"
                for video in self._find_m4s_adb(adb, folder_path, folder_name):
                    self.found.emit(video)
                    count += 1
        except Exception as exc:
            logger.exception("ADB 扫描失败")
            self.error.emit(f"ADB扫描错误: {str(exc)[:40]}")
        return count

    def _find_m4s_adb(
        self, adb: str, remote_path: str, root_folder: str
    ) -> list[CachedVideo]:
        """通过ADB查找m4s文件。"""
        videos: list[CachedVideo] = []
        if self._cancelled:
            return videos
        try:
            result = run_command(
                [adb, "-s", self.device_id, "shell", f"ls -1 {remote_path}"],
                timeout=10,
            )
            if result.returncode != 0:
                return videos

            files = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            if {"video.m4s", "audio.m4s"}.issubset(files):
                video = self._parse_video_adb(adb, remote_path, files, root_folder)
                if video:
                    videos.append(video)
            else:
                for item in files:
                    if item in {".", ".."}:
                        continue
                    sub_path = f"{remote_path}/{item}"
                    videos.extend(self._find_m4s_adb(adb, sub_path, root_folder))
        except subprocess.SubprocessError as exc:
            logger.debug("遍历 ADB 目录失败 %s: %s", remote_path, exc)
        return videos

    def _parse_video_adb(
        self, adb: str, remote_path: str, files: list[str], root_folder: str
    ) -> CachedVideo | None:
        """解析ADB设备上的视频信息。"""
        title = root_folder
        part_title = ""
        bvid = ""
        quality = ""
        resolution = ""
        frame_rate = ""
        cover_path = None

        if "index.json" in files:
            local_index = self._pull_temp_file(adb, f"{remote_path}/index.json")
            if local_index:
                data = safe_json_load(local_index)
                resolution, frame_rate = self._parse_index_json(data)
                remove_file(local_index)

        current_path = remote_path
        for _ in range(5):
            entry_remote = f"{current_path}/entry.json"
            local_entry = self._pull_temp_file(adb, entry_remote)
            if local_entry:
                data = safe_json_load(local_entry)
                title = data.get("title", title)
                bvid = data.get("bvid", "")
                page_data = data.get("page_data", {})
                part_title = page_data.get("part", "")
                quality = self._get_quality_name(data.get("quality", 0))
                remove_file(local_entry)
                cover_path = self._pull_cover_adb(adb, current_path, bvid or root_folder)
                break
            parts = current_path.rsplit("/", 1)
            if len(parts) < 2:
                break
            current_path = parts[0]

        size_mb = self._calc_remote_size(adb, remote_path)

        return CachedVideo(
            folder_path=Path(remote_path),
            video_path=Path(f"{remote_path}/video.m4s"),
            audio_path=Path(f"{remote_path}/audio.m4s"),
            title=title,
            part_title=part_title,
            size_mb=size_mb,
            bvid=bvid,
            quality=quality,
            resolution=resolution,
            frame_rate=frame_rate,
            cover_path=cover_path,
        )

    def _pull_temp_file(self, adb: str, remote_path: str) -> Path | None:
        """从设备拉取临时文件。"""
        if not self.temp_dir:
            return None
        local_path = self.temp_dir / Path(remote_path).name
        result = run_command(
            [adb, "-s", self.device_id, "pull", remote_path, str(local_path)],
            timeout=10,
        )
        if result.returncode == 0 and local_path.exists():
            return local_path
        remove_file(local_path)
        return None

    def _calc_remote_size(self, adb: str, remote_path: str) -> float:
        """计算远程文件大小。"""
        try:
            result = run_command(
                [
                    adb,
                    "-s",
                    self.device_id,
                    "shell",
                    f"stat -c %s {remote_path}/video.m4s {remote_path}/audio.m4s",
                ],
                timeout=10,
            )
            if result.returncode == 0:
                sizes = [
                    int(line.strip())
                    for line in result.stdout.splitlines()
                    if line.strip().isdigit()
                ]
                return format_bytes_to_mb(sum(sizes))
        except subprocess.SubprocessError as exc:
            logger.debug("读取远程文件大小失败: %s", exc)
        return 0.0

    def _pull_cover_adb(
        self, adb: str, remote_path: str, identifier: str
    ) -> Path | None:
        """从ADB设备拉取封面图片。"""
        if not self.cover_cache_dir:
            return None
        cover_remote = f"{remote_path}/cover.jpg"
        safe_id = hashlib.md5(f"{remote_path}_{identifier}".encode("utf-8")).hexdigest()
        cover_local = self.cover_cache_dir / f"{safe_id}.jpg"
        try:
            result = run_command(
                [adb, "-s", self.device_id, "pull", cover_remote, str(cover_local)],
                timeout=15,
            )
            if result.returncode == 0 and cover_local.exists():
                return cover_local
        except subprocess.SubprocessError as exc:
            logger.debug("拉取封面失败: %s", exc)
        remove_file(cover_local)
        return None

    def _scan_drive(self) -> int:
        """扫描本地驱动器。"""
        count = 0
        source = BILI_SOURCES.get(self.source_key)
        if not source:
            return 0

        download_path = Path(self.device_id) / "Android" / "data" / source["package"] / "download"
        if not download_path.exists():
            return 0

        folders = [folder for folder in download_path.iterdir() if folder.is_dir()]
        total = len(folders)
        for index, folder in enumerate(folders):
            self._wait_if_paused()
            if self._cancelled:
                break

            self.progress.emit(index + 1, total)
            for video in self._find_m4s_local(folder, folder.name):
                self.found.emit(video)
                count += 1
        return count

    def _find_m4s_local(self, folder: Path, root_folder: str) -> list[CachedVideo]:
        """在本地目录查找m4s文件。"""
        videos: list[CachedVideo] = []
        if self._cancelled:
            return videos

        video_m4s = folder / "video.m4s"
        audio_m4s = folder / "audio.m4s"

        if video_m4s.exists() and audio_m4s.exists():
            video = self._parse_video_local(folder, root_folder)
            if video:
                videos.append(video)
        else:
            with contextlib.suppress(PermissionError):
                for sub in folder.iterdir():
                    if sub.is_dir():
                        videos.extend(self._find_m4s_local(sub, root_folder))
        return videos

    def _parse_video_local(self, folder: Path, root_folder: str) -> CachedVideo | None:
        """解析本地视频信息。"""
        title = root_folder
        part_title = ""
        bvid = ""
        quality = ""
        resolution = ""
        frame_rate = ""
        cover_path: Path | None = None

        index_json = folder / "index.json"
        if index_json.exists():
            data = safe_json_load(index_json)
            resolution, frame_rate = self._parse_index_json(data)

        current = folder
        for _ in range(5):
            entry = current / "entry.json"
            if entry.exists():
                data = safe_json_load(entry)
                title = data.get("title", title)
                bvid = data.get("bvid", "")
                page_data = data.get("page_data", {})
                part_title = page_data.get("part", "")
                quality = self._get_quality_name(data.get("quality", 0))
                cover_file = current / "cover.jpg"
                if cover_file.exists():
                    cover_path = cover_file
                break
            parent = current.parent
            if parent == current:
                break
            current = parent

        video_m4s = folder / "video.m4s"
        audio_m4s = folder / "audio.m4s"
        size_mb = format_bytes_to_mb(
            video_m4s.stat().st_size + audio_m4s.stat().st_size
        )

        return CachedVideo(
            folder_path=folder,
            video_path=video_m4s,
            audio_path=audio_m4s,
            title=title,
            part_title=part_title,
            size_mb=size_mb,
            bvid=bvid,
            quality=quality,
            resolution=resolution,
            frame_rate=frame_rate,
            cover_path=cover_path,
        )

    def _parse_index_json(self, data: dict[str, Any]) -> tuple[str, str]:
        """解析index.json获取分辨率和帧率。"""
        resolution = ""
        frame_rate = ""
        try:
            video_list = data.get("video", [])
            if video_list:
                video_info = video_list[0]
                width = video_info.get("width", 0)
                height = video_info.get("height", 0)
                if width and height:
                    resolution = f"{width}×{height}"
                fps = video_info.get("frame_rate")
                if fps:
                    try:
                        fps_float = float(fps)
                        frame_rate = (
                            f"{fps_float:.0f}"
                            if fps_float == int(fps_float)
                            else f"{fps_float:.1f}"
                        )
                    except (ValueError, TypeError):
                        pass
        except (IndexError, TypeError) as exc:
            logger.debug("解析 index.json 失败: %s", exc)
        return resolution, frame_rate

    @staticmethod
    def _get_quality_name(quality_id: int) -> str:
        """根据质量ID获取质量名称。"""
        quality_map = {
            127: "8K",
            126: "杜比视界",
            125: "HDR",
            120: "4K",
            116: "1080P60",
            112: "1080P+",
            80: "1080P",
            74: "720P60",
            64: "720P",
            32: "480P",
            16: "360P",
        }
        if quality_id in quality_map:
            return quality_map[quality_id]
        return f"{quality_id}P" if quality_id else ""


# ============================================================
# 设备扫描器
# ============================================================
class DeviceScanner:
    """设备扫描和操作工具类。"""
    
    _adb_path: str | None = None

    @classmethod
    def find_adb(cls) -> str | None:
        """查找ADB可执行文件路径。"""
        if cls._adb_path:
            return cls._adb_path

        adb_name = "adb.exe" if sys.platform == "win32" else "adb"
        try:
            result = run_command([adb_name, "version"], timeout=5)
            if result.returncode == 0:
                cls._adb_path = adb_name
                return cls._adb_path
        except OSError:
            pass

        possible_paths = [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Android" / "Sdk" / "platform-tools" / "adb.exe",
            Path(os.environ.get("USERPROFILE", "")) / "AppData" / "Local" / "Android" / "Sdk" / "platform-tools" / "adb.exe",
            Path("C:/Android/sdk/platform-tools/adb.exe"),
            Path("C:/Program Files/Android/platform-tools/adb.exe"),
            Path("C:/Program Files (x86)/Android/platform-tools/adb.exe"),
        ]

        for path in possible_paths:
            if path.exists():
                cls._adb_path = str(path)
                return cls._adb_path
        return None

    @classmethod
    def get_adb_devices(cls) -> list[tuple[str, str]]:
        """获取通过ADB连接的设备列表。"""
        devices: list[tuple[str, str]] = []
        adb = cls.find_adb()
        if not adb:
            return devices

        try:
            result = run_command([adb, "devices", "-l"], timeout=10)
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")[1:]
                for line in lines:
                    if not line.strip():
                        continue
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] == "device":
                        serial = parts[0]
                        model = "Android设备"
                        for part in parts[2:]:
                            if part.startswith("model:"):
                                model = part.split(":")[1].replace("_", " ")
                                break
                        devices.append((serial, f"{model} ({serial})"))
        except subprocess.SubprocessError as exc:
            logger.debug("获取 ADB 设备失败: %s", exc)
        return devices

    @classmethod
    def get_drive_devices(cls) -> list[tuple[str, str]]:
        """获取包含哔哩哔哩缓存的驱动器列表。"""
        devices: list[tuple[str, str]] = []
        for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
            drive_path = Path(f"{letter}:/")
            if not drive_path.exists():
                continue

            android_data = drive_path / "Android" / "data"
            if not android_data.exists():
                continue

            for source in BILI_SOURCES.values():
                bili_path = android_data / source["package"] / "download"
                if bili_path.exists():
                    devices.append((f"{letter}:", f"存储设备 ({letter}:)"))
                    break
        return devices

    @classmethod
    def get_connected_devices(cls) -> list[tuple[str, str, str]]:
        """获取所有已连接设备（包括ADB和本地驱动器）。"""
        devices: list[tuple[str, str, str]] = []
        devices.extend((dev_id, dev_name, "adb") for dev_id, dev_name in cls.get_adb_devices())
        devices.extend((dev_id, dev_name, "drive") for dev_id, dev_name in cls.get_drive_devices())
        return devices

    @classmethod
    def pull_and_convert(
        cls, video: CachedVideo, output_path: Path, device_id: str, device_type: str
    ) -> bool:
        """拉取视频文件并转换为MP4。"""
        if device_type == "drive":
            return biliffm4s.combine(str(video.folder_path), str(output_path))
        if device_type == "adb":
            adb = cls.find_adb()
            if not adb:
                return False

            temp_dir = Path(tempfile.mkdtemp())
            try:
                local_video = temp_dir / "video.m4s"
                local_audio = temp_dir / "audio.m4s"

                result = run_command(
                    [adb, "-s", device_id, "pull", str(video.video_path), str(local_video)],
                    timeout=300,
                )
                if result.returncode != 0:
                    return False

                result = run_command(
                    [adb, "-s", device_id, "pull", str(video.audio_path), str(local_audio)],
                    timeout=300,
                )
                if result.returncode != 0:
                    return False

                return biliffm4s.combine(str(temp_dir), str(output_path))
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
        return False


# ============================================================
# 转换工作线程
# ============================================================
class ConvertWorker(QObject):
    """视频转换工作线程。"""
    
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(int, int)
    error = pyqtSignal(str)

    def __init__(
        self,
        videos: list[CachedVideo],
        output_dir: Path,
        device_id: str,
        device_type: str,
    ) -> None:
        """初始化转换器。"""
        super().__init__()
        self.videos = videos
        self.output_dir = output_dir
        self.device_id = device_id
        self.device_type = device_type
        self._cancelled = False

    def cancel(self) -> None:
        """取消转换。"""
        self._cancelled = True

    def run(self) -> None:
        """执行转换任务。"""
        success_count = 0
        total = len(self.videos)

        for index, video in enumerate(self.videos):
            if self._cancelled:
                break

            title_short = (
                f"{video.display_title[:25]}..."
                if len(video.display_title) > 25
                else video.display_title
            )
            self.progress.emit(index + 1, total, f"转换: {title_short}")

            safe_title = self._sanitize_filename(video.display_title)
            output_path = self.output_dir / f"{safe_title}.mp4"

            counter = 1
            while output_path.exists():
                output_path = self.output_dir / f"{safe_title}_{counter}.mp4"
                counter += 1

            try:
                result = DeviceScanner.pull_and_convert(
                    video, output_path, self.device_id, self.device_type
                )
                if result:
                    success_count += 1
                else:
                    self.error.emit(f"转换失败: {title_short}")
            except Exception as exc:
                logger.exception("转换失败")
                self.error.emit(f"错误: {str(exc)[:50]}")

        self.finished.emit(success_count, total)

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """清理文件名中的非法字符。"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, "_")
        filename = "".join(char for char in filename if ord(char) >= 32)
        return filename[:180].strip()


# ============================================================
# 关于对话框
# ============================================================
class AboutDialog(QDialog):
    """关于对话框。"""
    
    def __init__(self, parent: QWidget | None = None, icon_path: Path | None = None) -> None:
        """初始化关于对话框。"""
        super().__init__(parent)
        self.setWindowTitle("关于")
        self.setFixedSize(320, 360)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)

        header = QHBoxLayout()
        header.setSpacing(12)

        if icon_path and icon_path.exists():
            logo = QLabel()
            logo.setFixedSize(56, 56)
            pixmap = QPixmap(str(icon_path))
            if not pixmap.isNull():
                device_ratio = self.devicePixelRatioF()
                target_size = QSize(56, 56) * device_ratio
                scaled = pixmap.scaled(
                    target_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                scaled.setDevicePixelRatio(device_ratio)
                logo.setPixmap(scaled)
            header.addWidget(logo)

        title_box = QVBoxLayout()
        title_box.setSpacing(3)

        title = QLabel("Android哔哩哔哩视频导出器")
        title.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        title_box.addWidget(title)

        version = QLabel(f"版本 {VERSION}")
        version.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 10px;")
        title_box.addWidget(version)

        header.addLayout(title_box)
        header.addStretch()
        layout.addLayout(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {COLORS['border']};")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        info = QTextBrowser()
        info.setOpenExternalLinks(True)
        info.setHtml(
            f"""
        <style>
            body {{ font-family: "Microsoft YaHei", sans-serif; font-size: 11px; line-height: 1.6; }}
            .row {{ margin: 4px 0; }}
            .label {{ color: {COLORS["text_secondary"]}; }}
            a {{ color: {COLORS["primary"]}; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
        </style>    
        <div class="row"><span class="label">作者:</span> WaterRun</div>
        <div class="row"><span class="label">协作:</span> Claude Opus 4.5, Nano Banana Pro</div>
        <div class="row"><span class="label">概述:</span> 扫描接入的安卓设备的哔哩哔哩缓存目录并导出. 通过对<a href="https://github.com/Water-Run/-m4s-Python-biliffm4s/tree/master">biliffm4s</a>封装实现开箱即用</div>
        <div class="row"><span class="label">可运行:</span> Windows 64位</div>    
        <div class="row"><span class="label">许可证:</span> GNU GPL v3.0</div>
        <div class="row"><span class="label">技术栈:</span> PyQT, Pyinstaller, Python, biliffm4s, FFMpeg</div>
        <div class="row"><span class="label">链接:</span> <a href="https://github.com/Water-Run/biliandout">GitHub</a></div>
        """
        )
        layout.addWidget(info, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.setFixedSize(60, 26)
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)


# ============================================================
# 页面栈管理
# ============================================================
class WidgetStack:
    """简单的Widget栈管理器。"""
    
    def __init__(self) -> None:
        """初始化栈管理器。"""
        self.container = QWidget()
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.pages: dict[str, QWidget] = {}
        self.current_key: str | None = None

    def add_page(self, key: str, widget: QWidget) -> None:
        """添加页面。"""
        self.pages[key] = widget
        widget.setVisible(False)
        self.layout.addWidget(widget)
        if self.current_key is None:
            self.show_page(key)

    def show_page(self, key: str) -> None:
        """显示指定页面。"""
        if key == self.current_key:
            return
        if self.current_key and self.current_key in self.pages:
            self.pages[self.current_key].setVisible(False)
        if key in self.pages:
            self.pages[key].setVisible(True)
            self.current_key = key


# ============================================================
# 主窗口
# ============================================================
class MainWindow(QMainWindow):
    """应用程序主窗口。"""
    
    def __init__(self) -> None:
        """初始化主窗口。"""
        super().__init__()
        self.videos: list[CachedVideo] = []
        self.convert_thread: QThread | None = None
        self.convert_worker: ConvertWorker | None = None
        self.scan_thread: QThread | None = None
        self.scan_worker: ScanWorker | None = None
        self.scan_state = ScanState.IDLE

        self.auto_refresh_timer = QTimer(self)
        self.auto_refresh_timer.timeout.connect(self._auto_refresh_devices)

        base_path = (
            Path(sys.executable).parent
            if getattr(sys, "frozen", False)
            else Path(__file__).resolve().parent.parent
        )
        self.output_dir = base_path / "合并后的视频"

        icon_base = (
            Path(sys._MEIPASS)  # type: ignore[attr-defined]
            if getattr(sys, "frozen", False)
            else Path(__file__).resolve().parent
        )
        self.icon_path = icon_base / "logo.png"

        self._setup_ui()
        self._connect_signals()
        self._refresh_devices()
        self._start_auto_refresh_if_needed()

    @property
    def selected_device(self) -> tuple[str, str] | None:
        """返回当前选中的设备信息。"""
        data = self.device_combo.currentData()
        return data if data else None

    def _setup_ui(self) -> None:
        """设置用户界面。"""
        self.setWindowTitle("Android哔哩哔哩视频导出器")
        self.setMinimumSize(420, 480)
        self.resize(460, 520)

        if self.icon_path.exists():
            pixmap = QPixmap(str(self.icon_path))
            if not pixmap.isNull():
                self.setWindowIcon(QIcon(pixmap))

        self.setStyleSheet(STYLESHEET)

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # ========== 设备组 ==========
        device_group = QGroupBox("设备")
        device_layout = QVBoxLayout(device_group)
        device_layout.setSpacing(6)
        device_layout.setContentsMargins(8, 12, 8, 8)

        dev_row = QHBoxLayout()
        dev_row.setSpacing(6)

        dev_label = QLabel("设备:")
        dev_label.setFixedWidth(40)
        dev_row.addWidget(dev_label)

        self.device_combo = QComboBox()
        self.device_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        dev_row.addWidget(self.device_combo)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setFixedWidth(50)
        dev_row.addWidget(self.refresh_btn)
        device_layout.addLayout(dev_row)

        src_row = QHBoxLayout()
        src_row.setSpacing(6)

        src_label = QLabel("来源:")
        src_label.setFixedWidth(40)
        src_row.addWidget(src_label)

        self.source_combo = QComboBox()
        for key, info in BILI_SOURCES.items():
            self.source_combo.addItem(info["name"], key)
        self.source_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        src_row.addWidget(self.source_combo)

        self.scan_btn = QPushButton("加载")
        self.scan_btn.setObjectName("successBtn")
        self.scan_btn.setFixedWidth(50)
        src_row.addWidget(self.scan_btn)

        self.scan_pause_btn = QPushButton("暂停")
        self.scan_pause_btn.setObjectName("pauseBtn")
        self.scan_pause_btn.setFixedWidth(50)
        self.scan_pause_btn.setVisible(False)
        src_row.addWidget(self.scan_pause_btn)

        self.scan_cancel_btn = QPushButton("取消")
        self.scan_cancel_btn.setFixedWidth(50)
        self.scan_cancel_btn.setVisible(False)
        src_row.addWidget(self.scan_cancel_btn)

        device_layout.addLayout(src_row)
        main_layout.addWidget(device_group)

        # ========== 视频组 ==========
        video_group = QGroupBox("缓存视频")
        video_group_layout = QVBoxLayout(video_group)
        video_group_layout.setSpacing(6)
        video_group_layout.setContentsMargins(8, 8, 8, 8)

        self.video_stack = WidgetStack()
        video_group_layout.addWidget(self.video_stack.container, 1)

        # 空状态页
        self.empty_state_widget = QWidget()
        self.empty_state_widget.setObjectName("emptyState")
        empty_layout = QVBoxLayout(self.empty_state_widget)
        empty_layout.setContentsMargins(14, 24, 14, 24)
        self.empty_hint = QLabel()
        self.empty_hint.setObjectName("emptyHint")
        self.empty_hint.setWordWrap(True)
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_hint)
        self.video_stack.add_page("empty", self.empty_state_widget)

        # 加载页
        self.loading_widget = QWidget()
        loading_layout = QVBoxLayout(self.loading_widget)
        loading_layout.setContentsMargins(24, 36, 24, 36)
        loading_layout.setSpacing(8)

        loading_layout.addStretch(1)

        progress_container = QHBoxLayout()
        progress_container.addStretch(1)
        self.loading_progress = QProgressBar()
        self.loading_progress.setObjectName("scanProgress")
        self.loading_progress.setRange(0, 0)
        self.loading_progress.setTextVisible(False)
        self.loading_progress.setFixedSize(200, 18)
        progress_container.addWidget(self.loading_progress)
        progress_container.addStretch(1)
        loading_layout.addLayout(progress_container)

        self.loading_status_label = QLabel("正在扫描...")
        self.loading_status_label.setObjectName("loadingStatusLabel")
        self.loading_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_layout.addWidget(self.loading_status_label)

        loading_layout.addStretch(1)
        self.video_stack.add_page("loading", self.loading_widget)

        # 视频列表页
        self.video_list = QListWidget()
        self.video_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.video_list.setSpacing(4)
        self.video_stack.add_page("list", self.video_list)

        main_layout.addWidget(video_group, 1)

        # ========== 操作区 ==========
        action_widget = QWidget()
        action_layout = QVBoxLayout(action_widget)
        action_layout.setSpacing(6)
        action_layout.setContentsMargins(0, 0, 0, 0)

        list_actions = QHBoxLayout()
        list_actions.setSpacing(6)

        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.setFixedWidth(50)
        list_actions.addWidget(self.select_all_btn)

        self.deselect_btn = QPushButton("清除")
        self.deselect_btn.setFixedWidth(50)
        list_actions.addWidget(self.deselect_btn)

        list_actions.addStretch()

        self.count_label = QLabel("0 个视频")
        self.count_label.setObjectName("mutedLabel")
        list_actions.addWidget(self.count_label)

        action_layout.addLayout(list_actions)

        output_row = QHBoxLayout()
        output_row.setSpacing(6)

        out_label = QLabel("输出:")
        out_label.setFixedWidth(40)
        output_row.addWidget(out_label)

        self.output_label = QLabel()
        self.output_label.setObjectName("pathLabel")
        self.output_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.output_label.setMinimumWidth(80)
        self._update_output_label()
        output_row.addWidget(self.output_label, 1)

        self.browse_btn = QPushButton("浏览")
        self.browse_btn.setFixedWidth(50)
        output_row.addWidget(self.browse_btn)

        action_layout.addLayout(output_row)
        main_layout.addWidget(action_widget)

        self.export_progress_bar = QProgressBar()
        self.export_progress_bar.setVisible(False)
        self.export_progress_bar.setFixedHeight(18)
        main_layout.addWidget(self.export_progress_bar)

        # ========== 底部按钮 ==========
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.about_btn = QPushButton("关于")
        self.about_btn.setFixedWidth(50)
        btn_row.addWidget(self.about_btn)

        btn_row.addStretch()

        self.export_cancel_btn = QPushButton("取消")
        self.export_cancel_btn.setFixedWidth(50)
        self.export_cancel_btn.setVisible(False)
        btn_row.addWidget(self.export_cancel_btn)

        self.export_btn = QPushButton("导出选中")
        self.export_btn.setObjectName("primaryBtn")
        self.export_btn.setFixedWidth(80)
        btn_row.addWidget(self.export_btn)

        main_layout.addLayout(btn_row)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪，点击「加载」读取缓存")

        self._refresh_video_view()

    def _update_output_label(self) -> None:
        """更新输出目录标签显示。"""
        display = str(self.output_dir)
        metrics = self.output_label.fontMetrics()
        available_width = max(120, self.output_label.width() - 8)
        elided = metrics.elidedText(display, Qt.TextElideMode.ElideLeft, available_width)
        self.output_label.setText(elided)
        self.output_label.setToolTip(str(self.output_dir))

    def resizeEvent(self, event) -> None:
        """处理窗口大小变化。"""
        super().resizeEvent(event)
        self._update_output_label()

    def _connect_signals(self) -> None:
        """连接信号与槽。"""
        self.refresh_btn.clicked.connect(self._refresh_devices)
        self.scan_btn.clicked.connect(self._scan_videos)
        self.browse_btn.clicked.connect(self._browse_output)
        self.export_btn.clicked.connect(self._start_export)
        self.export_cancel_btn.clicked.connect(self._cancel_export)
        self.select_all_btn.clicked.connect(self._select_all)
        self.deselect_btn.clicked.connect(self._deselect_all)
        self.about_btn.clicked.connect(self._show_about)
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)
        self.scan_pause_btn.clicked.connect(self._toggle_scan_pause)
        self.scan_cancel_btn.clicked.connect(self._cancel_scan)
        self.video_list.itemSelectionChanged.connect(self._sync_item_selection_styles)

    def _start_auto_refresh_if_needed(self) -> None:
        """未连接设备时启动自动刷新。"""
        if not self.selected_device:
            self.auto_refresh_timer.start(1000)
        else:
            self.auto_refresh_timer.stop()

    def _auto_refresh_devices(self) -> None:
        """自动刷新设备（静默方式）。"""
        if self.scan_state != ScanState.IDLE:
            return
        if self.convert_thread and self.convert_thread.isRunning():
            return

        devices = DeviceScanner.get_connected_devices()
        current_data = self.device_combo.currentData()

        if devices and not current_data:
            self._refresh_devices()
        elif not devices and current_data:
            self._refresh_devices()

    def _refresh_devices(self) -> None:
        """刷新设备列表。"""
        self.device_combo.clear()
        self.videos.clear()
        self.video_list.clear()
        self._update_counts()
        devices = DeviceScanner.get_connected_devices()

        if not devices:
            self.device_combo.addItem("未检测到设备", None)
            self.status_bar.showMessage("未检测到设备，正在自动检测...")
            self._start_auto_refresh_if_needed()
        else:
            for dev_id, dev_name, dev_type in devices:
                self.device_combo.addItem(dev_name, (dev_id, dev_type))
            self.status_bar.showMessage(f"检测到 {len(devices)} 个设备")
            self.auto_refresh_timer.stop()
        self._refresh_video_view()
        self._update_action_states()

    def _on_device_changed(self, _: int) -> None:
        """处理设备切换。"""
        self.videos.clear()
        self.video_list.clear()
        self._update_counts()
        self._refresh_video_view()
        self._update_action_states()
        self._start_auto_refresh_if_needed()
        if not self.selected_device:
            self.status_bar.showMessage("未连接设备，正在自动检测...")
        else:
            self.status_bar.showMessage("设备就绪")

    def _scan_videos(self) -> None:
        """开始扫描视频。"""
        if self.scan_state != ScanState.IDLE:
            return

        selected_device = self.selected_device
        if not selected_device:
            QMessageBox.warning(self, "提示", "未选择设备")
            return

        device_id, device_type = selected_device
        source_key = self.source_combo.currentData()

        self.videos.clear()
        self.video_list.clear()
        self._update_counts()
        self._clear_cover_cache()

        self.scan_thread = QThread()
        self.scan_worker = ScanWorker(device_id, device_type, source_key, COVER_CACHE_DIR)
        self.scan_worker.moveToThread(self.scan_thread)

        self.scan_thread.started.connect(self.scan_worker.run)
        self.scan_worker.progress.connect(self._on_scan_progress)
        self.scan_worker.found.connect(self._on_video_found)
        self.scan_worker.finished.connect(self._on_scan_finished)
        self.scan_worker.error.connect(self._on_scan_error)

        self.loading_progress.setRange(0, 0)
        self.loading_progress.setValue(0)
        self.loading_status_label.setText("正在扫描...")
        self.scan_thread.start()
        self._set_scan_state(ScanState.LOADING)
        self.status_bar.showMessage("正在加载缓存视频...")

    def _toggle_scan_pause(self) -> None:
        """切换扫描暂停状态。"""
        if not self.scan_worker:
            return
        if self.scan_worker.is_paused():
            self.scan_worker.resume()
            self.scan_pause_btn.setText("暂停")
            self._set_scan_state(ScanState.LOADING)
            self.status_bar.showMessage("继续加载...")
        else:
            self.scan_worker.pause()
            self.scan_pause_btn.setText("继续")
            self._set_scan_state(ScanState.PAUSED)
            self.status_bar.showMessage("已暂停")

    def _cancel_scan(self) -> None:
        """取消扫描。"""
        if self.scan_worker:
            self.scan_worker.cancel()
            self.status_bar.showMessage("正在取消...")

    def _on_scan_progress(self, current: int, total: int) -> None:
        """处理扫描进度。"""
        if total <= 0:
            self.loading_progress.setRange(0, 0)
            self.loading_status_label.setText("正在扫描...")
        else:
            self.loading_progress.setRange(0, total)
            self.loading_progress.setValue(current)
            self.loading_status_label.setText(f"扫描 {current}/{total}")
        self.status_bar.showMessage(f"扫描 ({current}/{total})")

    def _on_video_found(self, video: CachedVideo) -> None:
        """处理发现的视频。"""
        self.videos.append(video)
        self._add_video_item(video)
        self._update_counts()

    def _on_scan_finished(self, count: int) -> None:
        """处理扫描完成。"""
        self._cleanup_scan_thread()
        self._set_scan_state(ScanState.IDLE)
        self.loading_progress.setRange(0, 100)
        self.loading_progress.setValue(0)

        if count > 0:
            self.status_bar.showMessage(f"找到 {count} 个视频")
        else:
            self.status_bar.showMessage("未找到缓存视频")
            self._set_empty_hint("no_video")
        self._refresh_video_view()

    def _on_scan_error(self, msg: str) -> None:
        """处理扫描错误。"""
        self.status_bar.showMessage(msg)

    def _cleanup_scan_thread(self) -> None:
        """清理扫描线程。"""
        if self.scan_thread:
            self.scan_thread.quit()
            self.scan_thread.wait()
            self.scan_thread = None
            self.scan_worker = None

    def _add_video_item(self, video: CachedVideo) -> None:
        """添加视频到列表。"""
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, video)

        widget = VideoListItemWidget(video)
        item.setSizeHint(widget.sizeHint())

        self.video_list.addItem(item)
        self.video_list.setItemWidget(item, widget)
        self._sync_item_selection_styles()

    def _sync_item_selection_styles(self) -> None:
        """同步列表项选中样式。"""
        for index in range(self.video_list.count()):
            item = self.video_list.item(index)
            widget = self.video_list.itemWidget(item)
            if isinstance(widget, VideoListItemWidget):
                widget.apply_selection(item.isSelected())

    def _clear_cover_cache(self) -> None:
        """清除封面缓存。"""
        if not COVER_CACHE_DIR.exists():
            return
        for file in COVER_CACHE_DIR.glob("*.jpg"):
            remove_file(file)

    def _update_counts(self) -> None:
        """更新视频计数。"""
        self.count_label.setText(f"{len(self.videos)} 个视频")

    def _refresh_video_view(self) -> None:
        """刷新视频视图。"""
        if self.scan_state == ScanState.LOADING:
            self.video_stack.show_page("loading")
        elif self.scan_state == ScanState.PAUSED:
            if self.videos:
                self.video_stack.show_page("list")
            else:
                self.video_stack.show_page("loading")
        else:
            if self.videos:
                self.video_stack.show_page("list")
            else:
                self._update_empty_hint()
                self.video_stack.show_page("empty")
        self._update_action_states()

    def _update_empty_hint(self, mode: str = "") -> None:
        """更新空状态提示。"""
        if not self.videos and self.scan_state == ScanState.IDLE:
            if not self.selected_device:
                text = (
                    "<b>如何连接设备</b><br><br>"
                    "1. 启用USB调试<br>"
                    "2. 连接设备并开启文件传输<br><br>"
                    "程序正在自动检测..."
                )
            else:
                text = "<b>设备已就绪</b><br><br>点击「加载」读取缓存"
            self.empty_hint.setText(text)
        elif not self.videos and mode == "no_video":
            self.empty_hint.setText("暂无缓存，请先在App中缓存视频")

    def _set_empty_hint(self, mode: str) -> None:
        """设置空状态提示。"""
        self._update_empty_hint(mode)

    def _set_scan_state(self, state: ScanState) -> None:
        """设置扫描状态。"""
        self.scan_state = state
        if state == ScanState.LOADING:
            self.scan_btn.setEnabled(False)
            self.scan_pause_btn.setVisible(True)
            self.scan_cancel_btn.setVisible(True)
            self.scan_pause_btn.setText("暂停")
        elif state == ScanState.PAUSED:
            self.scan_btn.setEnabled(False)
            self.scan_pause_btn.setVisible(True)
            self.scan_cancel_btn.setVisible(True)
        else:
            self.scan_btn.setEnabled(self.selected_device is not None)
            self.scan_pause_btn.setVisible(False)
            self.scan_cancel_btn.setVisible(False)
        self._refresh_video_view()

    def _get_selected(self) -> list[CachedVideo]:
        """获取选中的视频列表。"""
        selected: list[CachedVideo] = []
        for index in range(self.video_list.count()):
            item = self.video_list.item(index)
            if item.isSelected():
                video = item.data(Qt.ItemDataRole.UserRole)
                if video:
                    selected.append(video)
        return selected

    def _select_all(self) -> None:
        """全选视频。"""
        for index in range(self.video_list.count()):
            self.video_list.item(index).setSelected(True)

    def _deselect_all(self) -> None:
        """取消全选。"""
        self.video_list.clearSelection()

    def _browse_output(self) -> None:
        """浏览输出目录。"""
        path = QFileDialog.getExistingDirectory(self, "选择输出目录", str(self.output_dir))
        if path:
            self.output_dir = Path(path)
            self._update_output_label()

    def _start_export(self) -> None:
        """开始导出。"""
        selected = self._get_selected()
        if not selected:
            QMessageBox.warning(self, "提示", "先选择要导出的视频")
            return

        self.output_dir.mkdir(parents=True, exist_ok=True)
        selected_device = self.selected_device
        if not selected_device:
            return
        device_id, device_type = selected_device

        self._set_export_ui_enabled(False)
        self.export_progress_bar.setVisible(True)
        self.export_progress_bar.setMaximum(len(selected))
        self.export_progress_bar.setValue(0)
        self.export_cancel_btn.setVisible(True)

        self.convert_thread = QThread()
        self.convert_worker = ConvertWorker(selected, self.output_dir, device_id, device_type)
        self.convert_worker.moveToThread(self.convert_thread)

        self.convert_thread.started.connect(self.convert_worker.run)
        self.convert_worker.progress.connect(self._on_convert_progress)
        self.convert_worker.finished.connect(self._on_convert_finished)
        self.convert_worker.error.connect(self._on_convert_error)

        self.convert_thread.start()

    def _cancel_export(self) -> None:
        """取消导出。"""
        if self.convert_worker:
            self.convert_worker.cancel()

    def _on_convert_progress(self, current: int, total: int, msg: str) -> None:
        """处理转换进度。"""
        self.export_progress_bar.setValue(current)
        self.export_progress_bar.setFormat(f"{current}/{total}")
        self.status_bar.showMessage(msg)

    def _on_convert_finished(self, success: int, total: int) -> None:
        """处理转换完成。"""
        self._cleanup_convert_thread()
        self._set_export_ui_enabled(True)
        self.export_progress_bar.setVisible(False)
        self.export_cancel_btn.setVisible(False)

        QMessageBox.information(
            self, "完成", f"导出完成\n成功: {success}/{total}\n目录: {self.output_dir}"
        )
        self.status_bar.showMessage(f"导出完成: {success}/{total}")

    def _on_convert_error(self, msg: str) -> None:
        """处理转换错误。"""
        self.status_bar.showMessage(msg)

    def _cleanup_convert_thread(self) -> None:
        """清理转换线程。"""
        if self.convert_thread:
            self.convert_thread.quit()
            self.convert_thread.wait()
            self.convert_thread = None
            self.convert_worker = None

    def _set_export_ui_enabled(self, enabled: bool) -> None:
        """设置导出UI启用状态。"""
        widgets = [
            self.device_combo,
            self.source_combo,
            self.refresh_btn,
            self.scan_btn,
            self.select_all_btn,
            self.deselect_btn,
            self.video_list,
            self.browse_btn,
            self.export_btn,
            self.about_btn,
        ]
        for widget in widgets:
            widget.setEnabled(enabled)
        if not enabled:
            self.export_btn.setEnabled(False)
        else:
            self._update_action_states()

    def _update_action_states(self) -> None:
        """更新操作按钮状态。"""
        is_loading = self.scan_state == ScanState.LOADING
        is_paused = self.scan_state == ScanState.PAUSED
        lock_controls = is_loading and not is_paused

        self.device_combo.setEnabled(not lock_controls)
        self.source_combo.setEnabled(not lock_controls)
        self.refresh_btn.setEnabled(not lock_controls)
        self.browse_btn.setEnabled(True)
        self.about_btn.setEnabled(True)

        has_videos = bool(self.videos)
        self.select_all_btn.setEnabled(has_videos)
        self.deselect_btn.setEnabled(has_videos)
        self.video_list.setEnabled(has_videos)
        self.export_btn.setEnabled(has_videos and not is_loading)

        self.scan_btn.setEnabled(
            self.scan_state == ScanState.IDLE and self.selected_device is not None
        )

    def _show_about(self) -> None:
        """显示关于对话框。"""
        AboutDialog(self, self.icon_path).exec()

    def closeEvent(self, event) -> None:
        """处理窗口关闭事件。"""
        running = (self.convert_thread and self.convert_thread.isRunning()) or (
            self.scan_thread and self.scan_thread.isRunning()
        )

        if running:
            reply = QMessageBox.question(
                self,
                "确认",
                "有操作正在进行，确定退出?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
            if self.convert_worker:
                self.convert_worker.cancel()
            if self.scan_worker:
                self.scan_worker.cancel()
            self._cleanup_convert_thread()
            self._cleanup_scan_thread()

        self.auto_refresh_timer.stop()
        event.accept()


# ============================================================
# 程序入口
# ============================================================
def main() -> None:
    """应用程序入口点。"""
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(COLORS["background"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(COLORS["text"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(COLORS["surface"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(COLORS["background"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(COLORS["text"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(COLORS["surface"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(COLORS["text"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(COLORS["primary"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("white"))
    app.setPalette(palette)

    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()