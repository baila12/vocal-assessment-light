"""Legacy 层 — v7.6 Flask 绞杀者已完成, Flask 路由已移除。

仅保留 models.py (HistoryRecordV6) 供历史数据迁移使用。
"""
from .models import HistoryRecordV6

__all__ = [
    "HistoryRecordV6",
]
