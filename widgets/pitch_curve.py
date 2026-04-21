"""
音高曲线组件 - 修复版
修复内容：
1. 对数刻度下正确设置Y轴范围（人声范围C2-C6：65Hz-1046Hz）
2. 正确处理NaN值数据
3. 添加数据验证和错误处理
"""
import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
import pyqtgraph as pg


# 人声频率范围（C2 - C6）
VOCAL_FREQ_MIN = 65.0    # C2 ≈ 65.41 Hz
VOCAL_FREQ_MAX = 1046.5  # C6 ≈ 1046.50 Hz
import logging

_logger = logging.getLogger(__name__)


class PitchCurve(QWidget):
    """音高曲线显示组件 - 修复版

    修复要点：
    1. 使用固定的Y轴范围（C2-C6，65Hz-1046Hz）适应人声
    2. 对数刻度下正确处理数据（确保所有值>0）
    3. 添加数据验证防止显示异常
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 标题标签
        title = QLabel("音高曲线")
        title.setStyleSheet("color: #2C3E50; font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('w')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.25)

        # 设置标签字体
        label_style = {'font-size': '14px', 'color': '#2C3E50'}
        self.plot_widget.setLabel('left', '频率', units='Hz', **label_style)
        self.plot_widget.setLabel('bottom', '时间', units='s', **label_style)

        # 仅X轴可缩放，Y轴固定
        self.plot_widget.setMouseEnabled(x=True, y=False)

        # 启用Y轴对数刻度
        self.plot_widget.setLogMode(y=True)

        # 设置固定的Y轴显示范围（C2-C6人声范围）
        self.plot_widget.setYRange(VOCAL_FREQ_MIN, VOCAL_FREQ_MAX, padding=0.05)

        # 配置Y轴刻度标签（音符标记）
        ax = self.plot_widget.getAxis('left')
        tick_values = [
            (65.41, 'C2'), (82.41, 'E2'), (98.00, 'G2'),
            (130.81, 'C3'), (164.81, 'E3'), (196.00, 'G3'),
            (261.63, 'C4'), (329.63, 'E4'), (392.00, 'G4'), (440.00, 'A4'),
            (523.25, 'C5'), (659.25, 'E5'), (783.99, 'G5'),
            (1046.50, 'C6'),
        ]
        ax.setTicks([[(v, lbl) for v, lbl in tick_values]])

        # 音高曲线
        self.pitch_curve = self.plot_widget.plot(
            pen=pg.mkPen('#58D68D', width=3),
            symbol='o',
            symbolSize=6,
            symbolBrush='#58D68D'
        )

        # 播放头
        self.playhead_line = pg.InfiniteLine(
            pos=0,
            angle=90,
            pen=pg.mkPen('#E74C3C', width=3, style=Qt.SolidLine)
        )
        self.plot_widget.addItem(self.playhead_line)

        layout.addWidget(self.plot_widget)

    def set_pitch_data(self, times: np.ndarray, frequencies: np.ndarray):
        """设置音高数据

        Args:
            times: 时间数组（秒）
            frequencies: 频率数组（Hz），NaN表示无声/未检测到音高
        """
        # 数据验证
        if times is None or frequencies is None:
            self.clear()
            return

        if len(times) == 0 or len(frequencies) == 0:
            self.clear()
            return

        if len(times) != len(frequencies):
            _logger.warning(f"数据长度不匹配: times={len(times)}, frequencies={len(frequencies)}")
            return

        # 过滤掉NaN值（无声帧）
        valid_mask = ~np.isnan(frequencies)
        valid_times = times[valid_mask]
        valid_freqs = frequencies[valid_mask]

        # 检查是否有有效数据
        if len(valid_times) == 0:
            _logger.warning("没有有效的音高数据")
            self.clear()
            return

        # 验证频率值>0（对数刻度要求）
        if np.any(valid_freqs <= 0):
            _logger.warning("检测到非正频率值，已过滤")
            positive_mask = valid_freqs > 0
            valid_times = valid_times[positive_mask]
            valid_freqs = valid_freqs[positive_mask]

        if len(valid_times) == 0:
            self.clear()
            return

        # 将频率限制在人声范围内（防止异常值）
        valid_freqs = np.clip(valid_freqs, VOCAL_FREQ_MIN, VOCAL_FREQ_MAX)

        # 设置数据 - 对数刻度下直接传入频率值
        self.pitch_curve.setData(valid_times, valid_freqs)

        # 设置X轴范围（时间）
        time_max = float(np.max(times))
        self.plot_widget.setXRange(0, time_max, padding=0.02)

        # 记录实际数据的范围
        min_freq = float(np.min(valid_freqs))
        max_freq = float(np.max(valid_freqs))
        _logger.info(f"音高范围: {min_freq:.1f}Hz - {max_freq:.1f}Hz (C2-C6: 65-1046Hz)")

    def set_playhead(self, position_ms: int):
        """设置播放头位置

        Args:
            position_ms: 位置（毫秒）
        """
        position_sec = position_ms / 1000.0
        self.playhead_line.setValue(position_sec)

    def clear(self):
        """清空图表"""
        self.pitch_curve.setData([], [])
        self.playhead_line.setValue(0)