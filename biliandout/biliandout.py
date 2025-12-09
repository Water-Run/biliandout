"""
Android哔哩哔哩视频导出器 (biliandout)
一个PyQT Windows桌面端图形应用，可自动读取连接至计算机的安卓设备上的哔哩哔哩缓存视频，并导出为.mp4
"""

import sys
import os
import json
import subprocess
import threading
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QTableWidget, QTableWidgetItem,
    QFileDialog, QMessageBox, QProgressBar, QGroupBox, QHeaderView,
    QDialog, QTextBrowser, QCheckBox, QStatusBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QThread
from PyQt6.QtGui import QIcon, QPixmap, QFont

import biliffm4s


class BiliSource(Enum):
    """哔哩哔哩版本源"""
    DEFAULT = ("tv.danmaku.bili", "哔哩哔哩")
    CONCEPT = ("com.bilibili.app.blue", "哔哩哔哩概念版")

    def __init__(self, package: str, display_name: str):
        self.package = package
        self.display_name = display_name


@dataclass
class CachedVideo:
    """缓存视频信息"""
    folder_path: Path
    video_path: Path
    audio_path: Path
    title: str = "未知标题"
    part_title: str = ""
    size_mb: float = 0.0

    @property
    def display_title(self) -> str:
        if self.part_title:
            return f"{self.title} - {self.part_title}"
        return self.title


