"""Legacy 层 — 旧 Flask 代码包装, Phase 4 后删除"""

from .flask_app import get_flask_app, create_legacy_flask_app
from .models import HistoryRecordV6

__all__ = [
    "get_flask_app",
    "create_legacy_flask_app",
    "HistoryRecordV6",
]
