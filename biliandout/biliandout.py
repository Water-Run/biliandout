"""
Android哔哩哔哩视频导出器 (biliandout)
PyQt Windows桌面端图形应用，读取Android设备哔哩哔哩缓存视频并导出为.mp4
"""

from __future__ import annotations

import sys
import os
import json
import subprocess
import shutil
import tempfile
import hashlib
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from enum import Enum, auto

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox, QProgressBar, QGroupBox, QFrame,
    QDialog, QTextBrowser, QStatusBar, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread, QSize
from PyQt6.QtGui import QIcon, QPixmap, QFont, QPalette, QColor, QImage

import biliffm4s


# ============================================================
# 配置
# ============================================================
BILI_SOURCES: dict[str, dict] = {
    "default": {
        "package": "tv.danmaku.bili",
        "name": "普通版"
    },
    "concept": {
        "package": "com.bilibili.app.blue",
        "name": "概念版"
    },
}

VERSION = "1.1.0"

COVER_CACHE_DIR = Path(tempfile.gettempdir()) / "biliandout_covers"
COVER_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# 样式
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
    font-size: 13px;
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    margin-top: 10px;
    padding: 8px;
    background-color: {COLORS["surface"]};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: {COLORS["text"]};
}}

QLabel {{
    color: {COLORS["text"]};
    font-size: 13px;
}}

QLabel#mutedLabel {{
    color: {COLORS["text_muted"]};
    font-size: 12px;
}}

QLabel#pathLabel {{
    color: {COLORS["primary"]};
    font-size: 12px;
}}

QLabel#emptyHint {{
    color: {COLORS["text_secondary"]};
    font-size: 13px;
    line-height: 1.6;
}}

QLabel#videoTitleLabel {{
    font-size: 13px;
    font-weight: bold;
    color: {COLORS["text"]};
}}

QLabel#videoInfoLabel {{
    font-size: 12px;
    color: {COLORS["text_secondary"]};
}}

QPushButton {{
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 6px 14px;
    font-size: 13px;
    color: {COLORS["text"]};
    min-height: 24px;
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
    padding: 8px 20px;
    font-size: 13px;
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
    padding: 4px 12px;
    font-size: 12px;
    min-height: 20px;
}}

QPushButton#pauseBtn:hover {{
    background-color: #ec971f;
}}

QComboBox {{
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 13px;
    color: {COLORS["text"]};
    min-height: 24px;
}}

QComboBox:hover {{
    border-color: {COLORS["border_focus"]};
}}

QComboBox:focus {{
    border-color: {COLORS["border_focus"]};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    selection-background-color: #fff0f5;
    selection-color: {COLORS["text"]};
    outline: none;
    padding: 4px;
}}

QListWidget {{
    background-color: {COLORS["background"]};
    border: none;
    outline: none;
}}

QListWidget::item {{
    margin: 4px 0;
    padding: 0;
    border: none;
}}

QWidget#videoItem {{
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
}}

QWidget#videoItem[selected="true"] {{
    border-color: {COLORS["primary"]};
    background-color: #fff6fa;
}}

QLabel#coverLabel {{
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    background-color: #fdfdfd;
}}

QProgressBar {{
    border: none;
    border-radius: 4px;
    text-align: center;
    background-color: #e8e8e8;
    font-size: 11px;
    min-height: 18px;
    max-height: 18px;
}}

QProgressBar::chunk {{
    background-color: {COLORS["success"]};
    border-radius: 4px;
}}

QProgressBar#scanProgress::chunk {{
    background-color: {COLORS["primary"]};
}}

QStatusBar {{
    background-color: {COLORS["surface"]};
    border-top: 1px solid {COLORS["border"]};
    font-size: 12px;
    color: {COLORS["text_secondary"]};
    padding: 4px;
}}

QTextBrowser {{
    background-color: transparent;
    border: none;
    font-size: 13px;
    color: {COLORS["text"]};
}}

#emptyState {{
    background-color: #fafafa;
    border-radius: 8px;
    border: 1px solid #ebebeb;
    padding: 24px;
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
    resolution: str = ""
    frame_rate: str = ""
    cover_path: Optional[Path] = None

    @property
    def display_title(self) -> str:
        if self.part_title and self.part_title != self.title:
            return f"{self.title} - {self.part_title}"
        return self.title

    @property
    def size_display(self) -> str:
        if self.size_mb >= 1024:
            return f"{self.size_mb / 1024:.2f} GB"
        return f"{self.size_mb:.1f} MB"
    
    @property
    def tech_info(self) -> str:
        parts = []
        if self.resolution:
            parts.append(self.resolution)
        if self.frame_rate:
            parts.append(f"{self.frame_rate}fps")
        if self.quality:
            parts.append(self.quality)
        return " · ".join(parts) if parts else ""


