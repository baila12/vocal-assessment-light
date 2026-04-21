"""
雷达图组件 - 紧凑布局五维评分可视化
"""
import numpy as np
import platform
from PySide6.QtWidgets import QSizePolicy
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib


class RadarChart(FigureCanvasQTAgg):
    """五维能力雷达图 - 紧凑版"""

    DIMENSIONS = ['音量', '音准', '节奏', '气息', '情绪']

    COLORS = {
        'fill': '#1890ff',
        'line': '#1890ff',
        'grid': '#f0f0f0',
        'label': '#333',
        'tick': '#999'
    }

    def __init__(self, parent=None, width=3, height=3, dpi=100):
        self._setup_chinese_font()

        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor='white')
        super().__init__(self.fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(200, 200)

        self.fig.subplots_adjust(left=0.18, right=0.82, top=0.82, bottom=0.18)

        self.ax = self.fig.add_subplot(111, polar=True)
        self.ax.set_facecolor('white')

        self.angles = np.linspace(0, 2 * np.pi, len(self.DIMENSIONS), endpoint=False).tolist()
        self.angles += self.angles[:1]

        self.ax.set_xticks(self.angles[:-1])
        self.ax.set_xticklabels(
            self.DIMENSIONS,
            color=self.COLORS['label'],
            fontsize=10,
            fontweight='bold'
        )
        self.ax.set_ylim(0, 100)
        self.ax.set_yticks([20, 40, 60, 80, 100])
        self.ax.set_yticklabels(['20', '40', '60', '80', '100'], color=self.COLORS['tick'], fontsize=8)
        self.ax.grid(color=self.COLORS['grid'], linewidth=0.5, linestyle='--')
        self.ax.spines['polar'].set_color(self.COLORS['grid'])

        self.scores = [0, 0, 0, 0, 0]
        self._draw_radar()

    def _setup_chinese_font(self):
        """配置matplotlib中文字体"""
        if platform.system() == "Windows":
            font_list = ['Microsoft YaHei', 'SimHei', 'SimSun', 'Arial Unicode MS']
        elif platform.system() == "Darwin":
            font_list = ['PingFang SC', 'Heiti SC', 'STHeiti', 'Arial Unicode MS']
        else:
            font_list = ['WenQuanYi Micro Hei', 'Noto Sans CJK SC', 'Source Han Sans CN']

        for font in font_list:
            try:
                matplotlib.rcParams['font.sans-serif'] = [font] + matplotlib.rcParams.get('font.sans-serif', [])
                matplotlib.rcParams['axes.unicode_minus'] = False
                break
            except (KeyError, ValueError, RuntimeError):
                continue

    def _draw_radar(self):
        self.ax.clear()
        self.ax.set_facecolor('white')
        self.ax.set_xticks(self.angles[:-1])
        self.ax.set_xticklabels(
            self.DIMENSIONS,
            color=self.COLORS['label'],
            fontsize=10,
            fontweight='bold'
        )
        self.ax.set_ylim(0, 100)
        self.ax.set_yticks([20, 40, 60, 80, 100])
        self.ax.set_yticklabels(['20', '40', '60', '80', '100'], color=self.COLORS['tick'], fontsize=8)
        self.ax.grid(color=self.COLORS['grid'], linewidth=0.5, linestyle='--')
        self.ax.spines['polar'].set_color(self.COLORS['grid'])

        values = self.scores + [self.scores[0]]
        self.ax.fill(self.angles, values, color=self.COLORS['fill'], alpha=0.3)
        self.ax.plot(self.angles, values, color=self.COLORS['line'], linewidth=2, marker='o', markersize=6)
        self.fig.tight_layout()
        self.draw()

    def update_scores(self, scores):
        if isinstance(scores, dict):
            key_mapping = {'volume': 0, 'pitch': 1, 'rhythm': 2, 'breath': 3, 'emotion': 4}
            new_scores = [0, 0, 0, 0, 0]
            for key, idx in key_mapping.items():
                if key in scores:
                    new_scores[idx] = min(100, max(0, scores[key]))
            self.scores = new_scores
        elif isinstance(scores, (list, tuple)) and len(scores) == 5:
            self.scores = [min(100, max(0, s)) for s in scores]
        self._draw_radar()