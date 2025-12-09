# biliandout.py
"""
Android哔哩哔哩视频导出器 (biliandout)
PyQt Windows桌面端图形应用，读取Android设备哔哩哔哩缓存视频并导出为.mp4
"""

import sys
import os
import json
import subprocess
import shutil
import tempfile
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QListWidget, QListWidgetItem,
    QFileDialog, QMessageBox, QProgressBar, QGroupBox, QFrame,
    QDialog, QTextBrowser, QStatusBar, QSizePolicy, QScrollArea,
    QSpacerItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread, QSize
from PyQt6.QtGui import QIcon, QPixmap, QFont, QPalette, QColor

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
    margin-top: 16px;
    padding: 0px;
    padding-top: 4px;
    background-color: {COLORS["surface"]};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
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
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 6px;
    font-size: 12px;
    outline: none;
    padding: 2px;
}}

QListWidget::item {{
    padding: 8px 10px;
    border-bottom: 1px solid #f0f0f0;
    border-radius: 4px;
    margin: 1px 0;
}}

QListWidget::item:selected {{
    background-color: #fff0f5;
    border: 1px solid {COLORS["primary"]};
}}

QListWidget::item:hover:!selected {{
    background-color: #fafafa;
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

QScrollArea {{
    border: none;
    background-color: transparent;
}}

#guideWidget {{
    background-color: #fafafa;
    border: 2px dashed #ddd;
    border-radius: 8px;
}}

#guideLabel {{
    color: {COLORS["text_secondary"]};
    font-size: 13px;
    line-height: 1.8;
}}

#videoGroupContent {{
    background-color: transparent;
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
        """技术信息"""
        parts = []
        if self.resolution:
            parts.append(self.resolution)
        if self.frame_rate:
            parts.append(f"{self.frame_rate}fps")
        if self.quality:
            parts.append(self.quality)
        return " · ".join(parts) if parts else ""

