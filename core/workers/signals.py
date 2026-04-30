"""
工作线程信号定义
"""
from PySide6.QtCore import QObject, Signal


class WorkerSignals(QObject):
    """工作线程信号"""
    started = Signal(str)  # 任务开始: 任务名称
    progress = Signal(str, int)  # 进度更新: 步骤名称, 百分比
    finished = Signal(object)  # 完成: 结果数据
    error = Signal(str)  # 错误: 错误信息
