"""
加载遮罩组件 - 在耗时操作时显示进度
优化：增强视觉效果、添加动画感、显示更多信息
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QPushButton, QFrame, QHBoxLayout
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPainter, QBrush, QPen


class LoadingOverlay(QWidget):
    """半透明的加载遮罩 - 优化版，显示更多信息"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self._audio_info = {}  # 存储当前音频信息
        self._detail_text = ""  # 存储详细进度信息
        self.hide()
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("""
            LoadingOverlay {
                background-color: rgba(255, 255, 255, 0.95);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)

        # 容器框架
        container = QFrame()
        container.setMinimumWidth(400)
        container.setStyleSheet("""
            QFrame {
                background: white;
                border: 2px solid #E9ECEF;
                border-radius: 16px;
                padding: 20px;
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(12)

        self.title_label = QLabel("处理中...")
        self.title_label.setStyleSheet("""
            QLabel {
                color: #2C3E50;
                font-size: 18px;
                font-weight: bold;
            }
        """)
        self.title_label.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(self.title_label)

        # 音频信息区域
        self.info_frame = QFrame()
        self.info_frame.setStyleSheet("""
            QFrame {
                background: #F8F9FA;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        self.info_layout = QVBoxLayout(self.info_frame)
        self.info_layout.setSpacing(4)

        self.filename_label = QLabel("")
        self.filename_label.setStyleSheet("color: #2C3E50; font-size: 13px; font-weight: bold;")
        self.filename_label.setAlignment(Qt.AlignCenter)
        self.info_layout.addWidget(self.filename_label)

        self.audio_details_label = QLabel("")
        self.audio_details_label.setStyleSheet("color: #6C757D; font-size: 11px;")
        self.audio_details_label.setAlignment(Qt.AlignCenter)
        self.info_layout.addWidget(self.audio_details_label)

        self.info_frame.hide()  # 默认隐藏
        container_layout.addWidget(self.info_frame)

        self.step_label = QLabel("准备中...")
        self.step_label.setStyleSheet("""
            QLabel {
                color: #6C757D;
                font-size: 14px;
            }
        """)
        self.step_label.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(self.step_label)

        # 详细信息区域
        self.detail_label = QLabel("")
        self.detail_label.setStyleSheet("""
            QLabel {
                color: #7F8C8D;
                font-size: 11px;
            }
        """)
        self.detail_label.setAlignment(Qt.AlignCenter)
        self.detail_label.setWordWrap(True)
        self.detail_label.hide()
        container_layout.addWidget(self.detail_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumWidth(320)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background: #E9ECEF;
                border-radius: 8px;
                height: 20px;
                text-align: center;
                color: #2C3E50;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3498DB, stop:1 #2ECC71);
                border-radius: 8px;
            }
        """)
        container_layout.addWidget(self.progress_bar)

        self.cancel_btn = QPushButton("取消操作")
        self.cancel_btn.setMinimumWidth(120)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: #E74C3C;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #C0392B;
            }
            QPushButton:pressed {
                background: #A93226;
            }
        """)
        container_layout.addWidget(self.cancel_btn, alignment=Qt.AlignCenter)

        layout.addWidget(container)

    def show_with_animation(self):
        """显示遮罩"""
        self.show()
        self.progress_bar.setValue(0)
        self.raise_()

    def update_progress(self, step: str, percent: int):
        """更新进度"""
        self.step_label.setText(step)
        self.progress_bar.setValue(percent)

    def set_audio_info(self, filename: str = "", duration: str = "", sample_rate: str = "", format: str = ""):
        """设置音频信息

        Args:
            filename: 文件名
            duration: 时长（格式化后）
            sample_rate: 采样率
            format: 文件格式
        """
        self._audio_info = {
            'filename': filename,
            'duration': duration,
            'sample_rate': sample_rate,
            'format': format
        }

        if filename:
            self.filename_label.setText(filename)
            details = []
            if duration:
                details.append(f"时长: {duration}")
            if sample_rate:
                details.append(f"采样率: {sample_rate}Hz")
            if format:
                details.append(f"格式: {format}")
            self.audio_details_label.setText(" | ".join(details))
            self.info_frame.show()
        else:
            self.info_frame.hide()

    def set_detail(self, detail: str):
        """设置详细进度信息

        Args:
            detail: 详细信息文本
        """
        self._detail_text = detail
        if detail:
            self.detail_label.setText(detail)
            self.detail_label.show()
        else:
            self.detail_label.hide()

    def clear_info(self):
        """清除所有信息"""
        self._audio_info = {}
        self._detail_text = ""
        self.filename_label.setText("")
        self.audio_details_label.setText("")
        self.detail_label.setText("")
        self.info_frame.hide()
        self.detail_label.hide()

    def paintEvent(self, event):
        """绘制半透明背景"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QBrush(QColor(255, 255, 255, 240)))
        super().paintEvent(event)

    def resizeEvent(self, event):
        """确保遮罩覆盖整个父窗口"""
        if self.parent():
            self.setGeometry(self.parent().rect())
        super().resizeEvent(event)