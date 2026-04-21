"""
数据层 - 仓储模块
负责与存储介质交互，隔离业务逻辑与数据访问
"""
from .history_repository import HistoryRepository, JsonHistoryRepository

__all__ = ['HistoryRepository', 'JsonHistoryRepository']
