"""
主窗口 - 紧凑布局设计（基于10次HTML迭代）
页面1: 音频导入和基本信息（左侧220px，右侧内容）
页面2: 波形和音高可视化（双栏并排）
页面3: 评估结果（雷达图+评分面板）
"""
import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QStackedWidget,
    QFrame, QMessageBox, QSplitter
)
from PySide6.QtCore import Qt

from core.workers import WorkerManager
from core.recorder import AudioRecorder
from utils.history_manager import HistoryManager
from widgets.audio_info_card import AudioInfoCard
from widgets.waveform_view import WaveformView
from widgets.pitch_curve import PitchCurve
from widgets.radar_chart import RadarChart
from widgets.score_panel import ScorePanel
from widgets.loading_overlay import LoadingOverlay
from widgets.recording_panel import RecordingPanel
from widgets.history_list import HistoryList


# 统一的紧凑样式常量
STYLE = {
    'navbar_height': '44px',
    'nav_tab_padding': '10px 16px',
    'nav_tab_font': '13px',
    'btn_padding': '5px 12px',
    'btn_font': '12px',
    'main_padding': '12px',
    'card_padding': '10px',
    'card_radius': '6px',
    'card_border': '#d9d9d9',
    'title_font': '12px',
    'info_font': '11px',
    'hint_font': '10px',
    'gap': '8px',
    'left_width': '220px',
    'primary_color': '#1890ff',
    'text_color': '#333',
    'border_color': '#e0e0e0',
}


