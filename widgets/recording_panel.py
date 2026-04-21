"""
录音面板 - 实时录音功能
功能: 实时波形、音量dB、时长显示
"""
import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame
from PySide6.QtCore import Qt, Signal
import pyqtgraph as pg


class RecordingPanel(QWidget):
    """录音面板组件"""
    recording_completed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("recordingPanel")
        self._is_recording = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        title_label = QLabel("实时录音")
        title_label.setObjectName("titleLabel")
        layout.addWidget(title_label)

        waveform_frame = QFrame()
        waveform_frame.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E9ECEF; border-radius: 6px;")
        waveform_layout = QVBoxLayout(waveform_frame)
        waveform_layout.setContentsMargins(8, 8, 8, 8)

        self.waveform_plot = pg.PlotWidget()
        self.waveform_plot.setBackground('w')
        self.waveform_plot.showGrid(x=False, y=True, alpha=0.3)
        self.waveform_plot.setYRange(-1, 1)
        self.waveform_plot.setMouseEnabled(x=False, y=False)
        self.waveform_curve = self.waveform_plot.plot(pen=pg.mkPen('#E74C3C', width=2))
        waveform_layout.addWidget(self.waveform_plot)
        layout.addWidget(waveform_frame)

        info_row = QHBoxLayout()
        info_row.setSpacing(20)

        volume_frame = QFrame()
        volume_frame.setStyleSheet("background-color: #F8F9FA; border-radius: 4px; padding: 8px;")
        volume_layout = QVBoxLayout(volume_frame)
        volume_layout.setSpacing(4)
        volume_title = QLabel("音量")
        volume_title.setStyleSheet("color: #6C757D; font-size: 11px;")
        volume_layout.addWidget(volume_title)
        self.volume_label = QLabel("-80 dB")
        self.volume_label.setStyleSheet("color: #E74C3C; font-size: 18px; font-weight: bold;")
        volume_layout.addWidget(self.volume_label)
        info_row.addWidget(volume_frame)

        time_frame = QFrame()
        time_frame.setStyleSheet("background-color: #F8F9FA; border-radius: 4px; padding: 8px;")
        time_layout = QVBoxLayout(time_frame)
        time_layout.setSpacing(4)
        time_title = QLabel("时长")
        time_title.setStyleSheet("color: #6C757D; font-size: 11px;")
        time_layout.addWidget(time_title)
        self.time_label = QLabel("00:00")
        self.time_label.setStyleSheet("color: #3498DB; font-size: 18px; font-weight: bold; font-family: monospace;")
        time_layout.addWidget(self.time_label)
        info_row.addWidget(time_frame)
        info_row.addStretch()
        layout.addLayout(info_row)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.record_btn = QPushButton("开始录音")
        self.record_btn.setObjectName("recordBtn")
        self.record_btn.setFixedSize(120, 40)
        btn_row.addWidget(self.record_btn)
        self.stop_btn = QPushButton("停止录音")
        self.stop_btn.setStyleSheet("QPushButton { background-color: #F5B041; color: white; border: none; border-radius: 20px; padding: 10px 20px; font-weight: bold; } QPushButton:hover { background-color: #E5A030; }")
        self.stop_btn.setFixedSize(120, 40)
        self.stop_btn.setEnabled(False)
        btn_row.addWidget(self.stop_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.status_label = QLabel("点击「开始录音」开始录制")
        self.status_label.setStyleSheet("color: #6C757D; font-size: 12px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        layout.addStretch()

    def update_volume(self, db: float):
        self.volume_label.setText(f"{db:.1f} dB")
        color = "#E74C3C" if db > -10 else "#27AE60" if db > -30 else "#F39C12"
        self.volume_label.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")

    def update_waveform(self, waveform: np.ndarray):
        self.waveform_curve.setData(waveform)

    def update_time(self, seconds: float):
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        self.time_label.setText(f"{minutes:02d}:{secs:02d}")

    def set_recording_state(self, is_recording: bool):
        self._is_recording = is_recording
        self.record_btn.setEnabled(not is_recording)
        self.stop_btn.setEnabled(is_recording)
        if is_recording:
            self.status_label.setText("正在录音...")
            self.status_label.setStyleSheet("color: #E74C3C; font-size: 12px; font-weight: bold;")
        else:
            self.status_label.setText("点击「开始录音」开始录制")
            self.status_label.setStyleSheet("color: #6C757D; font-size: 12px;")

    def is_recording(self) -> bool:
        return self._is_recording

    def reset(self):
        self._is_recording = False
        self.record_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.volume_label.setText("-80 dB")
        self.volume_label.setStyleSheet("color: #E74C3C; font-size: 18px; font-weight: bold;")
        self.time_label.setText("00:00")
        self.waveform_curve.setData([])
        self.status_label.setText("点击「开始录音」开始录制")
        self.status_label.setStyleSheet("color: #6C757D; font-size: 12px;")