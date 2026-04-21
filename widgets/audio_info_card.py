"""
音频信息卡片 - 紧凑布局
"""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt


class AudioInfoCard(QFrame):
    """音频信息显示卡片 - 紧凑版"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            AudioInfoCard {
                background: #FFFFFF;
                border: 1px solid #d9d9d9;
                border-radius: 6px;
            }
            QLabel#cardTitle {
                color: #333;
                font-size: 12px;
                font-weight: 600;
                border-bottom: 1px solid #f0f0f0;
                padding-bottom: 4px;
            }
            QLabel#label {
                color: #999;
                font-size: 11px;
            }
            QLabel#value {
                color: #333;
                font-size: 11px;
                font-weight: 500;
            }
        """)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(3)
        layout.setContentsMargins(10, 10, 10, 10)

        # 标题
        title = QLabel("音频信息")
        title.setObjectName("cardTitle")
        layout.addWidget(title)

        # 基本信息 - 紧凑列表
        self.filename_label = self._add_row(layout, "文件名", "--")
        self.duration_label = self._add_row(layout, "时长", "--")
        self.sample_rate_label = self._add_row(layout, "采样率", "--")
        self.channels_label = self._add_row(layout, "声道", "--")
        self.format_label = self._add_row(layout, "格式", "--")
        self.size_label = self._add_row(layout, "大小", "--")

        layout.addStretch()

    def _add_row(self, layout: QVBoxLayout, label: str, value: str) -> QLabel:
        """添加一行信息"""
        row = QHBoxLayout()
        row.setSpacing(0)

        label_widget = QLabel(label)
        label_widget.setObjectName("label")
        row.addWidget(label_widget)

        row.addStretch()

        value_widget = QLabel(value)
        value_widget.setObjectName("value")
        value_widget.setAlignment(Qt.AlignRight)
        row.addWidget(value_widget)

        layout.addLayout(row)
        return value_widget

    def update_info(self, info_data: dict):
        """更新信息"""
        basic = info_data.get('basic_info', {})
        tech = info_data.get('technical_params', {})
        vol = info_data.get('volume_info', {})
        pitch = info_data.get('pitch_stats', {})

        self.filename_label.setText(basic.get('filename', '--'))
        self.format_label.setText(basic.get('format', '--'))
        self.duration_label.setText(tech.get('duration_formatted', '--'))
        self.sample_rate_label.setText(f"{tech.get('sample_rate', 0)} Hz")
        self.channels_label.setText(tech.get('channel_name', '--'))

        # 大小信息
        size = basic.get('size_mb', None)
        if size:
            self.size_label.setText(f"{size:.1f} MB")
        else:
            self.size_label.setText('--')

    def clear(self):
        """清空信息"""
        for label in [self.filename_label, self.duration_label, self.sample_rate_label,
                      self.channels_label, self.format_label, self.size_label]:
            label.setText("--")