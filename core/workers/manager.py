"""
工作线程管理器

管理音频加载和评估任务的线程池
"""
from PySide6.QtCore import QThreadPool
from typing import Dict, Callable

from .signals import WorkerSignals
from .audio_loader import AudioLoadTask
from .assessment_task import AssessmentTask


class WorkerManager:
    """工作线程管理器 - 单例模式"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._pool = QThreadPool.globalInstance()
            cls._instance._pool.setMaxThreadCount(4)
            cls._instance._current_task = None
        return cls._instance

    def start_load(self, filepath: str, callbacks: Dict[str, Callable]) -> AudioLoadTask:
        """启动加载任务"""
        task = AudioLoadTask(filepath)
        task.signals.started.connect(callbacks.get('started', lambda x: None))
        task.signals.progress.connect(callbacks.get('progress', lambda x, y: None))
        task.signals.finished.connect(callbacks.get('finished', lambda x: None))
        task.signals.error.connect(callbacks.get('error', lambda x: None))
        self._pool.start(task)
        self._current_task = task
        return task

    def start_assessment(self, filepath: str, callbacks: Dict[str, Callable]) -> AssessmentTask:
        """启动评估任务"""
        task = AssessmentTask(filepath)
        task.signals.started.connect(callbacks.get('started', lambda x: None))
        task.signals.progress.connect(callbacks.get('progress', lambda x, y: None))
        task.signals.finished.connect(callbacks.get('finished', lambda x: None))
        task.signals.error.connect(callbacks.get('error', lambda x: None))
        self._pool.start(task)
        self._current_task = task
        return task

    def cancel_current(self):
        """取消当前任务"""
        if self._current_task and hasattr(self._current_task, 'cancel'):
            self._current_task.cancel()