class DeviceScanner:
    """Android设备扫描器"""

    @staticmethod
    def get_connected_devices() -> list[tuple[str, str]]:
        """获取已连接的Android设备列表，返回 [(drive_letter, device_name), ...]"""
        devices = []

        # 扫描所有可能的驱动器
        for drive_letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
            drive_path = Path(f"{drive_letter}:/")
            if not drive_path.exists():
                continue

            # 检查是否存在Android目录结构
            android_path = drive_path / "Android" / "data"
            if android_path.exists():
                # 检查是否有哔哩哔哩目录
                for source in BiliSource:
                    bili_path = android_path / source.package / "download"
                    if bili_path.exists():
                        device_name = f"设备 ({drive_letter}:)"
                        if (drive_letter, device_name) not in devices:
                            devices.append((drive_letter, device_name))
                        break

        return devices

    @staticmethod
    def scan_cached_videos(drive_letter: str, source: BiliSource) -> list[CachedVideo]:
        """扫描指定设备和源的缓存视频"""
        videos = []
        download_path = Path(f"{drive_letter}:/Android/data/{source.package}/download")

        if not download_path.exists():
            return videos

        # 遍历download目录下的所有文件夹
        for video_folder in download_path.iterdir():
            if not video_folder.is_dir():
                continue

            # 递归查找video.m4s和audio.m4s
            found_videos = DeviceScanner._find_m4s_pairs(video_folder)

            for folder_path, video_path, audio_path in found_videos:
                # 尝试读取视频信息
                title, part_title = DeviceScanner._read_video_info(folder_path)

                # 计算文件大小
                size_mb = (video_path.stat().st_size + audio_path.stat().st_size) / (1024 * 1024)

                videos.append(CachedVideo(
                    folder_path=folder_path,
                    video_path=video_path,
                    audio_path=audio_path,
                    title=title,
                    part_title=part_title,
                    size_mb=size_mb
                ))

        return videos

    @staticmethod
    def _find_m4s_pairs(folder: Path) -> list[tuple[Path, Path, Path]]:
        """递归查找文件夹中的m4s文件对"""
        pairs = []

        video_m4s = folder / "video.m4s"
        audio_m4s = folder / "audio.m4s"

        if video_m4s.exists() and audio_m4s.exists():
            pairs.append((folder, video_m4s, audio_m4s))

        # 递归子文件夹
        for subfolder in folder.iterdir():
            if subfolder.is_dir():
                pairs.extend(DeviceScanner._find_m4s_pairs(subfolder))

        return pairs

    @staticmethod
    def _read_video_info(folder: Path) -> tuple[str, str]:
        """从entry.json或index.json读取视频信息"""
        title = "未知标题"
        part_title = ""

        # 向上查找entry.json
        current = folder
        for _ in range(5):  # 最多向上5层
            entry_json = current / "entry.json"
            if entry_json.exists():
                try:
                    with open(entry_json, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        title = data.get("title", title)
                        # 获取分P标题
                        page_data = data.get("page_data", {})
                        part_title = page_data.get("part", "")
                        break
                except (json.JSONDecodeError, IOError):
                    pass

            parent = current.parent
            if parent == current:
                break
            current = parent

        return title, part_title


class ConvertWorker(QObject):
    """视频转换工作线程"""
    progress = pyqtSignal(int, int, str)  # current, total, message
    finished = pyqtSignal(int, int)  # success_count, total_count
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

            # 生成输出文件名
            safe_title = self._sanitize_filename(video.display_title)
            output_path = self.output_dir / f"{safe_title}.mp4"

            # 如果文件已存在，添加数字后缀
            counter = 1
            while output_path.exists():
                output_path = self.output_dir / f"{safe_title}_{counter}.mp4"
                counter += 1

            try:
                result = biliffm4s.combine(str(video.folder_path), str(output_path))
                if result:
                    success_count += 1
            except Exception as e:
                self.error.emit(f"转换失败: {video.display_title}\n错误: {str(e)}")

        self.finished.emit(success_count, total)

    @staticmethod
    def _sanitize_filename(filename: str) -> str:
        """清理文件名中的非法字符"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, "_")
        return filename[:200]  # 限制长度


class AboutDialog(QDialog):
    """关于对话框"""

    def __init__(self, parent=None, icon_path: Path | None = None):
        super().__init__(parent)
        self.setWindowTitle("关于")
        self.setFixedSize(450, 400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)

        # Logo
        if icon_path and icon_path.exists():
            logo_label = QLabel()
            pixmap = QPixmap(str(icon_path))
            scaled_pixmap = pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio,
                                          Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(logo_label)

        # 标题
        title_label = QLabel("Android哔哩哔哩视频导出器 v1.0")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # 信息
        info_text = """
<p><b>作者:</b> WaterRun</p>
<p><b>联合:</b> Claude Opus 4.5, Nano-Banana-Pro</p>
<p><b>架构:</b> Python, PyQT, Pyinstaller</p>
<p><b>GitHub:</b> <a href="https://github.com/Water-Run/biliandout">项目主页</a> | 
<a href="https://github.com/Water-Run/biliandout/releases">Release</a></p>

<hr>
<p><b>额外参考:</b></p>
<p>• <a href="https://github.com/Water-Run/-m4s-Python-biliffm4s">biliffm4s</a></p>
<p>• <a href="https://github.com/FFmpeg/FFmpeg">ffmpeg</a></p>
<p>• <a href="https://pyinstaller.org/">pyinstaller</a></p>
<p>• <a href="https://www.python.org/">python</a></p>
"""

        info_browser = QTextBrowser()
        info_browser.setHtml(info_text)
        info_browser.setOpenExternalLinks(True)
        info_browser.setStyleSheet("""
            QTextBrowser {
                background-color: transparent;
                border: none;
            }
        """)
        layout.addWidget(info_browser)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        close_btn.setFixedWidth(100)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()

        self.videos: list[CachedVideo] = []
        self.output_dir: Path = Path.home() / "Desktop"
        self.convert_thread: QThread | None = None
        self.convert_worker: ConvertWorker | None = None

        # 获取图标路径
        if getattr(sys, 'frozen', False):
            # 打包后的路径
            base_path = Path(sys._MEIPASS)
        else:
            # 开发环境路径
            base_path = Path(__file__).parent

        self.icon_path = base_path / "logo.png"

        self._setup_ui()
        self._connect_signals()

        # 初始扫描设备
        self._refresh_devices()

    def _setup_ui(self):
        """设置UI"""
        self.setWindowTitle("Android哔哩哔哩视频导出器")
        self.setMinimumSize(800, 600)

        # 设置图标
        if self.icon_path.exists():
            self.setWindowIcon(QIcon(str(self.icon_path)))

        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # 设备选择区域
        device_group = QGroupBox("设备与源")
        device_layout = QHBoxLayout(device_group)

        device_layout.addWidget(QLabel("设备:"))
        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(150)
        device_layout.addWidget(self.device_combo)

        device_layout.addWidget(QLabel("源:"))
        self.source_combo = QComboBox()
        for source in BiliSource:
            self.source_combo.addItem(source.display_name, source)
        device_layout.addWidget(self.source_combo)

        self.refresh_btn = QPushButton("刷新设备")
        device_layout.addWidget(self.refresh_btn)

        self.scan_btn = QPushButton("扫描视频")
        device_layout.addWidget(self.scan_btn)

        device_layout.addStretch()

        self.about_btn = QPushButton("关于")
        device_layout.addWidget(self.about_btn)

        main_layout.addWidget(device_group)

        # 视频列表
        list_group = QGroupBox("缓存视频列表")
        list_layout = QVBoxLayout(list_group)

        self.video_table = QTableWidget()
        self.video_table.setColumnCount(4)
        self.video_table.setHorizontalHeaderLabels(["选择", "标题", "大小 (MB)", "路径"])
        self.video_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.video_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.video_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        list_layout.addWidget(self.video_table)

        # 全选/取消全选
        select_layout = QHBoxLayout()
        self.select_all_btn = QPushButton("全选")
        self.deselect_all_btn = QPushButton("取消全选")
        select_layout.addWidget(self.select_all_btn)
        select_layout.addWidget(self.deselect_all_btn)
        select_layout.addStretch()

        self.video_count_label = QLabel("共 0 个视频")
        select_layout.addWidget(self.video_count_label)

        list_layout.addLayout(select_layout)
        main_layout.addWidget(list_group)

        # 输出设置
        output_group = QGroupBox("输出设置")
        output_layout = QHBoxLayout(output_group)

        output_layout.addWidget(QLabel("输出目录:"))
        self.output_path_label = QLabel(str(self.output_dir))
        self.output_path_label.setStyleSheet("color: #0066cc;")
        output_layout.addWidget(self.output_path_label, 1)

        self.browse_btn = QPushButton("浏览...")
        output_layout.addWidget(self.browse_btn)

        main_layout.addWidget(output_group)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # 操作按钮
        action_layout = QHBoxLayout()
        action_layout.addStretch()

        self.convert_btn = QPushButton("导出选中视频")
        self.convert_btn.setMinimumWidth(150)
        self.convert_btn.setStyleSheet("""
            QPushButton {
                background-color: #fb7299;
                color: white;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #fc8bab;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        action_layout.addWidget(self.convert_btn)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setVisible(False)
        action_layout.addWidget(self.cancel_btn)

        main_layout.addLayout(action_layout)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

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

    def _refresh_devices(self):
        """刷新设备列表"""
        self.device_combo.clear()
        devices = DeviceScanner.get_connected_devices()

        if not devices:
            self.device_combo.addItem("未检测到设备", None)
            self.status_bar.showMessage("未检测到已连接的Android设备")
        else:
            for drive_letter, device_name in devices:
                self.device_combo.addItem(device_name, drive_letter)
            self.status_bar.showMessage(f"检测到 {len(devices)} 个设备")

    def _scan_videos(self):
        """扫描缓存视频"""
        drive_letter = self.device_combo.currentData()
        if not drive_letter:
            QMessageBox.warning(self, "警告", "请先连接Android设备")
            return

        source = self.source_combo.currentData()

        self.status_bar.showMessage("正在扫描...")
        QApplication.processEvents()

        self.videos = DeviceScanner.scan_cached_videos(drive_letter, source)
        self._update_video_table()

        self.status_bar.showMessage(f"扫描完成，找到 {len(self.videos)} 个缓存视频")

    def _update_video_table(self):
        """更新视频表格"""
        self.video_table.setRowCount(len(self.videos))

        for row, video in enumerate(self.videos):
            # 复选框
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self.video_table.setCellWidget(row, 0, checkbox_widget)

            # 标题
            title_item = QTableWidgetItem(video.display_title)
            title_item.setFlags(title_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.video_table.setItem(row, 1, title_item)

            # 大小
            size_item = QTableWidgetItem(f"{video.size_mb:.2f}")
            size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.video_table.setItem(row, 2, size_item)

            # 路径
            path_item = QTableWidgetItem(str(video.folder_path))
            path_item.setFlags(path_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.video_table.setItem(row, 3, path_item)

        self.video_count_label.setText(f"共 {len(self.videos)} 个视频")

    def _get_selected_videos(self) -> list[CachedVideo]:
        """获取选中的视频"""
        selected = []
        for row in range(self.video_table.rowCount()):
            checkbox_widget = self.video_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    selected.append(self.videos[row])
        return selected

    def _select_all(self):
        """全选"""
        for row in range(self.video_table.rowCount()):
            checkbox_widget = self.video_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(True)

    def _deselect_all(self):
        """取消全选"""
        for row in range(self.video_table.rowCount()):
            checkbox_widget = self.video_table.cellWidget(row, 0)
            if checkbox_widget:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(False)

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
            QMessageBox.warning(self, "警告", "请至少选择一个视频")
            return

        if not self.output_dir.exists():
            QMessageBox.warning(self, "警告", "输出目录不存在")
            return

        # 禁用UI
        self._set_ui_enabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(len(selected_videos))
        self.progress_bar.setValue(0)
        self.cancel_btn.setVisible(True)

        # 创建工作线程
        self.convert_thread = QThread()
        self.convert_worker = ConvertWorker(selected_videos, self.output_dir)
        self.convert_worker.moveToThread(self.convert_thread)

        # 连接信号
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
        self.status_bar.showMessage(message)

    def _on_convert_finished(self, success_count: int, total_count: int):
        """转换完成回调"""
        self._cleanup_convert_thread()
        self._set_ui_enabled(True)
        self.progress_bar.setVisible(False)
        self.cancel_btn.setVisible(False)

        QMessageBox.information(
            self, "完成",
            f"转换完成!\n成功: {success_count}/{total_count}"
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
        self.video_table.setEnabled(enabled)

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


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()