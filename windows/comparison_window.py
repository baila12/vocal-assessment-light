"""
比对窗口 - 双音频对比分析模式
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QSplitter, QFrame,
    QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt, QThread, Signal
from pathlib import Path

from core.vocal_processor import VocalProcessor
from core.audio_analyzer import AudioAnalyzer
from core.comparison_analyzer import ComparisonAnalyzer
from widgets.audio_info_card import AudioInfoCard
from widgets.waveform_view import WaveformView
from widgets.radar_chart import RadarChart
from widgets.score_panel import ScorePanel
from widgets.comparison_result import ComparisonResultPanel
from widgets.audio_player import AudioPlayer


class LoadAudioWorker(QThread):
    """音频加载工作线程 - 异步加载避免UI阻塞"""
    finished = Signal(dict, str, bool)  # info, filepath, is_standard
    error = Signal(str, bool)  # error, is_standard

    def __init__(self, analyzer, filepath: str, is_standard: bool):
        super().__init__()
        self.analyzer = analyzer
        self.filepath = filepath
        self.is_standard = is_standard

    def run(self):
        try:
            info = self.analyzer.analyze(self.filepath)
            self.finished.emit(info, self.filepath, self.is_standard)
        except Exception as e:
            self.error.emit(str(e), self.is_standard)


class ComparisonWorker(QThread):
    """比对工作线程"""
    finished = Signal(dict, dict, dict)
    error = Signal(str)

    def __init__(self, processor: VocalProcessor, analyzer: ComparisonAnalyzer,
                 standard_path: str, target_path: str):
        super().__init__()
        self.processor = processor
        self.analyzer = analyzer
        self.standard_path = standard_path
        self.target_path = target_path

    def run(self):
        try:
            standard_result = self.processor.process(self.standard_path)
            target_result = self.processor.process(self.target_path)
            comparison = self.analyzer.compare(self.standard_path, self.target_path)
            self.finished.emit(standard_result, target_result, comparison)
        except Exception as e:
            self.error.emit(str(e))


class ComparisonWindow(QMainWindow):
    """比对窗口 - 双音频对比"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("声乐评估系统 - 对比分析")
        self.setMinimumSize(1400, 900)
        self._setup_ui()
        self._init_modules()
        self._connect_signals()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        # 顶部工具栏
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        # 主内容区
        splitter = QSplitter(Qt.Horizontal)
        left_panel = self._create_audio_panel("标准音频", is_standard=True)
        right_panel = self._create_audio_panel("待评判音频", is_standard=False)
        center_panel = self._create_center_panel()
        splitter.addWidget(left_panel)
        splitter.addWidget(center_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 400, 400])
        layout.addWidget(splitter, 1)

    def _create_toolbar(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E9ECEF; border-radius: 8px; padding: 8px;")
        layout = QHBoxLayout(frame)
        layout.setSpacing(12)

        self.compare_btn = QPushButton("开始对比")
        self.compare_btn.setStyleSheet("background-color: #27AE60; color: white; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold;")
        self.compare_btn.setEnabled(False)
        layout.addWidget(self.compare_btn)

        self.status_label = QLabel("请加载标准音频和待评判音频")
        self.status_label.setStyleSheet("color: #6C757D; font-size: 13px;")
        layout.addWidget(self.status_label, 1)

        self.mode_btn = QPushButton("切换到单曲评估")
        self.mode_btn.setStyleSheet("background-color: #F8F9FA; color: #495057; border: 1px solid #DEE2E6; border-radius: 6px; padding: 8px 16px;")
        layout.addWidget(self.mode_btn)

        return frame

    def _create_audio_panel(self, title: str, is_standard: bool) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        # 标题和导入按钮
        header = QFrame()
        header.setStyleSheet("background-color: #FFFFFF; border: 1px solid #E9ECEF; border-radius: 6px; padding: 8px;")
        header_layout = QHBoxLayout(header)
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #2C3E50; font-size: 14px; font-weight: bold;")
        header_layout.addWidget(title_label)
        import_btn = QPushButton("导入")
        import_btn.setStyleSheet("background-color: #3498DB; color: white; border: none; border-radius: 4px; padding: 6px 12px;")
        header_layout.addWidget(import_btn)
        layout.addWidget(header)

        # 音频信息
        info_card = AudioInfoCard()
        layout.addWidget(info_card)

        # 波形
        waveform = WaveformView()
        layout.addWidget(waveform, 1)

        # 评分面板
        score_panel = ScorePanel()
        layout.addWidget(score_panel, 1)

        # 存储引用
        if is_standard:
            self.standard_import_btn = import_btn
            self.standard_info = info_card
            self.standard_waveform = waveform
            self.standard_score = score_panel
        else:
            self.target_import_btn = import_btn
            self.target_info = info_card
            self.target_waveform = waveform
            self.target_score = score_panel

        return panel

    def _create_center_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        # 雷达图对比
        radar_group = QGroupBox("能力对比")
        radar_group.setStyleSheet("QGroupBox { color: #2C3E50; font-weight: bold; font-size: 13px; border: 1px solid #DEE2E6; border-radius: 6px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 8px; }")
        radar_layout = QVBoxLayout(radar_group)
        self.radar = RadarChart()
        radar_layout.addWidget(self.radar)
        layout.addWidget(radar_group, 1)

        # 比对结果
        self.comparison_result = ComparisonResultPanel()
        layout.addWidget(self.comparison_result, 1)

        return panel

    def _init_modules(self):
        self.processor = VocalProcessor()
        self.analyzer = AudioAnalyzer()
        self.comparison_analyzer = ComparisonAnalyzer()
        self.worker = None
        self.load_worker = None  # 新增：加载工作线程
        self.standard_file = None
        self.target_file = None
        self.standard_result = None
        self.target_result = None

    def _connect_signals(self):
        self.standard_import_btn.clicked.connect(lambda: self._on_import(is_standard=True))
        self.target_import_btn.clicked.connect(lambda: self._on_import(is_standard=False))
        self.compare_btn.clicked.connect(self._on_compare)
        self.mode_btn.clicked.connect(self._on_switch_mode)

    def _on_import(self, is_standard: bool):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "选择音频文件", "",
            "音频文件 (*.wav *.mp3 *.flac *.ogg);;所有文件 (*)"
        )
        if filepath:
            self._load_audio(filepath, is_standard)

    def _load_audio(self, filepath: str, is_standard: bool):
        """异步加载音频"""
        self.status_label.setText(f"正在加载音频...")

        # 禁用相关导入按钮
        if is_standard:
            self.standard_import_btn.setEnabled(False)
        else:
            self.target_import_btn.setEnabled(False)

        self.load_worker = LoadAudioWorker(self.analyzer, filepath, is_standard)
        self.load_worker.finished.connect(self._on_load_finished)
        self.load_worker.error.connect(self._on_load_error)
        self.load_worker.start()

    def _on_load_finished(self, info: dict, filepath: str, is_standard: bool):
        """加载完成回调"""
        if is_standard:
            self.standard_file = filepath
            self.standard_info.update_info(info)
            self.standard_waveform.load_audio(filepath)
            self.standard_import_btn.setEnabled(True)
        else:
            self.target_file = filepath
            self.target_info.update_info(info)
            self.target_waveform.load_audio(filepath)
            self.target_import_btn.setEnabled(True)
        self._update_status()

    def _on_load_error(self, error: str, is_standard: bool):
        """加载错误回调"""
        self.status_label.setText(f"加载失败")
        if is_standard:
            self.standard_import_btn.setEnabled(True)
        else:
            self.target_import_btn.setEnabled(True)
        QMessageBox.warning(self, "加载错误", error)

    def _update_status(self):
        has_standard = self.standard_file is not None
        has_target = self.target_file is not None
        if has_standard and has_target:
            self.status_label.setText("已加载两个音频，可以开始对比")
            self.compare_btn.setEnabled(True)
        elif has_standard:
            self.status_label.setText("已加载标准音频，请加载待评判音频")
        elif has_target:
            self.status_label.setText("已加载待评判音频，请加载标准音频")
        else:
            self.status_label.setText("请加载标准音频和待评判音频")

    def _on_compare(self):
        if not self.standard_file or not self.target_file:
            return
        self.status_label.setText("对比分析中...")
        self.compare_btn.setEnabled(False)
        self.worker = ComparisonWorker(
            self.processor, self.comparison_analyzer,
            self.standard_file, self.target_file
        )
        self.worker.finished.connect(self._on_compare_finished)
        self.worker.error.connect(self._on_compare_error)
        self.worker.start()

    def _on_compare_finished(self, standard_result: dict, target_result: dict, comparison: dict):
        self.status_label.setText("对比完成")
        self.compare_btn.setEnabled(True)
        self.standard_result = standard_result
        self.target_result = target_result

        standard_scores = standard_result.get('scores', {})
        target_scores = target_result.get('scores', {})

        self.standard_score.update_scores(standard_scores)
        self.target_score.update_scores(target_scores)
        self.radar.update_scores(target_scores)
        self.comparison_result.update_result(comparison)
        self.comparison_result.set_scores(
            sum(standard_scores.values()) / len(standard_scores) if standard_scores else 0,
            sum(target_scores.values()) / len(target_scores) if target_scores else 0
        )

    def _on_compare_error(self, error: str):
        self.status_label.setText(f"对比失败: {error}")
        self.compare_btn.setEnabled(True)
        QMessageBox.warning(self, "对比错误", error)

    def _on_switch_mode(self):
        from windows.main_window import MainWindow
        self.main_window = MainWindow()
        self.main_window.show()
        self.hide()
