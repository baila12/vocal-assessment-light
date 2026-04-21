"""
评分面板 - 紧凑布局显示五维评分和改进建议
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QFrame
from PySide6.QtCore import Qt


class ScorePanel(QWidget):
    """评分详情面板 - 紧凑版"""

    DIMENSIONS = [
        {'key': 'volume', 'name': '音量', 'color': '#1890ff'},
        {'key': 'pitch', 'name': '音准', 'color': '#52c41a'},
        {'key': 'rhythm', 'name': '节奏', 'color': '#fa8c16'},
        {'key': 'breath', 'name': '气息', 'color': '#722ed1'},
        {'key': 'emotion', 'name': '情绪', 'color': '#f5222d'}
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._scores = {}

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        # 卡片样式
        self.setStyleSheet("""
            ScorePanel {
                background: #fff;
                border: 1px solid #d9d9d9;
                border-radius: 6px;
            }
            QLabel#cardTitle {
                color: #333;
                font-size: 12px;
                font-weight: 600;
            }
        """)

        # 总分显示 - 紧凑版
        total_frame = QFrame()
        total_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 6px;
            }
        """)
        total_layout = QVBoxLayout(total_frame)
        total_layout.setSpacing(2)
        total_layout.setContentsMargins(10, 10, 10, 10)

        total_label = QLabel("综合评分")
        total_label.setStyleSheet("color: rgba(255,255,255,0.8); font-size: 10px;")
        total_label.setAlignment(Qt.AlignCenter)
        total_layout.addWidget(total_label)

        self.total_score_label = QLabel("--")
        self.total_score_label.setStyleSheet("color: #fff; font-size: 24px; font-weight: bold;")
        self.total_score_label.setAlignment(Qt.AlignCenter)
        total_layout.addWidget(self.total_score_label)
        layout.addWidget(total_frame)

        # 各维度分数 - 紧凑列表
        scores_title = QLabel("各项得分")
        scores_title.setObjectName("cardTitle")
        scores_title.setStyleSheet("""
            QLabel {
                color: #333;
                font-size: 12px;
                font-weight: 600;
                border-bottom: 1px solid #f0f0f0;
                padding-bottom: 4px;
                margin-bottom: 4px;
            }
        """)
        layout.addWidget(scores_title)

        self.score_bars = {}
        self.score_labels = {}

        for dim in self.DIMENSIONS:
            row = QHBoxLayout()
            row.setSpacing(6)

            name_label = QLabel(dim['name'])
            name_label.setStyleSheet("color: #333; font-size: 11px;")
            name_label.setFixedWidth(44)
            row.addWidget(name_label)

            bar = QProgressBar()
            bar.setMaximum(100)
            bar.setValue(0)
            bar.setTextVisible(False)
            bar.setFixedHeight(5)
            bar.setStyleSheet(f"""
                QProgressBar {{
                    border: none;
                    background: #f0f0f0;
                    border-radius: 3px;
                }}
                QProgressBar::chunk {{
                    background: {dim['color']};
                    border-radius: 3px;
                }}
            """)
            row.addWidget(bar, 1)
            self.score_bars[dim['key']] = bar

            score_label = QLabel("--")
            score_label.setStyleSheet(f"color: {dim['color']}; font-size: 11px; font-weight: 600;")
            score_label.setFixedWidth(28)
            score_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            row.addWidget(score_label)
            self.score_labels[dim['key']] = score_label

            layout.addLayout(row)

        # 改进建议 - 紧凑版
        advice_frame = QFrame()
        advice_frame.setStyleSheet("""
            QFrame {
                background: #fffbe6;
                border: 1px solid #ffe58f;
                border-radius: 6px;
                margin-top: 8px;
            }
        """)
        advice_layout = QVBoxLayout(advice_frame)
        advice_layout.setSpacing(3)
        advice_layout.setContentsMargins(10, 6, 10, 6)

        advice_title = QLabel("改进建议")
        advice_title.setStyleSheet("color: #d48806; font-size: 11px; font-weight: 600;")
        advice_layout.addWidget(advice_title)

        self.advice_text = QLabel("请先导入音频文件并进行评估")
        self.advice_text.setStyleSheet("color: #666; font-size: 10px; line-height: 1.4;")
        self.advice_text.setWordWrap(True)
        advice_layout.addWidget(self.advice_text)

        layout.addWidget(advice_frame)
        layout.addStretch()

    def update_scores(self, scores: dict):
        self._scores = scores or {}
        for dim in self.DIMENSIONS:
            key = dim['key']
            if key in self._scores:
                target_value = int(self._scores[key])
                self.score_bars[key].setValue(target_value)
                self.score_labels[key].setText(str(target_value))
            else:
                self.score_bars[key].setValue(0)
                self.score_labels[key].setText("--")
        if self._scores:
            avg = sum(self._scores.values()) / len(self._scores)
            self.total_score_label.setText(f"{avg:.1f}")
        else:
            self.total_score_label.setText("--")

    def set_advice(self, advice_text: str):
        self.advice_text.setText(advice_text)

    def clear(self):
        self._scores = {}
        self.total_score_label.setText("--")
        for dim in self.DIMENSIONS:
            key = dim['key']
            self.score_bars[key].setValue(0)
            self.score_labels[key].setText("--")
        self.advice_text.setText("请先导入音频文件并进行评估")