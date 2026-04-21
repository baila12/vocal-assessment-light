"""
比对结果面板 - 显示标准音频与待评判音频的对比分析
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QFrame, QGroupBox
from PySide6.QtCore import Qt


class ComparisonResultPanel(QWidget):
    """比对结果显示面板"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        title_label = QLabel("对比分析结果")
        title_label.setStyleSheet("color: #1976D2; font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        # 评分差距显示
        score_frame = QFrame()
        score_frame.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E9ECEF; border-radius: 6px; padding: 12px;")
        score_layout = QHBoxLayout(score_frame)
        self.standard_score_label = QLabel("标准: --")
        self.standard_score_label.setStyleSheet("color: #3498DB; font-size: 16px; font-weight: bold;")
        score_layout.addWidget(self.standard_score_label)
        self.target_score_label = QLabel("待评判: --")
        self.target_score_label.setStyleSheet("color: #E74C3C; font-size: 16px; font-weight: bold;")
        score_layout.addWidget(self.target_score_label)
        self.diff_label = QLabel("差距: --")
        self.diff_label.setStyleSheet("color: #F39C12; font-size: 16px; font-weight: bold;")
        score_layout.addWidget(self.diff_label)
        score_layout.addStretch()
        layout.addWidget(score_frame)

        # 对比维度分析
        diff_group = QGroupBox("差异分析")
        diff_group.setStyleSheet("QGroupBox { color: #2C3E50; font-weight: bold; font-size: 13px; border: 1px solid #DEE2E6; border-radius: 6px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 8px; }")
        diff_layout = QVBoxLayout(diff_group)
        self.pitch_diff_label = QLabel("音准差异: --")
        self.pitch_diff_label.setStyleSheet("color: #58D68D; font-size: 12px;")
        diff_layout.addWidget(self.pitch_diff_label)
        self.rhythm_diff_label = QLabel("节奏差异: --")
        self.rhythm_diff_label.setStyleSheet("color: #F5B041; font-size: 12px;")
        diff_layout.addWidget(self.rhythm_diff_label)
        self.volume_diff_label = QLabel("音量差异: --")
        self.volume_diff_label.setStyleSheet("color: #5DADE2; font-size: 12px;")
        diff_layout.addWidget(self.volume_diff_label)
        layout.addWidget(diff_group)

        # 改进建议
        suggestion_group = QGroupBox("改进建议")
        suggestion_group.setStyleSheet("QGroupBox { color: #2C3E50; font-weight: bold; font-size: 13px; border: 1px solid #DEE2E6; border-radius: 6px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 8px; }")
        suggestion_layout = QVBoxLayout(suggestion_group)
        self.suggestion_text = QTextEdit()
        self.suggestion_text.setReadOnly(True)
        self.suggestion_text.setStyleSheet("background-color: #F8F9FA; color: #495057; border: none; font-size: 13px; padding: 8px;")
        self.suggestion_text.setPlaceholderText("暂无对比建议...")
        self.suggestion_text.setMinimumHeight(150)
        suggestion_layout.addWidget(self.suggestion_text)
        layout.addWidget(suggestion_group)
        layout.addStretch()

    def update_result(self, result: dict):
        pitch_diff = result.get('pitch_diff', {})
        rhythm_diff = result.get('rhythm_diff', {})
        volume_diff = result.get('volume_diff', {})
        suggestions = result.get('suggestions', [])
        overall_diff = result.get('overall_diff', 0)
        self.diff_label.setText(f"差距: {overall_diff:.1f}")
        avg_pitch_diff = pitch_diff.get('avg_diff', 0)
        self.pitch_diff_label.setText(f"音准差异: 平均偏差 {avg_pitch_diff:.1f}Hz")
        bpm_diff = rhythm_diff.get('bpm_diff', 0)
        direction = rhythm_diff.get('direction', '基本一致')
        self.rhythm_diff_label.setText(f"节奏差异: BPM相差 {bpm_diff:.1f}，{direction}")
        db_diff = volume_diff.get('db_diff', 0)
        vol_direction = volume_diff.get('direction', '基本一致')
        self.volume_diff_label.setText(f"音量差异: 相差 {abs(db_diff):.1f}dB，{vol_direction}")
        if suggestions:
            self.suggestion_text.setText("\n".join([f"• {s}" for s in suggestions]))
        else:
            self.suggestion_text.setText("暂无改进建议")

    def set_scores(self, standard_score: float, target_score: float):
        self.standard_score_label.setText(f"标准: {standard_score:.1f}")
        self.target_score_label.setText(f"待评判: {target_score:.1f}")
        diff = target_score - standard_score
        self.diff_label.setText(f"差距: {diff:.1f}")

    def clear(self):
        self.standard_score_label.setText("标准: --")
        self.target_score_label.setText("待评判: --")
        self.diff_label.setText("差距: --")
        self.pitch_diff_label.setText("音准差异: --")
        self.rhythm_diff_label.setText("节奏差异: --")
        self.volume_diff_label.setText("音量差异: --")
        self.suggestion_text.clear()