class ScanState(Enum):
    IDLE = auto()
    LOADING = auto()
    PAUSED = auto()


# ============================================================
# 高分屏友好的列表条目
# ============================================================
class VideoListItemWidget(QWidget):
    COVER_SIZE = QSize(120, 140)  # 与 960×1120 保持 6:7 比例

    def __init__(self, video: CachedVideo, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.video = video
        self.setObjectName("videoItem")
        self.setProperty("selected", False)
        self._setup_ui()
        self.update_content(video)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)

        self.cover_holder = QWidget()
        cover_layout = QVBoxLayout(self.cover_holder)
        cover_layout.setContentsMargins(0, 0, 0, 0)
        cover_layout.setSpacing(4)

        self.cover_label = QLabel()
        self.cover_label.setObjectName("coverLabel")
        self.cover_label.setFixedSize(self.COVER_SIZE)
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cover_layout.addWidget(self.cover_label, alignment=Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        cover_layout.addStretch()

        layout.addWidget(self.cover_holder, 0, Qt.AlignmentFlag.AlignTop)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)

        self.title_label = QLabel()
        self.title_label.setObjectName("videoTitleLabel")
        self.title_label.setWordWrap(True)

        self.info_label = QLabel()
        self.info_label.setObjectName("videoInfoLabel")
        self.info_label.setWordWrap(True)

        self.path_label = QLabel()
        self.path_label.setObjectName("mutedLabel")
        self.path_label.setWordWrap(True)
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.info_label)
        text_layout.addWidget(self.path_label)
        text_layout.addStretch()

        layout.addLayout(text_layout, 1)

    def update_content(self, video: CachedVideo):
        self.title_label.setText(video.display_title)

        info_parts = [video.size_display]
        if video.tech_info:
            info_parts.append(video.tech_info)
        if video.bvid:
            info_parts.append(video.bvid)
        self.info_label.setText(" | ".join(info_parts))

        self.path_label.setText(str(video.folder_path))
        self._update_cover(video.cover_path)

    def _update_cover(self, cover_path: Optional[Path]):
        if cover_path and cover_path.exists():
            image = QImage(str(cover_path))
            if not image.isNull():
                dpr = max(self.devicePixelRatioF(), 1.0)
                target = QSize(
                    int(self.COVER_SIZE.width() * dpr),
                    int(self.COVER_SIZE.height() * dpr)
                )
                pixmap = QPixmap.fromImage(image).scaled(
                    target,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                pixmap.setDevicePixelRatio(dpr)
                self.cover_label.setPixmap(pixmap)
                self.cover_holder.setVisible(True)
                return
        self.cover_label.clear()
        self.cover_holder.setVisible(False)

    def apply_selection(self, selected: bool):
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)