# ============================================================
# 扫描工作线程
# ============================================================
class ScanWorker(QObject):
    """视频扫描工作线程"""
    progress = pyqtSignal(int, int)  # 当前, 总数
    found = pyqtSignal(object)  # 找到视频
    finished = pyqtSignal(int)  # 完成，返回数量
    error = pyqtSignal(str)

    def __init__(self, device_id: str, device_type: str, source_key: str):
        super().__init__()
        self.device_id = device_id
        self.device_type = device_type
        self.source_key = source_key
        self._cancelled = False
        self._paused = False
        self.temp_dir: Optional[Path] = None

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
        """等待暂停状态解除"""
        while self._paused and not self._cancelled:
            QThread.msleep(100)

    def _scan_adb(self) -> int:
        """通过ADB扫描"""
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
        """递归查找m4s文件（ADB）"""
        videos = []
        
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

    def _parse_video_adb(self, adb: str, remote_path: str, files: list, root_folder: str) -> Optional[CachedVideo]:
        """解析视频信息（ADB）"""
        title = root_folder
        part_title = ""
        bvid = ""
        quality = ""
        resolution = ""
        frame_rate = ""
        
        # 读取 index.json
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
        
        # 向上查找 entry.json
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
        
        # 获取文件大小
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
            frame_rate=frame_rate
        )

    def _scan_drive(self) -> int:
        """扫描驱动器"""
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
        """递归查找本地m4s文件"""
        videos = []
        
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
        """解析本地视频信息"""
        title = root_folder
        part_title = ""
        bvid = ""
        quality = ""
        resolution = ""
        frame_rate = ""
        
        # 读取 index.json
        index_json = folder / "index.json"
        if index_json.exists():
            try:
                with open(index_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    resolution, frame_rate = self._parse_index_json(data)
            except:
                pass
        
        # 向上查找 entry.json
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
        
        # 文件大小
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
            frame_rate=frame_rate
        )

    def _parse_index_json(self, data: dict) -> tuple[str, str]:
        """解析 index.json 获取分辨率和帧率"""
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
        """获取画质名称"""
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
        """查找ADB可执行文件"""
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
        """通过ADB获取已连接设备"""
        devices = []
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
        """扫描驱动器盘符"""
        devices = []
        
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
        """获取所有已连接设备"""
        devices = []
        
        for dev_id, dev_name in cls.get_adb_devices():
            devices.append((dev_id, dev_name, "adb"))
            
        for dev_id, dev_name in cls.get_drive_devices():
            devices.append((dev_id, dev_name, "drive"))
            
        return devices

    @classmethod
    def pull_and_convert(cls, video: CachedVideo, output_path: Path, device_id: str, device_type: str) -> bool:
        """拉取文件并转换"""
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
    """视频转换工作线程"""
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
                result = DeviceScanner.pull_and_convert(
                    video, output_path, self.device_id, self.device_type
                )
                if result:
                    success_count += 1
                else:
                    self.error.emit(f"转换失败: {title_short}")
            except Exception as e:
                self.error.emit(f"错误: {str(e)[:50]}")

        self.finished.emit(success_count, total)

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """清理文件名"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, "_")
        filename = "".join(c for c in filename if ord(c) >= 32)
        return filename[:180].strip()


# ============================================================
# 关于对话框
# ============================================================
class AboutDialog(QDialog):
    """关于对话框"""

    def __init__(self, parent=None, icon_path: Path = None):
        super().__init__(parent)
        self.setWindowTitle("关于")
        self.setFixedSize(360, 390)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # 头部
        header = QHBoxLayout()
        header.setSpacing(16)
        
        if icon_path and icon_path.exists():
            logo = QLabel()
            pixmap = QPixmap(str(icon_path))
            scaled = pixmap.scaled(
                64, 64,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            logo.setPixmap(scaled)
            logo.setFixedSize(64, 64)
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

        # 分隔线
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {COLORS['border']};")
        sep.setFixedHeight(1)
        layout.addWidget(sep)

        # 信息
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

        # 关闭按钮
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
    """主窗口"""

    def __init__(self):
        super().__init__()

        self.videos: list[CachedVideo] = []
        self.convert_thread: Optional[QThread] = None
        self.convert_worker: Optional[ConvertWorker] = None
        self.scan_thread: Optional[QThread] = None
        self.scan_worker: Optional[ScanWorker] = None

        # 默认输出目录
        if getattr(sys, 'frozen', False):
            base_path = Path(sys.executable).parent
        else:
            base_path = Path(__file__).parent.parent
        self.output_dir = base_path / "合并后的视频"

        # 图标路径
        if getattr(sys, 'frozen', False):
            icon_base = Path(sys._MEIPASS)
        else:
            icon_base = Path(__file__).parent
        self.icon_path = icon_base / "logo.png"

        self._setup_ui()
        self._connect_signals()
        self._refresh_devices()

    def _setup_ui(self):
        """构建界面"""
        self.setWindowTitle("Android哔哩哔哩视频导出器")
        self.setMinimumSize(560, 640)
        self.resize(560, 640)

        if self.icon_path.exists():
            self.setWindowIcon(QIcon(str(self.icon_path)))

        self.setStyleSheet(STYLESHEET)

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # ===== 设备设置 =====
        device_group = QGroupBox("设备")
        device_layout = QVBoxLayout(device_group)
        device_layout.setSpacing(10)
        device_layout.setContentsMargins(12, 16, 12, 12)

        # 设备选择行
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

        # 数据源选择行
        src_row = QHBoxLayout()
        src_row.setSpacing(10)

        src_label = QLabel("扫描:")
        src_label.setFixedWidth(45)
        src_row.addWidget(src_label)

        self.source_combo = QComboBox()
        for key, info in BILI_SOURCES.items():
            self.source_combo.addItem(info["name"], key)
        self.source_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        src_row.addWidget(self.source_combo)

        self.scan_btn = QPushButton("扫描")
        self.scan_btn.setObjectName("successBtn")
        self.scan_btn.setFixedWidth(60)
        src_row.addWidget(self.scan_btn)

        device_layout.addLayout(src_row)
        main_layout.addWidget(device_group)

        # ===== 缓存视频 =====
        video_group = QGroupBox("缓存视频")
        video_group_layout = QVBoxLayout(video_group)
        video_group_layout.setSpacing(0)
        video_group_layout.setContentsMargins(0, 12, 0, 0)

        # 视频列表
        self.video_list = QListWidget()
        self.video_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.video_list.setMinimumHeight(240)
        self.video_list.setVisible(False)
        video_group_layout.addWidget(self.video_list)

        # 引导提示
        self.guide_widget = QWidget()
        self.guide_widget.setObjectName("guideWidget")
        guide_layout = QVBoxLayout(self.guide_widget)
        guide_layout.setContentsMargins(24, 24, 24, 24)

        self.guide_label = QLabel()
        self.guide_label.setObjectName("guideLabel")
        self.guide_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.guide_label.setWordWrap(True)
        self.guide_label.setText(
            "<div style='text-align: center; line-height: 2;'>"
            "<b style='font-size: 14px;'>如何连接 Android 设备</b><br><br>"
            "1. 进入开发者选项，打开 USB 调试<br>"
            "2. 使用数据线连接至此设备<br>"
            "3. 在 Android 设备上开启 USB 文件传输模式<br><br>"
            "<span style='color: #999;'>连接设备后点击「刷新」按钮</span>"
            "</div>"
        )
        guide_layout.addWidget(self.guide_label)

        self.guide_widget.setMinimumHeight(240)
        video_group_layout.addWidget(self.guide_widget)

        main_layout.addWidget(video_group, 1)

        # ===== 扫描进度条（视频框下方）=====
        self.scan_progress_widget = QWidget()
        scan_progress_layout = QHBoxLayout(self.scan_progress_widget)
        scan_progress_layout.setContentsMargins(0, 0, 0, 0)
        scan_progress_layout.setSpacing(8)

        self.scan_progress_bar = QProgressBar()
        self.scan_progress_bar.setObjectName("scanProgress")
        self.scan_progress_bar.setFormat("扫描中 %v/%m")
        scan_progress_layout.addWidget(self.scan_progress_bar, 1)

        self.scan_pause_btn = QPushButton("暂停")
        self.scan_pause_btn.setObjectName("pauseBtn")
        self.scan_pause_btn.setFixedWidth(50)
        scan_progress_layout.addWidget(self.scan_pause_btn)

        self.scan_cancel_btn = QPushButton("取消")
        self.scan_cancel_btn.setFixedWidth(50)
        scan_progress_layout.addWidget(self.scan_cancel_btn)

        self.scan_progress_widget.setVisible(False)
        main_layout.addWidget(self.scan_progress_widget)

        # ===== 操作区域 =====
        action_widget = QWidget()
        action_layout = QVBoxLayout(action_widget)
        action_layout.setSpacing(10)
        action_layout.setContentsMargins(0, 0, 0, 0)

        # 列表操作行
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

        # 输出目录行
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

        # ===== 导出进度条 =====
        self.export_progress_bar = QProgressBar()
        self.export_progress_bar.setVisible(False)
        main_layout.addWidget(self.export_progress_bar)

        # ===== 底部按钮 =====
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

        # ===== 状态栏 =====
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

    def _update_output_label(self):
        """更新输出目录显示"""
        display = str(self.output_dir)
        if len(display) > 45:
            display = "..." + display[-42:]
        self.output_label.setText(display)
        self.output_label.setToolTip(str(self.output_dir))

    def _connect_signals(self):
        """连接信号"""
        self.refresh_btn.clicked.connect(self._refresh_devices)
        self.scan_btn.clicked.connect(self._scan_videos)
        self.browse_btn.clicked.connect(self._browse_output)
        self.export_btn.clicked.connect(self._start_export)
        self.export_cancel_btn.clicked.connect(self._cancel_export)
        self.select_all_btn.clicked.connect(self._select_all)
        self.deselect_btn.clicked.connect(self._deselect_all)
        self.about_btn.clicked.connect(self._show_about)
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)

        # 扫描控制
        self.scan_pause_btn.clicked.connect(self._toggle_scan_pause)
        self.scan_cancel_btn.clicked.connect(self._cancel_scan)

    def _refresh_devices(self):
        """刷新设备列表"""
        self.device_combo.clear()
        self.videos.clear()
        self.video_list.clear()
        self._update_video_display()

        devices = DeviceScanner.get_connected_devices()

        if not devices:
            self.device_combo.addItem("未检测到设备", None)
            self.scan_btn.setEnabled(False)
            self._show_guide(True)
            
            adb = DeviceScanner.find_adb()
            if adb:
                self.status_bar.showMessage("未检测到设备 - 确认USB调试已开启并授权")
            else:
                self.status_bar.showMessage("未检测到设备 - 未找到ADB，仅支持文件传输模式")
        else:
            for dev_id, dev_name, dev_type in devices:
                self.device_combo.addItem(dev_name, (dev_id, dev_type))
            self.scan_btn.setEnabled(True)
            self._show_guide(False)
            self.status_bar.showMessage(f"检测到 {len(devices)} 个设备")

    def _show_guide(self, show: bool):
        """显示/隐藏引导提示"""
        self.guide_widget.setVisible(show)
        self.video_list.setVisible(not show and len(self.videos) > 0)
        
        # 禁用列表操作按钮
        has_videos = len(self.videos) > 0
        self.select_all_btn.setEnabled(has_videos)
        self.deselect_btn.setEnabled(has_videos)
        self.export_btn.setEnabled(has_videos)

    def _update_video_display(self):
        """更新视频显示"""
        has_videos = len(self.videos) > 0
        self.video_list.setVisible(has_videos)
        self.guide_widget.setVisible(not has_videos and self.device_combo.currentData() is None)
        
        self.select_all_btn.setEnabled(has_videos)
        self.deselect_btn.setEnabled(has_videos)
        self.export_btn.setEnabled(has_videos)
        self.count_label.setText(f"{len(self.videos)} 个视频")

    def _on_device_changed(self, index: int):
        """设备切换"""
        self.videos.clear()
        self.video_list.clear()
        self._update_video_display()
        
        data = self.device_combo.currentData()
        if data is None:
            self._show_guide(True)
        else:
            self._show_guide(False)

    def _scan_videos(self):
        """扫描视频"""
        data = self.device_combo.currentData()
        if not data:
            QMessageBox.warning(self, "提示", "未选择设备")
            return

        device_id, device_type = data
        source_key = self.source_combo.currentData()

        # 清空现有数据
        self.videos.clear()
        self.video_list.clear()

        # 显示进度
        self.scan_progress_widget.setVisible(True)
        self.scan_progress_bar.setMaximum(100)
        self.scan_progress_bar.setValue(0)
        self.scan_progress_bar.setFormat("准备扫描...")
        self.scan_pause_btn.setText("暂停")

        self.guide_widget.setVisible(False)
        self.video_list.setVisible(True)

        self._set_scan_ui_enabled(False)

        # 启动扫描线程
        self.scan_thread = QThread()
        self.scan_worker = ScanWorker(device_id, device_type, source_key)
        self.scan_worker.moveToThread(self.scan_thread)

        self.scan_thread.started.connect(self.scan_worker.run)
        self.scan_worker.progress.connect(self._on_scan_progress)
        self.scan_worker.found.connect(self._on_video_found)
        self.scan_worker.finished.connect(self._on_scan_finished)
        self.scan_worker.error.connect(self._on_scan_error)

        self.scan_thread.start()

    def _toggle_scan_pause(self):
        """切换扫描暂停状态"""
        if self.scan_worker:
            if self.scan_worker.is_paused():
                self.scan_worker.resume()
                self.scan_pause_btn.setText("暂停")
                self.status_bar.showMessage("继续扫描...")
            else:
                self.scan_worker.pause()
                self.scan_pause_btn.setText("继续")
                self.status_bar.showMessage("扫描已暂停")

    def _cancel_scan(self):
        """取消扫描"""
        if self.scan_worker:
            self.scan_worker.cancel()
            self.status_bar.showMessage("正在取消...")

    def _on_scan_progress(self, current: int, total: int):
        """扫描进度"""
        self.scan_progress_bar.setMaximum(total)
        self.scan_progress_bar.setValue(current)
        self.scan_progress_bar.setFormat(f"扫描中 {current}/{total}")
        self.status_bar.showMessage(f"扫描文件夹 ({current}/{total})")

    def _on_video_found(self, video: CachedVideo):
        """找到视频"""
        self.videos.append(video)
        self._add_video_item(video)
        self.count_label.setText(f"{len(self.videos)} 个视频")

    def _on_scan_finished(self, count: int):
        """扫描完成"""
        self._cleanup_scan_thread()
        self._set_scan_ui_enabled(True)
        self.scan_progress_widget.setVisible(False)

        self._update_video_display()

        if count > 0:
            self.status_bar.showMessage(f"扫描完成，找到 {count} 个缓存视频")
        else:
            self.status_bar.showMessage("未找到缓存视频")
            self.video_list.setVisible(False)
            self.guide_label.setText(
                "<div style='text-align: center; line-height: 2;'>"
                "<b style='font-size: 14px;'>未找到缓存视频</b><br><br>"
                "<span style='color: #999;'>确认已在哔哩哔哩 App 中缓存视频</span>"
                "</div>"
            )
            self.guide_widget.setVisible(True)

    def _on_scan_error(self, msg: str):
        """扫描错误"""
        self.status_bar.showMessage(msg)

    def _cleanup_scan_thread(self):
        """清理扫描线程"""
        if self.scan_thread:
            self.scan_thread.quit()
            self.scan_thread.wait()
            self.scan_thread = None
            self.scan_worker = None

    def _set_scan_ui_enabled(self, enabled: bool):
        """设置扫描时的UI状态"""
        self.device_combo.setEnabled(enabled)
        self.source_combo.setEnabled(enabled)
        self.refresh_btn.setEnabled(enabled)
        self.scan_btn.setEnabled(enabled and self.device_combo.currentData() is not None)

    def _update_list(self):
        """更新列表"""
        self.video_list.clear()
        for video in self.videos:
            self._add_video_item(video)
        self._update_video_display()

    def _get_selected(self) -> list[CachedVideo]:
        """获取选中项"""
        selected = []
        for i in range(self.video_list.count()):
            item = self.video_list.item(i)
            if item.isSelected():
                video = item.data(Qt.ItemDataRole.UserRole)
                if video:
                    selected.append(video)
        return selected

    def _select_all(self):
        """全选"""
        for i in range(self.video_list.count()):
            self.video_list.item(i).setSelected(True)

    def _deselect_all(self):
        """清除选择"""
        self.video_list.clearSelection()

    def _browse_output(self):
        """选择输出目录"""
        path = QFileDialog.getExistingDirectory(self, "选择输出目录", str(self.output_dir))
        if path:
            self.output_dir = Path(path)
            self._update_output_label()

    def _start_export(self):
        """开始导出"""
        selected = self._get_selected()
        if not selected:
            QMessageBox.warning(self, "提示", "先选择要导出的视频")
            return

        # 确保输出目录存在
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
        """取消导出"""
        if self.convert_worker:
            self.convert_worker.cancel()

    def _on_convert_progress(self, current: int, total: int, msg: str):
        """转换进度"""
        self.export_progress_bar.setValue(current)
        self.export_progress_bar.setFormat(f"{current}/{total}")
        self.status_bar.showMessage(msg)

    def _on_convert_finished(self, success: int, total: int):
        """转换完成"""
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
        """转换错误"""
        self.status_bar.showMessage(msg)

    def _cleanup_convert_thread(self):
        """清理转换线程"""
        if self.convert_thread:
            self.convert_thread.quit()
            self.convert_thread.wait()
            self.convert_thread = None
            self.convert_worker = None

    def _set_export_ui_enabled(self, enabled: bool):
        """设置导出时的UI状态"""
        self.device_combo.setEnabled(enabled)
        self.source_combo.setEnabled(enabled)
        self.refresh_btn.setEnabled(enabled)
        self.scan_btn.setEnabled(enabled and self.device_combo.currentData() is not None)
        self.browse_btn.setEnabled(enabled)
        self.export_btn.setEnabled(enabled and len(self.videos) > 0)
        self.select_all_btn.setEnabled(enabled and len(self.videos) > 0)
        self.deselect_btn.setEnabled(enabled and len(self.videos) > 0)
        self.video_list.setEnabled(enabled)
        self.about_btn.setEnabled(enabled)

    def _set_ui_enabled(self, enabled: bool, scanning: bool = False):
        """设置UI状态"""
        self.device_combo.setEnabled(enabled)
        self.source_combo.setEnabled(enabled)
        self.refresh_btn.setEnabled(enabled)
        self.scan_btn.setEnabled(enabled and self.device_combo.currentData() is not None)
        self.browse_btn.setEnabled(enabled)
        self.export_btn.setEnabled(enabled and len(self.videos) > 0)
        self.select_all_btn.setEnabled(enabled and len(self.videos) > 0)
        self.deselect_btn.setEnabled(enabled and len(self.videos) > 0)
        self.video_list.setEnabled(enabled)
        self.about_btn.setEnabled(enabled)
        
        if scanning:
            self.cancel_btn.setVisible(True)
        elif enabled:
            self.cancel_btn.setVisible(False)

    def _show_about(self):
        """显示关于"""
        AboutDialog(self, self.icon_path).exec()

    def closeEvent(self, event):
        """关闭事件"""
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


# ============================================================
# 入口
# ============================================================
def main():
    os.environ["QT_QPA_PLATFORM"] = "windows:darkmode=0"

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 设置调色板
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

    # 设置默认字体
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()