class MainWindow(QMainWindow):
    """主窗口 - 紧凑布局"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("声乐评估系统")
        self.setMinimumSize(1000, 600)
        self.resize(1100, 700)

        self.worker_manager = WorkerManager()
        self.current_file = None
        self.current_audio_data = None
        self.current_sample_rate = None
        self.assessment_result = None

        # 录音器
        self.recorder = AudioRecorder()
        self._recording_panel = None  # 录音面板（延迟创建）

        # 历史记录管理器
        self.history_manager = HistoryManager()

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """设置UI - 紧凑布局"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # 顶部导航栏 - 紧凑版
        self.nav_bar = self._create_nav_bar()
        layout.addWidget(self.nav_bar)

        # 主内容区 - 堆叠页面
        self.stack = QStackedWidget()

        # 页面1: 导入页面 - 紧凑双栏
        self.page_import = self._create_import_page()
        self.stack.addWidget(self.page_import)

        # 页面2: 可视化页面 - 双栏并排
        self.page_visual = self._create_visual_page()
        self.stack.addWidget(self.page_visual)

        # 页面3: 评估页面 - 紧凑版
        self.page_assess = self._create_assess_page()
        self.stack.addWidget(self.page_assess)

        layout.addWidget(self.stack, 1)

        # 加载遮罩
        self.loading = LoadingOverlay(self)
        self.loading.cancel_btn.clicked.connect(self._on_cancel_operation)

        # 状态栏 - 紧凑版
        self.status_bar = QLabel("就绪 - 请导入音频文件开始评估")
        self.status_bar.setFixedHeight(28)
        self.status_bar.setStyleSheet("""
            QLabel {
                background: #FFFFFF;
                color: #888;
                padding: 6px 16px;
                border-top: 1px solid #e0e0e0;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.status_bar)

    def _create_nav_bar(self) -> QFrame:
        """创建导航栏 - 紧凑版"""
        frame = QFrame()
        frame.setFixedHeight(44)
        frame.setStyleSheet("""
            QFrame {
                background: #FFFFFF;
                border-bottom: 1px solid #e0e0e0;
            }
            QPushButton {
                background: transparent;
                color: #666;
                border: none;
                padding: 10px 16px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                color: #1890ff;
                background: #f0f7ff;
            }
            QPushButton#active {
                color: #1890ff;
                border-bottom: 2px solid #1890ff;
            }
            QPushButton#action {
                background: #1890ff;
                color: white;
                border-radius: 3px;
                padding: 5px 12px;
                font-size: 12px;
            }
            QPushButton#action:hover {
                background: #40a9ff;
            }
            QPushButton#action:disabled {
                background: #d9d9d9;
                color: #999;
            }
            QPushButton#import {
                background: #fff;
                color: #333;
                border: 1px solid #d9d9d9;
                border-radius: 3px;
                padding: 5px 12px;
                font-size: 12px;
            }
            QPushButton#import:hover {
                color: #1890ff;
                border-color: #1890ff;
            }
        """)

        layout = QHBoxLayout(frame)
        layout.setSpacing(0)
        layout.setContentsMargins(16, 0, 16, 0)

        # 导航按钮
        self.nav_import_btn = QPushButton("1. 导入音频")
        self.nav_import_btn.setObjectName("active")
        self.nav_import_btn.clicked.connect(lambda: self._switch_page(0))

        self.nav_visual_btn = QPushButton("2. 波形分析")
        self.nav_visual_btn.clicked.connect(lambda: self._switch_page(1))

        self.nav_assess_btn = QPushButton("3. 评估结果")
        self.nav_assess_btn.clicked.connect(lambda: self._switch_page(2))

        layout.addWidget(self.nav_import_btn)
        layout.addWidget(self.nav_visual_btn)
        layout.addWidget(self.nav_assess_btn)
        layout.addStretch()

        # 操作按钮 - 紧凑间距
        self.import_btn = QPushButton("导入音频")
        self.import_btn.setObjectName("import")
        self.import_btn.clicked.connect(self._on_import)

        self.assess_btn = QPushButton("开始评估")
        self.assess_btn.setObjectName("action")
        self.assess_btn.setEnabled(False)
        self.assess_btn.clicked.connect(self._on_assess)

        layout.addWidget(self.import_btn)
        layout.addSpacing(6)

        # 录音按钮
        self.record_btn = QPushButton("录音")
        self.record_btn.setObjectName("import")
        self.record_btn.clicked.connect(self._on_record_toggle)
        layout.addWidget(self.record_btn)
        layout.addSpacing(6)
        layout.addWidget(self.assess_btn)

        return frame

    def _create_import_page(self) -> QWidget:
        """创建导入页面 - 紧凑双栏布局"""
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 4, 12, 4)

        # 左侧 - 音频信息卡片 (220px)
        left_panel = QVBoxLayout()
        left_panel.setSpacing(4)

        self.audio_info = AudioInfoCard()
        self.audio_info.setFixedWidth(220)
        left_panel.addWidget(self.audio_info)

        # 波形预览占位
        preview_frame = QFrame()
        preview_frame.setFixedHeight(50)
        preview_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f0f0f0, stop:0.5 #e8e8e8, stop:1 #f0f0f0);
                border-radius: 4px;
            }
            QLabel {
                color: #999;
                font-size: 10px;
            }
        """)
        preview_layout = QVBoxLayout(preview_frame)
        preview_label = QLabel("音频预览")
        preview_label.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(preview_label)
        left_panel.addWidget(preview_frame)

        left_panel.addStretch()
        layout.addLayout(left_panel)

        # 右侧 - 垂直布局多个卡片
        right_panel = QVBoxLayout()
        right_panel.setSpacing(8)

        # 导入操作区
        import_card = QFrame()
        import_card.setStyleSheet("""
            QFrame {
                background: #fff;
                border: 1px solid #d9d9d9;
                border-radius: 6px;
            }
        """)
        import_layout = QVBoxLayout(import_card)
        import_layout.setContentsMargins(10, 10, 10, 10)
        import_layout.setSpacing(6)

        import_title = QLabel("导入音频")
        import_title.setStyleSheet("color: #333; font-size: 12px; font-weight: 600;")
        import_layout.addWidget(import_title)

        # 拖拽提示区
        drop_zone = QFrame()
        drop_zone.setStyleSheet("""
            QFrame {
                background: #fafafa;
                border: 2px dashed #d9d9d9;
                border-radius: 4px;
            }
        """)
        drop_layout = QVBoxLayout(drop_zone)
        drop_layout.setContentsMargins(16, 16, 16, 16)
        drop_layout.setSpacing(4)

        drop_text = QLabel("点击或拖拽音频文件到此处导入")
        drop_text.setStyleSheet("color: #666; font-size: 12px;")
        drop_text.setAlignment(Qt.AlignCenter)
        drop_layout.addWidget(drop_text)

        drop_hint = QLabel("支持 WAV / MP3 / FLAC / OGG / M4A")
        drop_hint.setStyleSheet("color: #999; font-size: 10px;")
        drop_hint.setAlignment(Qt.AlignCenter)
        drop_layout.addWidget(drop_hint)

        import_layout.addWidget(drop_zone)
        right_panel.addWidget(import_card)

        # 五维评分体系
        dims_card = QFrame()
        dims_card.setStyleSheet("""
            QFrame {
                background: #fff;
                border: 1px solid #d9d9d9;
                border-radius: 6px;
            }
        """)
        dims_layout = QVBoxLayout(dims_card)
        dims_layout.setContentsMargins(10, 10, 10, 10)
        dims_layout.setSpacing(6)

        dims_title = QLabel("五维评分体系")
        dims_title.setStyleSheet("color: #333; font-size: 12px; font-weight: 600;")
        dims_layout.addWidget(dims_title)

        # 五维网格
        dims_grid = QHBoxLayout()
        dims_grid.setSpacing(6)

        dimensions = [
            ("V", "音量", "#1890ff", "#e6f7ff"),
            ("P", "音准", "#52c41a", "#f6ffed"),
            ("R", "节奏", "#fa8c16", "#fff7e6"),
            ("B", "气息", "#722ed1", "#f9f0ff"),
            ("E", "情绪", "#f5222d", "#fff1f0"),
        ]

        for icon, name, color, bg in dimensions:
            dim_item = QFrame()
            dim_item.setStyleSheet(f"""
                QFrame {{
                    background: #fafafa;
                    border-radius: 4px;
                }}
            """)
            dim_layout = QVBoxLayout(dim_item)
            dim_layout.setContentsMargins(4, 6, 4, 6)
            dim_layout.setSpacing(2)

            icon_label = QLabel(icon)
            icon_label.setStyleSheet(f"""
                QLabel {{
                    background: {bg};
                    color: {color};
                    border-radius: 12px;
                    padding: 4px;
                    font-size: 11px;
                    font-weight: 600;
                }}
            """)
            icon_label.setAlignment(Qt.AlignCenter)
            icon_label.setFixedSize(24, 24)
            dim_layout.addWidget(icon_label, alignment=Qt.AlignCenter)

            name_label = QLabel(name)
            name_label.setStyleSheet("color: #333; font-size: 11px; font-weight: 500;")
            name_label.setAlignment(Qt.AlignCenter)
            dim_layout.addWidget(name_label, alignment=Qt.AlignCenter)

            dims_grid.addWidget(dim_item)

        dims_layout.addLayout(dims_grid)
        right_panel.addWidget(dims_card)

        # 使用流程
        tips_card = QFrame()
        tips_card.setStyleSheet("""
            QFrame {
                background: #fff;
                border: 1px solid #d9d9d9;
                border-radius: 6px;
            }
        """)
        tips_layout = QVBoxLayout(tips_card)
        tips_layout.setContentsMargins(10, 10, 10, 10)
        tips_layout.setSpacing(6)

        tips_title = QLabel("使用流程")
        tips_title.setStyleSheet("color: #333; font-size: 12px; font-weight: 600;")
        tips_layout.addWidget(tips_title)

        tips_row = QHBoxLayout()
        tips_row.setSpacing(12)

        steps = [("1", "导入音频"), ("2", "波形分析"), ("3", "获取评分")]
        for num, text in steps:
            step_layout = QHBoxLayout()
            step_layout.setSpacing(4)

            num_label = QLabel(num)
            num_label.setStyleSheet("""
                QLabel {
                    background: #1890ff;
                    color: white;
                    border-radius: 8px;
                    font-size: 10px;
                }
            """)
            num_label.setAlignment(Qt.AlignCenter)
            num_label.setFixedSize(16, 16)
            step_layout.addWidget(num_label)

            text_label = QLabel(text)
            text_label.setStyleSheet("color: #555; font-size: 11px;")
            step_layout.addWidget(text_label)

            tips_row.addLayout(step_layout)
            if num != "3":
                arrow = QLabel("→")
                arrow.setStyleSheet("color: #d9d9d9; font-size: 12px;")
                tips_row.addWidget(arrow)

        tips_layout.addLayout(tips_row)
        right_panel.addWidget(tips_card)

        # 历史记录
        history_card = QFrame()
        history_card.setStyleSheet("""
            QFrame {
                background: #fff;
                border: 1px solid #d9d9d9;
                border-radius: 6px;
            }
        """)
        history_layout = QVBoxLayout(history_card)
        history_layout.setContentsMargins(10, 10, 10, 10)
        history_layout.setSpacing(4)

        history_title = QLabel("最近评估")
        history_title.setStyleSheet("color: #333; font-size: 12px; font-weight: 600;")
        history_layout.addWidget(history_title)

        self.history_list = HistoryList()
        self.history_list.setFixedHeight(120)
        self.history_list.item_selected.connect(self._on_history_selected)
        history_layout.addWidget(self.history_list)

        # 加载历史记录
        self._load_history()

        right_panel.addWidget(history_card)
        right_panel.addStretch()

        layout.addLayout(right_panel)

        return page

    def _create_visual_page(self) -> QWidget:
        """创建可视化页面 - 双栏并排"""
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 4, 12, 4)

        # 左侧 - 波形图
        waveform_card = QFrame()
        waveform_card.setStyleSheet("""
            QFrame {
                background: #fff;
                border: 1px solid #d9d9d9;
                border-radius: 6px;
            }
        """)
        waveform_layout = QVBoxLayout(waveform_card)
        waveform_layout.setContentsMargins(10, 10, 10, 10)
        waveform_layout.setSpacing(6)

        waveform_header = QHBoxLayout()
        waveform_title = QLabel("波形图")
        waveform_title.setStyleSheet("color: #333; font-size: 12px; font-weight: 600;")
        waveform_header.addWidget(waveform_title)
        waveform_header.addStretch()
        waveform_layout.addLayout(waveform_header)

        self.waveform = WaveformView()
        waveform_layout.addWidget(self.waveform)

        layout.addWidget(waveform_card)

        # 右侧 - 音高曲线
        pitch_card = QFrame()
        pitch_card.setStyleSheet("""
            QFrame {
                background: #fff;
                border: 1px solid #d9d9d9;
                border-radius: 6px;
            }
        """)
        pitch_layout = QVBoxLayout(pitch_card)
        pitch_layout.setContentsMargins(10, 10, 10, 10)
        pitch_layout.setSpacing(6)

        pitch_header = QHBoxLayout()
        pitch_title = QLabel("音高曲线")
        pitch_title.setStyleSheet("color: #333; font-size: 12px; font-weight: 600;")
        pitch_header.addWidget(pitch_title)
        pitch_header.addStretch()
        pitch_layout.addLayout(pitch_header)

        self.pitch_curve = PitchCurve()
        pitch_layout.addWidget(self.pitch_curve)

        layout.addWidget(pitch_card)

        return page

    def _create_assess_page(self) -> QWidget:
        """创建评估页面 - 紧凑版"""
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 4, 12, 4)

        # 左侧 - 雷达图
        radar_card = QFrame()
        radar_card.setStyleSheet("""
            QFrame {
                background: #fff;
                border: 1px solid #d9d9d9;
                border-radius: 6px;
            }
        """)
        radar_layout = QVBoxLayout(radar_card)
        radar_layout.setContentsMargins(10, 10, 10, 10)
        radar_layout.setSpacing(6)

        radar_title = QLabel("五维能力分析")
        radar_title.setStyleSheet("color: #333; font-size: 12px; font-weight: 600;")
        radar_layout.addWidget(radar_title)

        self.radar = RadarChart(width=3, height=3)
        radar_layout.addWidget(self.radar, 1)

        layout.addWidget(radar_card)

        # 右侧 - 评分面板
        self.score_panel = ScorePanel()
        layout.addWidget(self.score_panel)

        return page

    def _connect_signals(self):
        """连接信号"""
        # 录音器信号 - 使用QueuedConnection确保线程安全
        self.recorder.volume_updated.connect(self._on_recording_volume, Qt.QueuedConnection)
        self.recorder.time_updated.connect(self._on_recording_time, Qt.QueuedConnection)
        self.recorder.recording_started.connect(self._on_recording_started, Qt.QueuedConnection)
        self.recorder.recording_stopped.connect(self._on_recording_stopped, Qt.QueuedConnection)
        self.recorder.error_occurred.connect(self._on_recording_error, Qt.QueuedConnection)

    def _switch_page(self, index: int):
        """切换页面"""
        self.stack.setCurrentIndex(index)

        # 更新导航按钮样式
        buttons = [self.nav_import_btn, self.nav_visual_btn, self.nav_assess_btn]
        for i, btn in enumerate(buttons):
            if i == index:
                btn.setObjectName("active")
            else:
                btn.setObjectName("")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _on_import(self):
        """导入音频"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "选择音频文件", "",
            "音频文件 (*.wav *.mp3 *.flac *.ogg *.m4a);;所有文件 (*)"
        )

        if not filepath:
            return

        self.current_file = filepath
        self._start_load(filepath)

    def _start_load(self, filepath: str):
        """开始异步加载"""
        self.loading.show_with_animation()
        self.loading.update_progress("准备加载...", 0)
        self.import_btn.setEnabled(False)
        self.assess_btn.setEnabled(False)

        callbacks = {
            'started': self._on_load_started,
            'progress': self._on_load_progress,
            'finished': self._on_load_finished,
            'error': self._on_load_error
        }

        self.worker_manager.start_load(filepath, callbacks)

    def _on_load_started(self, message: str):
        """加载开始"""
        self.status_bar.setText(message)

    def _on_load_progress(self, step: str, percent: int):
        """加载进度"""
        self.loading.update_progress(step, percent)
        self.status_bar.setText(f"{step} ({percent}%)")

    def _on_load_finished(self, result: dict):
        """加载完成"""
        self.loading.hide()
        self.import_btn.setEnabled(True)
        self.assess_btn.setEnabled(True)

        if not result.get('valid'):
            QMessageBox.warning(self, "加载失败", "无法解析音频文件")
            return

        self.current_audio_data = result.get('audio_data')
        self.current_sample_rate = result.get('sample_rate')

        self.audio_info.update_info(result)

        if self.current_audio_data is not None:
            self.waveform.set_audio_data(self.current_audio_data, self.current_sample_rate)

        filename = result.get('basic_info', {}).get('filename', '未知文件')
        self.status_bar.setText(f"加载完成: {filename}")
        self._switch_page(1)

    def _on_load_error(self, error: str):
        """加载错误"""
        self.loading.hide()
        self.import_btn.setEnabled(True)
        self.status_bar.setText(f"加载失败: {error}")
        QMessageBox.warning(self, "加载错误", error)

    def _on_assess(self):
        """开始评估"""
        if not self.current_file:
            return

        self.loading.show_with_animation()
        self.loading.update_progress("准备评估...", 0)
        self.assess_btn.setEnabled(False)

        callbacks = {
            'started': self._on_assess_started,
            'progress': self._on_assess_progress,
            'finished': self._on_assess_finished,
            'error': self._on_assess_error
        }

        self.worker_manager.start_assessment(self.current_file, callbacks)

    def _on_assess_started(self, message: str):
        """评估开始"""
        self.status_bar.setText(message)

    def _on_assess_progress(self, step: str, percent: int):
        """评估进度"""
        self.loading.update_progress(step, percent)
        self.status_bar.setText(f"{step} ({percent}%)")

    def _on_assess_finished(self, result: dict):
        """评估完成"""
        self.loading.hide()
        self.assess_btn.setEnabled(True)
        self.assessment_result = result

        scores = result.get('scores', {})
        self.radar.update_scores(scores)
        self.score_panel.update_scores(scores)
        self.score_panel.set_advice(result.get('advice', ''))

        if result.get('pitch'):
            self.pitch_curve.set_pitch_data(
                result['pitch']['times'],
                result['pitch']['frequencies']
            )

        # 保存到历史记录
        self._save_to_history(result)

        self.status_bar.setText("评估完成")
        self._switch_page(2)

    def _on_assess_error(self, error: str):
        """评估错误"""
        self.loading.hide()
        self.assess_btn.setEnabled(True)
        self.status_bar.setText(f"评估失败: {error}")
        QMessageBox.warning(self, "评估错误", error)

    def _on_cancel_operation(self):
        """取消操作"""
        self.worker_manager.cancel_current()
        self.loading.hide()
        self.import_btn.setEnabled(True)
        self.assess_btn.setEnabled(True)
        self.status_bar.setText("已取消")

    def resizeEvent(self, event):
        """窗口大小变化时更新遮罩"""
        super().resizeEvent(event)
        if self.loading:
            self.loading.setGeometry(self.rect())

    def _on_record_toggle(self):
        """切换录音状态"""
        if self.recorder.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        """开始录音"""
        if not self.recorder.is_ready():
            error = self.recorder.get_error()
            QMessageBox.warning(self, "录音错误", error)
            return

        self.recorder.start_recording()
        self.record_btn.setText("停止录音")
        self.record_btn.setStyleSheet("QPushButton { background-color: #E74C3C; color: white; border: none; border-radius: 3px; padding: 5px 12px; font-size: 12px; }")
        self.status_bar.setText("正在录音...")

    def _stop_recording(self):
        """停止录音"""
        filepath = self.recorder.stop_recording()
        self.record_btn.setText("录音")
        self.record_btn.setStyleSheet("")
        self.record_btn.setObjectName("import")
        self.record_btn.style().unpolish(self.record_btn)
        self.record_btn.style().polish(self.record_btn)

        if filepath:
            self.status_bar.setText(f"录音已保存: {filepath}")
            # 自动加载录音文件
            self.current_file = filepath
            self._start_load(filepath)

    def _on_recording_volume(self, db: float):
        """录音音量更新"""
        pass  # 可扩展：显示音量指示器

    def _on_recording_time(self, seconds: float):
        """录音时间更新"""
        self.status_bar.setText(f"正在录音... {seconds:.1f}秒")

    def _on_recording_started(self):
        """录音开始"""
        self.import_btn.setEnabled(False)
        self.assess_btn.setEnabled(False)

    def _on_recording_stopped(self, filepath: str):
        """录音停止"""
        self.import_btn.setEnabled(True)
        self.assess_btn.setEnabled(True)
        self.status_bar.setText(f"录音已保存: {filepath}")

    def _on_recording_error(self, error: str):
        """录音错误"""
        self.record_btn.setText("录音")
        self.record_btn.setStyleSheet("")
        self.record_btn.setObjectName("import")
        self.record_btn.style().unpolish(self.record_btn)
        self.record_btn.style().polish(self.record_btn)
        self.import_btn.setEnabled(True)
        self.assess_btn.setEnabled(True)
        self.status_bar.setText(f"录音错误: {error}")
        QMessageBox.warning(self, "录音错误", error)

    def _load_history(self):
        """加载历史记录"""
        records = self.history_manager.get_all(limit=10)
        self.history_list.load_history(records)

    def _save_to_history(self, result: dict):
        """保存评估结果到历史记录"""
        filename = os.path.basename(self.current_file) if self.current_file else "未知文件"
        scores = result.get('scores', {})
        total_score = sum(scores.values()) / len(scores) if scores else 0

        record = {
            'filename': filename,
            'filepath': self.current_file,
            'score': total_score,
            'scores': scores,
            'advice': result.get('advice', '')
        }
        self.history_manager.add_record(record)
        self._load_history()  # 刷新列表

    def _on_history_selected(self, record: dict):
        """选择历史记录"""
        filepath = record.get('filepath')
        if filepath and os.path.exists(filepath):
            self.current_file = filepath
            self._start_load(filepath)
        else:
            QMessageBox.warning(self, "文件不存在", "该音频文件已被移动或删除")