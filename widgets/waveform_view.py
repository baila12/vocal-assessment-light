"""
波形显示组件 - 使用pyqtgraph显示音频波形
优化：增强视觉效果、改进样式
"""
import numpy as np
import librosa
import logging
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Signal, Qt
import pyqtgraph as pg

logger = logging.getLogger(__name__)


class WaveformView(QWidget):
    """波形显示组件 - 优化版"""

    load_finished = Signal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._audio_data = None
        self._sample_rate = None
        self._duration_ms = 0

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 标题标签
        title = QLabel("波形图")
        title.setStyleSheet("color: #2C3E50; font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.25)

        # 增大标签字体
        label_style = {'font-size': '14px', 'color': '#2C3E50'}
        self.plot_widget.setLabel('left', '振幅', **label_style)
        self.plot_widget.setLabel('bottom', '时间', units='s', **label_style)

        self.plot_widget.setMouseEnabled(x=True, y=False)

        # 增强波形曲线样式
        self.waveform_curve = self.plot_widget.plot(
            pen=pg.mkPen('#5DADE2', width=2.5)
        )

        # 改进播放头样式
        self.playhead_line = pg.InfiniteLine(
            pos=0,
            angle=90,
            pen=pg.mkPen('#E74C3C', width=3, style=Qt.SolidLine)
        )
        self.plot_widget.addItem(self.playhead_line)

        layout.addWidget(self.plot_widget)

    def load_audio(self, filepath: str):
        """
        同步加载音频 - 警告：此方法会阻塞UI线程
        建议使用 set_audio_data() 在异步加载后设置数据
        """
        try:
            self._audio_data, self._sample_rate = librosa.load(filepath, sr=None, mono=True)
            self._update_display()
            self.load_finished.emit(True, "加载成功")
            return True
        except Exception as e:
            logger.error(f"加载波形失败: {e}")
            self.load_finished.emit(False, str(e))
            return False

    def set_audio_data(self, audio_data: np.ndarray, sample_rate: int):
        """
        从已加载的数据设置波形显示 - 推荐方法，不会阻塞UI
        配合工作线程使用：在线程中加载音频后调用此方法更新显示
        """
        self._audio_data = audio_data
        self._sample_rate = sample_rate
        self._update_display()

    def _format_time(self, seconds: float) -> str:
        """将秒数格式化为 M:SS 格式

        Args:
            seconds: 时间（秒）

        Returns:
            格式化的时间字符串，如 "0:30", "1:45"
        """
        total_seconds = int(seconds)
        minutes = total_seconds // 60
        secs = total_seconds % 60
        return f"{minutes}:{secs:02d}"

    def _calculate_tick_interval(self, duration: float) -> float:
        """根据音频时长计算合适的刻度间隔

        Args:
            duration: 音频时长（秒）

        Returns:
            合适的刻度间隔（秒）
        """
        # 目标：显示5-8个刻度
        target_ticks = 6
        raw_interval = duration / target_ticks

        # 标准化到合适的间隔
        standard_intervals = [1, 2, 5, 10, 15, 30, 60, 120, 300, 600]
        for interval in standard_intervals:
            if interval >= raw_interval:
                return float(interval)
        return float(standard_intervals[-1])

    def _update_time_axis(self, duration: float):
        """更新X轴时间刻度标签

        Args:
            duration: 音频时长（秒）
        """
        if duration <= 0:
            return

        interval = self._calculate_tick_interval(duration)
        ticks = []
        t = 0.0
        while t <= duration:
            ticks.append((t, self._format_time(t)))
            t += interval

        # 确保最后一个刻度是音频结束时间
        if ticks and ticks[-1][0] < duration - 0.1:
            ticks.append((duration, self._format_time(duration)))

        ax = self.plot_widget.getAxis('bottom')
        ax.setTicks([ticks])

    def _update_display(self):
        """更新显示（内部方法）- 添加降采样优化"""
        if self._audio_data is None or self._sample_rate is None:
            return
        self._duration_ms = len(self._audio_data) / self._sample_rate * 1000

        # 降采样以优化性能 - 最大显示点数
        max_points = 10000
        if len(self._audio_data) > max_points:
            factor = max(1, len(self._audio_data) // max_points)  # 确保factor >= 1
            # 使用块采样保持波形特征
            audio_downsampled = self._audio_data[::factor]
            times = np.linspace(0, len(self._audio_data) / self._sample_rate, len(audio_downsampled))
        else:
            times = np.linspace(0, len(self._audio_data) / self._sample_rate, len(self._audio_data))
            audio_downsampled = self._audio_data

        self.waveform_curve.setData(times, audio_downsampled)
        duration_sec = self._duration_ms / 1000
        self.plot_widget.setXRange(0, duration_sec)
        self.playhead_line.setValue(0)

        # 更新时间轴刻度
        self._update_time_axis(duration_sec)

    def set_playhead(self, position_ms: int):
        position_sec = position_ms / 1000.0
        self.playhead_line.setValue(position_sec)

    def clear(self):
        self.waveform_curve.setData([])
        self.playhead_line.setValue(0)
        self._audio_data = None
        self._sample_rate = None
        self._duration_ms = 0

    def get_duration_ms(self) -> int:
        return int(self._duration_ms)