# ============================================================
# 扫描工作线程
# ============================================================
class ScanWorker(QObject):
    """视频扫描工作线程"""
    progress = pyqtSignal(int, int)
    found = pyqtSignal(object)
    finished = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, device_id: str, device_type: str, source_key: str, cover_cache_dir: Optional[Path] = None):
        super().__init__()
        self.device_id = device_id
        self.device_type = device_type
        self.source_key = source_key
        self._cancelled = False
        self._paused = False
        self.temp_dir: Optional[Path] = None
        self.cover_cache_dir = cover_cache_dir
        if self.cover_cache_dir:
            self.cover_cache_dir.mkdir(parents=True, exist_ok=True)

    def cancel(self):
        self._cancelled = True

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def is_paused(self) -> bool:
        return self._paused

    def run(self):
        count = 0
        try:
            self.temp_dir = Path(tempfile.mkdtemp())
            if self.device_type == "adb":
                count = self._scan_adb()
            else:
                count = self._scan_drive()
        except Exception as e:
            self.error.emit(f"扫描错误: {str(e)[:50]}")
        finally:
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            self.finished.emit(count)

    def _wait_if_paused(self):
        while self._paused and not self._cancelled:
            QThread.msleep(100)

    def _scan_adb(self) -> int:
        count = 0
        adb = DeviceScanner.find_adb()
        source = BILI_SOURCES.get(self.source_key)
        if not adb or not source:
            return 0

        remote_base = f"/sdcard/Android/data/{source['package']}/download"
        try:
            result = subprocess.run(
                [adb, "-s", self.device_id, "shell", f"ls -1 {remote_base}"],
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            if result.returncode != 0:
                return 0

            folders = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
            total = len(folders)
            for i, folder_name in enumerate(folders):
                self._wait_if_paused()
                if self._cancelled:
                    break

                self.progress.emit(i + 1, total)
                folder_path = f"{remote_base}/{folder_name}"
                videos = self._find_m4s_adb(adb, folder_path, folder_name)
                for video in videos:
                    self.found.emit(video)
                    count += 1
        except Exception as e:
            self.error.emit(f"ADB扫描错误: {str(e)[:40]}")
        return count

    def _find_m4s_adb(self, adb: str, remote_path: str, root_folder: str) -> list[CachedVideo]:
        videos: list[CachedVideo] = []
        if self._cancelled:
            return videos
        try:
            result = subprocess.run(
                [adb, "-s", self.device_id, "shell", f"ls -1 {remote_path}"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            if result.returncode != 0:
                return videos

            files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
            has_video = "video.m4s" in files
            has_audio = "audio.m4s" in files

            if has_video and has_audio:
                video = self._parse_video_adb(adb, remote_path, files, root_folder)
                if video:
                    videos.append(video)
            else:
                for item in files:
                    if item in [".", ".."]:
                        continue
                    sub_path = f"{remote_path}/{item}"
                    videos.extend(self._find_m4s_adb(adb, sub_path, root_folder))
        except:
            pass
        return videos

    def _parse_video_adb(self, adb: str, remote_path: str, files: list[str], root_folder: str) -> Optional[CachedVideo]:
        title = root_folder
        part_title = ""
        bvid = ""
        quality = ""
        resolution = ""
        frame_rate = ""
        has_cover = "cover.jpg" in files
        cover_path = None

        if "index.json" in files:
            try:
                local_index = self.temp_dir / "index.json"
                result = subprocess.run(
                    [adb, "-s", self.device_id, "pull", f"{remote_path}/index.json", str(local_index)],
                    capture_output=True,
                    timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
                if result.returncode == 0 and local_index.exists():
                    with open(local_index, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        resolution, frame_rate = self._parse_index_json(data)
                    local_index.unlink()
            except:
                pass

        current_path = remote_path
        for _ in range(5):
            try:
                entry_path = f"{current_path}/entry.json"
                local_entry = self.temp_dir / "entry.json"
                result = subprocess.run(
                    [adb, "-s", self.device_id, "pull", entry_path, str(local_entry)],
                    capture_output=True,
                    timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
                if result.returncode == 0 and local_entry.exists():
                    with open(local_entry, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        title = data.get("title", title)
                        bvid = data.get("bvid", "")
                        page_data = data.get("page_data", {})
                        part_title = page_data.get("part", "")
                        quality_id = data.get("quality", 0)
                        quality = self._get_quality_name(quality_id)
                    local_entry.unlink()
                    break
            except:
                pass

            parts = current_path.rsplit("/", 1)
            if len(parts) < 2:
                break
            current_path = parts[0]

        if has_cover:
            cover_path = self._pull_cover_adb(adb, remote_path, bvid or root_folder)

        size_mb = 0.0
        try:
            size_result = subprocess.run(
                [adb, "-s", self.device_id, "shell", f"stat -c %s {remote_path}/video.m4s {remote_path}/audio.m4s"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            if size_result.returncode == 0:
                sizes = [int(s.strip()) for s in size_result.stdout.strip().split("\n") if s.strip().isdigit()]
                size_mb = sum(sizes) / (1024 * 1024)
        except:
            pass

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
            cover_path=cover_path
        )

    def _pull_cover_adb(self, adb: str, remote_path: str, identifier: str) -> Optional[Path]:
        if not self.cover_cache_dir:
            return None
        cover_remote = f"{remote_path}/cover.jpg"
        safe_id = hashlib.md5(f"{remote_path}_{identifier}".encode("utf-8")).hexdigest()
        cover_local = self.cover_cache_dir / f"{safe_id}.jpg"
        try:
            result = subprocess.run(
                [adb, "-s", self.device_id, "pull", cover_remote, str(cover_local)],
                capture_output=True,
                timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            if result.returncode == 0 and cover_local.exists():
                return cover_local
        except:
            pass
        if cover_local.exists():
            cover_local.unlink(missing_ok=True)
        return None

    def _scan_drive(self) -> int:
        count = 0
        source = BILI_SOURCES.get(self.source_key)
        if not source:
            return 0

        download_path = Path(f"{self.device_id}/Android/data/{source['package']}/download")
        if not download_path.exists():
            return 0

        folders = list(download_path.iterdir())
        total = len(folders)
        for i, folder in enumerate(folders):
            self._wait_if_paused()
            if self._cancelled:
                break

            if folder.is_dir():
                self.progress.emit(i + 1, total)
                videos = self._find_m4s_local(folder, folder.name)
                for video in videos:
                    self.found.emit(video)
                    count += 1
        return count

    def _find_m4s_local(self, folder: Path, root_folder: str) -> list[CachedVideo]:
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
            try:
                for sub in folder.iterdir():
                    if sub.is_dir():
                        videos.extend(self._find_m4s_local(sub, root_folder))
            except PermissionError:
                pass
        return videos

    def _parse_video_local(self, folder: Path, root_folder: str) -> Optional[CachedVideo]:
        title = root_folder
        part_title = ""
        bvid = ""
        quality = ""
        resolution = ""
        frame_rate = ""
        cover_file = folder / "cover.jpg"
        cover_path = cover_file if cover_file.exists() else None

        index_json = folder / "index.json"
        if index_json.exists():
            try:
                with open(index_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    resolution, frame_rate = self._parse_index_json(data)
            except:
                pass

        current = folder
        for _ in range(5):
            entry = current / "entry.json"
            if entry.exists():
                try:
                    with open(entry, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        title = data.get("title", title)
                        bvid = data.get("bvid", "")
                        page_data = data.get("page_data", {})
                        part_title = page_data.get("part", "")
                        quality_id = data.get("quality", 0)
                        quality = self._get_quality_name(quality_id)
                    break
                except:
                    pass
            parent = current.parent
            if parent == current:
                break
            current = parent

        video_m4s = folder / "video.m4s"
        audio_m4s = folder / "audio.m4s"
        size_mb = (video_m4s.stat().st_size + audio_m4s.stat().st_size) / (1024 * 1024)

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
            cover_path=cover_path
        )

    def _parse_index_json(self, data: dict) -> tuple[str, str]:
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
                fps = video_info.get("frame_rate", "")
                if fps:
                    try:
                        fps_float = float(fps)
                        frame_rate = f"{fps_float:.0f}" if fps_float == int(fps_float) else f"{fps_float:.1f}"
                    except:
                        pass
        except:
            pass
        return resolution, frame_rate

    @staticmethod
    def _get_quality_name(quality_id: int) -> str:
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
            16: "360P"
        }
        return quality_map.get(quality_id, f"{quality_id}P" if quality_id else "")


# ============================================================
# 设备扫描器
# ============================================================
class DeviceScanner:
    """Android设备扫描器"""
    
    _adb_path: Optional[str] = None

    @classmethod
    def find_adb(cls) -> Optional[str]:
        if cls._adb_path:
            return cls._adb_path

        adb_name = "adb.exe" if sys.platform == "win32" else "adb"
        try:
            result = subprocess.run(
                [adb_name, "version"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
            if result.returncode == 0:
                cls._adb_path = adb_name
                return cls._adb_path
        except:
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
        devices: list[tuple[str, str]] = []
        adb = cls.find_adb()
        if not adb:
            return devices

        try:
            result = subprocess.run(
                [adb, "devices", "-l"],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            )
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
        except:
            pass
        return devices

    @classmethod
    def get_drive_devices(cls) -> list[tuple[str, str]]:
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
        devices: list[tuple[str, str, str]] = []
        for dev_id, dev_name in cls.get_adb_devices():
            devices.append((dev_id, dev_name, "adb"))
        for dev_id, dev_name in cls.get_drive_devices():
            devices.append((dev_id, dev_name, "drive"))
        return devices

    @classmethod
    def pull_and_convert(cls, video: CachedVideo, output_path: Path, device_id: str, device_type: str) -> bool:
        if device_type == "drive":
            return biliffm4s.combine(str(video.folder_path), str(output_path))
        elif device_type == "adb":
            adb = cls.find_adb()
            if not adb:
                return False

            temp_dir = Path(tempfile.mkdtemp())
            try:
                local_video = temp_dir / "video.m4s"
                local_audio = temp_dir / "audio.m4s"

                result = subprocess.run(
                    [adb, "-s", device_id, "pull", str(video.video_path), str(local_video)],
                    capture_output=True,
                    timeout=300,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                )
                if result.returncode != 0:
                    return False

                result = subprocess.run(
                    [adb, "-s", device_id, "pull", str(video.audio_path), str(local_audio)],
                    capture_output=True,
                    timeout=300,
                    creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
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
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(int, int)
    error = pyqtSignal(str)

    def __init__(self, videos: list[CachedVideo], output_dir: Path, device_id: str, device_type: str):
        super().__init__()
        self.videos = videos
        self.output_dir = output_dir
        self.device_id = device_id
        self.device_type = device_type
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        success_count = 0
        total = len(self.videos)

        for i, video in enumerate(self.videos):
            if self._cancelled:
                break

            title_short = video.display_title[:30] + "..." if len(video.display_title) > 30 else video.display_title
            self.progress.emit(i + 1, total, f"转换: {title_short}")

            safe_title = self._sanitize_filename(video.display_title)
            output_path = self.output_dir / f"{safe_title}.mp4"

            counter = 1
            while output_path.exists():
                output_path = self.output_dir / f"{safe_title}_{counter}.mp4"
                counter += 1

            try:
                result = DeviceScanner.pull_and_convert(video, output_path, self.device_id, self.device_type)
                if result:
                    success_count += 1
                else:
                    self.error.emit(f"转换失败: {title_short}")
            except Exception as e:
                self.error.emit(f"错误: {str(e)[:50]}")

        self.finished.emit(success_count, total)

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, "_")
        filename = "".join(c for c in filename if ord(c) >= 32)
        return filename[:180].strip()


# ============================================================
# 关于对话框
# ============================================================
class AboutDialog(QDialog):
    def __init__(self, parent=None, icon_path: Path = None):
        super().__init__(parent)
        self.setWindowTitle("关于")
        self.setFixedSize(360, 390)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        header = QHBoxLayout()
        header.setSpacing(16)

        if icon_path and icon_path.exists():
            logo = QLabel()
            pixmap = QPixmap(str(icon_path))
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    QSize(72, 72),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                logo.setPixmap(scaled)
            logo.setFixedSize(72, 72)
            header.addWidget(logo)

        title_box = QVBoxLayout()
        title_box.setSpacing(4)

        title = QLabel("Android哔哩哔哩视频导出器")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        title_box.addWidget(title)

        version = QLabel(f"版本 {VERSION}")
        version.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
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
        info.setHtml(f"""
        <style>
            body {{ font-family: "Microsoft YaHei", sans-serif; font-size: 13px; line-height: 1.8; }}
            .row {{ margin: 6px 0; }}
            .label {{ color: {COLORS["text_secondary"]}; }}
            a {{ color: {COLORS["primary"]}; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
        </style>
        <div class="row"><span class="label">作者:</span> WaterRun</div>
        <div class="row"><span class="label">协作:</span> Claude-Opus-4.5, Nano-Banana-Pro</div>
        <div class="row"><span class="label">许可证:</span> GNU General Public License v3.0</div>
        <div class="row"><span class="label">技术栈:</span> Python, PyQt, PyInstaller, biliffm4s, FFmpeg</div>
        <div class="row"><span class="label">项目链接:</span> <a href="https://github.com/Water-Run/biliandout">GitHub</a></div>
        """)
        layout.addWidget(info, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.setFixedWidth(80)
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)


# ============================================================
# 主窗口
# ============================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.videos: list[CachedVideo] = []
        self.convert_thread: Optional[QThread] = None
        self.convert_worker: Optional[ConvertWorker] = None
        self.scan_thread: Optional[QThread] = None
        self.scan_worker: Optional[ScanWorker] = None
        self.scan_state = ScanState.IDLE

        if getattr(sys, 'frozen', False):
            base_path = Path(sys.executable).parent
        else:
            base_path = Path(__file__).parent.parent
        self.output_dir = base_path / "合并后的视频"

        if getattr(sys, 'frozen', False):
            icon_base = Path(sys._MEIPASS)
        else:
            icon_base = Path(__file__).parent
        self.icon_path = icon_base / "logo.png"

        self._setup_ui()
        self._connect_signals()
        self._refresh_devices()

    def _setup_ui(self):
        self.setWindowTitle("Android哔哩哔哩视频导出器")
        self.setMinimumSize(600, 680)
        self.resize(640, 720)

        if self.icon_path.exists():
            pixmap = QPixmap(str(self.icon_path))
            if not pixmap.isNull():
                icon = QIcon(pixmap)
                self.setWindowIcon(icon)

        self.setStyleSheet(STYLESHEET)

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        device_group = QGroupBox("设备")
        device_layout = QVBoxLayout(device_group)
        device_layout.setSpacing(10)
        device_layout.setContentsMargins(12, 16, 12, 12)

        dev_row = QHBoxLayout()
        dev_row.setSpacing(10)

        dev_label = QLabel("设备:")
        dev_label.setFixedWidth(45)
        dev_row.addWidget(dev_label)

        self.device_combo = QComboBox()
        self.device_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        dev_row.addWidget(self.device_combo)

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setFixedWidth(60)
        dev_row.addWidget(self.refresh_btn)
        device_layout.addLayout(dev_row)

        src_row = QHBoxLayout()
        src_row.setSpacing(10)

        src_label = QLabel("来源:")
        src_label.setFixedWidth(45)
        src_row.addWidget(src_label)

        self.source_combo = QComboBox()
        for key, info in BILI_SOURCES.items():
            self.source_combo.addItem(info["name"], key)
        self.source_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        src_row.addWidget(self.source_combo)

        self.scan_btn = QPushButton("开始加载")
        self.scan_btn.setObjectName("successBtn")
        self.scan_btn.setFixedWidth(90)
        src_row.addWidget(self.scan_btn)

        self.scan_pause_btn = QPushButton("暂停")
        self.scan_pause_btn.setObjectName("pauseBtn")
        self.scan_pause_btn.setFixedWidth(60)
        self.scan_pause_btn.setVisible(False)
        src_row.addWidget(self.scan_pause_btn)

        self.scan_cancel_btn = QPushButton("取消")
        self.scan_cancel_btn.setFixedWidth(60)
        self.scan_cancel_btn.setVisible(False)
        src_row.addWidget(self.scan_cancel_btn)

        device_layout.addLayout(src_row)
        main_layout.addWidget(device_group)

        video_group = QGroupBox("缓存视频")
        video_group_layout = QVBoxLayout(video_group)
        video_group_layout.setSpacing(8)
        video_group_layout.setContentsMargins(12, 12, 12, 12)

        self.video_stack = QWidgetStack()
        video_group_layout.addWidget(self.video_stack.container)

        self.empty_state_widget = QWidget()
        self.empty_state_widget.setObjectName("emptyState")
        empty_layout = QVBoxLayout(self.empty_state_widget)
        empty_layout.setContentsMargins(8, 8, 8, 8)
        self.empty_hint = QLabel()
        self.empty_hint.setObjectName("emptyHint")
        self.empty_hint.setWordWrap(True)
        self.empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_hint)
        self.video_stack.add_page("empty", self.empty_state_widget)

        self.loading_widget = QWidget()
        loading_layout = QVBoxLayout(self.loading_widget)
        loading_layout.setContentsMargins(0, 60, 0, 60)
        loading_layout.addStretch()
        self.loading_progress = QProgressBar()
        self.loading_progress.setObjectName("scanProgress")
        self.loading_progress.setRange(0, 0)
        self.loading_progress.setTextVisible(False)
        self.loading_progress.setMinimumHeight(30)
        loading_layout.addWidget(self.loading_progress)
        loading_layout.addStretch()
        self.video_stack.add_page("loading", self.loading_widget)

        self.video_list = QListWidget()
        self.video_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.video_list.setSpacing(6)
        self.video_list.setUniformItemSizes(False)
        self.video_stack.add_page("list", self.video_list)

        main_layout.addWidget(video_group, 1)

        action_widget = QWidget()
        action_layout = QVBoxLayout(action_widget)
        action_layout.setSpacing(10)
        action_layout.setContentsMargins(0, 0, 0, 0)

        list_actions = QHBoxLayout()
        list_actions.setSpacing(8)

        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.setFixedWidth(70)
        list_actions.addWidget(self.select_all_btn)

        self.deselect_btn = QPushButton("清除选择")
        self.deselect_btn.setFixedWidth(80)
        list_actions.addWidget(self.deselect_btn)

        list_actions.addStretch()

        self.count_label = QLabel("0 个视频")
        self.count_label.setObjectName("mutedLabel")
        list_actions.addWidget(self.count_label)

        action_layout.addLayout(list_actions)

        output_row = QHBoxLayout()
        output_row.setSpacing(10)

        out_label = QLabel("输出目录:")
        out_label.setFixedWidth(65)
        output_row.addWidget(out_label)

        self.output_label = QLabel()
        self.output_label.setObjectName("pathLabel")
        self.output_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._update_output_label()
        output_row.addWidget(self.output_label)

        self.browse_btn = QPushButton("浏览")
        self.browse_btn.setFixedWidth(60)
        output_row.addWidget(self.browse_btn)

        action_layout.addLayout(output_row)
        main_layout.addWidget(action_widget)

        self.export_progress_bar = QProgressBar()
        self.export_progress_bar.setVisible(False)
        main_layout.addWidget(self.export_progress_bar)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.about_btn = QPushButton("关于")
        self.about_btn.setFixedWidth(70)
        btn_row.addWidget(self.about_btn)

        btn_row.addStretch()

        self.export_cancel_btn = QPushButton("取消")
        self.export_cancel_btn.setFixedWidth(70)
        self.export_cancel_btn.setVisible(False)
        btn_row.addWidget(self.export_cancel_btn)

        self.export_btn = QPushButton("导出选中")
        self.export_btn.setObjectName("primaryBtn")
        self.export_btn.setFixedWidth(110)
        btn_row.addWidget(self.export_btn)

        main_layout.addLayout(btn_row)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪，点击「开始加载」手动读取缓存")

        self._refresh_video_view()

    def _update_output_label(self):
        display = str(self.output_dir)
        if len(display) > 45:
            display = "..." + display[-42:]
        self.output_label.setText(display)
        self.output_label.setToolTip(str(self.output_dir))

    def _connect_signals(self):
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

    def _refresh_devices(self):
        self.device_combo.clear()
        self.videos.clear()
        self.video_list.clear()
        self._update_counts()
        devices = DeviceScanner.get_connected_devices()

        if not devices:
            self.device_combo.addItem("未检测到设备", None)
            self.status_bar.showMessage("未检测到设备，请连接后手动点击「开始加载」")
        else:
            for dev_id, dev_name, dev_type in devices:
                self.device_combo.addItem(dev_name, (dev_id, dev_type))
            self.status_bar.showMessage(f"检测到 {len(devices)} 个设备，请手动点击「开始加载」读取缓存")
        self._refresh_video_view()
        self._update_action_states()

    def _on_device_changed(self, index: int):
        self.videos.clear()
        self.video_list.clear()
        self._update_counts()
        self._refresh_video_view()
        self._update_action_states()
        if self.device_combo.currentData() is None:
            self.status_bar.showMessage("未连接设备")
        else:
            self.status_bar.showMessage("设备就绪，需手动点击「开始加载」读取缓存")

    def _scan_videos(self):
        if self.scan_state != ScanState.IDLE:
            return

        data = self.device_combo.currentData()
        if not data:
            QMessageBox.warning(self, "提示", "未选择设备")
            return

        device_id, device_type = data
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
        self.scan_thread.start()
        self._set_scan_state(ScanState.LOADING)
        self.status_bar.showMessage("正在加载缓存视频...")

    def _toggle_scan_pause(self):
        if not self.scan_worker:
            return
        if self.scan_worker.is_paused():
            self.scan_worker.resume()
            self.scan_pause_btn.setText("暂停")
            self._set_scan_state(ScanState.LOADING)
            self.status_bar.showMessage("继续加载缓存视频...")
        else:
            self.scan_worker.pause()
            self.scan_pause_btn.setText("继续")
            self._set_scan_state(ScanState.PAUSED)
            self.status_bar.showMessage("加载已暂停，可继续或取消")

    def _cancel_scan(self):
        if self.scan_worker:
            self.scan_worker.cancel()
            self.status_bar.showMessage("正在取消加载...")

    def _on_scan_progress(self, current: int, total: int):
        if total <= 0:
            self.loading_progress.setRange(0, 0)
        else:
            self.loading_progress.setRange(0, total)
            self.loading_progress.setValue(current)
        self.status_bar.showMessage(f"扫描文件夹 ({current}/{total})")

    def _on_video_found(self, video: CachedVideo):
        self.videos.append(video)
        self._add_video_item(video)
        self._update_counts()
        if self.scan_state != ScanState.LOADING:
            self._refresh_video_view()

    def _on_scan_finished(self, count: int):
        self._cleanup_scan_thread()
        self._set_scan_state(ScanState.IDLE)
        self.loading_progress.setRange(0, 100)
        self.loading_progress.setValue(0)

        if count > 0:
            self.status_bar.showMessage(f"扫描完成，找到 {count} 个缓存视频")
        else:
            self.status_bar.showMessage("未找到缓存视频")
            self._set_empty_hint("no_video")
        self._refresh_video_view()

    def _on_scan_error(self, msg: str):
        self.status_bar.showMessage(msg)

    def _cleanup_scan_thread(self):
        if self.scan_thread:
            self.scan_thread.quit()
            self.scan_thread.wait()
            self.scan_thread = None
            self.scan_worker = None

    def _add_video_item(self, video: CachedVideo):
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, video)

        widget = VideoListItemWidget(video)
        item.setSizeHint(widget.sizeHint())

        self.video_list.addItem(item)
        self.video_list.setItemWidget(item, widget)
        self._sync_item_selection_styles()

    def _sync_item_selection_styles(self):
        for i in range(self.video_list.count()):
            item = self.video_list.item(i)
            widget = self.video_list.itemWidget(item)
            if isinstance(widget, VideoListItemWidget):
                widget.apply_selection(item.isSelected())

    def _clear_cover_cache(self):
        if not COVER_CACHE_DIR.exists():
            return
        for file in COVER_CACHE_DIR.glob("*.jpg"):
            try:
                file.unlink()
            except:
                pass

    def _update_counts(self):
        self.count_label.setText(f"{len(self.videos)} 个视频")

    def _refresh_video_view(self):
        if self.scan_state == ScanState.LOADING:
            self.video_stack.show_page("loading")
        else:
            if self.videos:
                self.video_stack.show_page("list")
            else:
                self._update_empty_hint()
                self.video_stack.show_page("empty")
        self._update_action_states()

    def _update_empty_hint(self):
        data = self.device_combo.currentData()
        if data is None:
            text = (
                "<b>如何连接 Android 设备</b><br><br>"
                "1. 启用开发者选项并打开 USB 调试<br>"
                "2. 使用数据线连接到本机<br>"
                "3. 在设备上打开 USB 文件传输模式<br><br>"
                "连接后请手动点击「开始加载」，程序不会自动扫描。"
            )
        else:
            text = (
                "<b>设备已就绪</b><br><br>"
                "请手动点击「开始加载」读取哔哩哔哩缓存视频。<br>"
                "未操作时不会自动扫描。"
            )
        if not self.videos and self.scan_state == ScanState.IDLE:
            self.empty_hint.setText(text)
        elif not self.videos:
            self.empty_hint.setText("暂无可用缓存，确认已在哔哩哔哩 App 中缓存视频")

    def _set_scan_state(self, state: ScanState):
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
            self.scan_btn.setEnabled(self.device_combo.currentData() is not None)
            self.scan_pause_btn.setVisible(False)
            self.scan_cancel_btn.setVisible(False)
        self._refresh_video_view()

    def _get_selected(self) -> list[CachedVideo]:
        selected: list[CachedVideo] = []
        for i in range(self.video_list.count()):
            item = self.video_list.item(i)
            if item.isSelected():
                video = item.data(Qt.ItemDataRole.UserRole)
                if video:
                    selected.append(video)
        return selected

    def _select_all(self):
        for i in range(self.video_list.count()):
            self.video_list.item(i).setSelected(True)

    def _deselect_all(self):
        self.video_list.clearSelection()

    def _browse_output(self):
        path = QFileDialog.getExistingDirectory(self, "选择输出目录", str(self.output_dir))
        if path:
            self.output_dir = Path(path)
            self._update_output_label()

    def _start_export(self):
        selected = self._get_selected()
        if not selected:
            QMessageBox.warning(self, "提示", "先选择要导出的视频")
            return

        self.output_dir.mkdir(parents=True, exist_ok=True)

        data = self.device_combo.currentData()
        if not data:
            return
        device_id, device_type = data

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

    def _cancel_export(self):
        if self.convert_worker:
            self.convert_worker.cancel()

    def _on_convert_progress(self, current: int, total: int, msg: str):
        self.export_progress_bar.setValue(current)
        self.export_progress_bar.setFormat(f"{current}/{total}")
        self.status_bar.showMessage(msg)

    def _on_convert_finished(self, success: int, total: int):
        self._cleanup_convert_thread()
        self._set_export_ui_enabled(True)
        self.export_progress_bar.setVisible(False)
        self.export_cancel_btn.setVisible(False)

        QMessageBox.information(
            self, "完成",
            f"导出完成\n\n成功: {success} / {total}\n输出目录: {self.output_dir}"
        )
        self.status_bar.showMessage(f"导出完成: {success}/{total}")

    def _on_convert_error(self, msg: str):
        self.status_bar.showMessage(msg)

    def _cleanup_convert_thread(self):
        if self.convert_thread:
            self.convert_thread.quit()
            self.convert_thread.wait()
            self.convert_thread = None
            self.convert_worker = None

    def _set_export_ui_enabled(self, enabled: bool):
        widgets = [
            self.device_combo, self.source_combo, self.refresh_btn, self.scan_btn,
            self.select_all_btn, self.deselect_btn, self.video_list,
            self.browse_btn, self.export_btn, self.about_btn
        ]
        for widget in widgets:
            widget.setEnabled(enabled and not (widget is self.video_list and len(self.videos) == 0))
        if not enabled:
            self.export_btn.setEnabled(False)
        else:
            self.export_btn.setEnabled(len(self.videos) > 0)

    def _update_action_states(self):
        locked = self.scan_state == ScanState.LOADING
        widgets = [
            self.device_combo, self.source_combo, self.refresh_btn,
            self.browse_btn, self.select_all_btn, self.deselect_btn,
            self.about_btn
        ]
        for widget in widgets:
            widget.setEnabled(not locked)

        has_videos = len(self.videos) > 0
        self.video_list.setEnabled(not locked and has_videos)
        self.export_btn.setEnabled(not locked and has_videos)
        self.scan_btn.setEnabled(self.scan_state == ScanState.IDLE and self.device_combo.currentData() is not None)

    def _show_about(self):
        AboutDialog(self, self.icon_path).exec()

    def closeEvent(self, event):
        running = (self.convert_thread and self.convert_thread.isRunning()) or \
                  (self.scan_thread and self.scan_thread.isRunning())

        if running:
            reply = QMessageBox.question(
                self, "确认", "有操作正在进行，确定退出?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
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
        event.accept()


class QWidgetStack:
    """简易堆栈容器，保持老式风格"""
    def __init__(self):
        self.container = QWidget()
        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.pages: dict[str, QWidget] = {}
        self.current_key: Optional[str] = None

    def add_page(self, key: str, widget: QWidget):
        self.pages[key] = widget
        widget.setVisible(False)
        self.layout.addWidget(widget)
        if self.current_key is None:
            self.show_page(key)

    def show_page(self, key: str):
        if key == self.current_key:
            return
        if self.current_key and self.current_key in self.pages:
            self.pages[self.current_key].setVisible(False)
        if key in self.pages:
            self.pages[key].setVisible(True)
            self.current_key = key


# ============================================================
# 入口
# ============================================================
def main():
    # Qt6 默认开启高 DPI，设置舍入策略即可，避免 Qt5 专用属性导致异常
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

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