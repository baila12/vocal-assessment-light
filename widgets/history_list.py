"""
历史记录列表 - 显示评估历史
增强：空状态提示、时间戳格式化、分数颜色标识
"""
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget, QHBoxLayout, QLabel, QVBoxLayout
from PySide6.QtCore import Qt, Signal
from datetime import datetime


class HistoryList(QListWidget):
    """历史记录列表控件"""
    item_selected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("QListWidget { background: #FFFFFF; color: #495057; border: 1px solid #E9ECEF; border-radius: 6px; padding: 5px; } QListWidget::item { padding: 0px; border-bottom: 1px solid #E9ECEF; margin-bottom: 2px; } QListWidget::item:selected { background: #E3F2FD; border-radius: 4px; } QListWidget::item:hover { background: #F8F9FA; border-radius: 4px; } QListWidget::item:selected:hover { background: #BBDEFB; }")
        self.setSpacing(2)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._history_data = []
        self._empty_label = None  # 空状态标签
        self.itemClicked.connect(self._on_item_clicked)

    def add_record(self, record: dict):
        self._clear_empty_state()
        self._history_data.append(record)
        item_widget = self._create_item_widget(record)
        list_item = QListWidgetItem()
        list_item.setSizeHint(item_widget.sizeHint())
        list_item.setData(Qt.UserRole, len(self._history_data) - 1)
        self.addItem(list_item)
        self.setItemWidget(list_item, item_widget)

    def _create_item_widget(self, record: dict):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)
        left_layout = QVBoxLayout()
        left_layout.setSpacing(3)
        filename = record.get('filename', '未知文件')
        name_label = QLabel(filename)
        name_label.setStyleSheet("color: #2C3E50; font-size: 12px; font-weight: bold;")
        left_layout.addWidget(name_label)

        # 改进时间戳处理
        time_str = self._format_timestamp(record.get('timestamp'))
        time_label = QLabel(time_str)
        time_label.setStyleSheet("color: #ADB5BD; font-size: 10px;")
        left_layout.addWidget(time_label)
        layout.addLayout(left_layout, 1)

        score = record.get('score', 0)
        score_label = QLabel(f"{score:.0f}")
        color = self._get_score_color(score)
        score_label.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")
        layout.addWidget(score_label)
        return widget

    def _format_timestamp(self, timestamp) -> str:
        """格式化时间戳"""
        if timestamp is None:
            return datetime.now().strftime('%m-%d %H:%M')

        if isinstance(timestamp, str):
            return timestamp

        if isinstance(timestamp, (int, float)):
            # 处理时间戳（秒级或毫秒级）
            if timestamp > 1e10:  # 毫秒级时间戳
                timestamp = timestamp / 1000
            try:
                return datetime.fromtimestamp(timestamp).strftime('%m-%d %H:%M')
            except (ValueError, OSError):
                return datetime.now().strftime('%m-%d %H:%M')

        return str(timestamp)

    def _get_score_color(self, score: float) -> str:
        """根据分数获取颜色"""
        if score >= 90:
            return '#27AE60'  # 优秀-绿色
        elif score >= 80:
            return '#3498DB'  # 良好-蓝色
        elif score >= 70:
            return '#F39C12'  # 中等-橙色
        else:
            return '#E74C3C'  # 需改进-红色

    def _on_item_clicked(self, item):
        index = item.data(Qt.UserRole)
        if 0 <= index < len(self._history_data):
            self.item_selected.emit(self._history_data[index])

    def load_history(self, history_list: list):
        self.clear()
        self._history_data = []

        if not history_list:
            self._show_empty_state()
            return

        for record in history_list:
            self.add_record(record)

    def _show_empty_state(self):
        """显示空状态提示"""
        self._empty_label = QLabel("暂无评估记录")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet("color: #ADB5BD; font-size: 13px; padding: 20px;")
        empty_item = QListWidgetItem()
        empty_item.setFlags(Qt.NoItemFlags)  # 不可选择
        self.addItem(empty_item)
        self.setItemWidget(empty_item, self._empty_label)

    def _clear_empty_state(self):
        """清除空状态"""
        if self._empty_label:
            self._empty_label = None
            self.clear()

    def get_history(self) -> list:
        return self._history_data.copy()

    def clear_history(self):
        self.clear()
        self._history_data = []
        self._show_empty_state()