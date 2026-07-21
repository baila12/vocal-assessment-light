"""
Legacy 数据模型 — ADR-4: 独立表隔离

旧 Flask 使用的 history_v6 表与新 FastAPI 的 history 表互不影响。
Alembic 迁移不会触碰此表，确保绞杀者模式下的数据安全。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class HistoryRecordV6:
    """v6.3 历史记录模型 — 锁定为独立表名 history_v6"""

    __tablename__ = "history_v6"

    id: Optional[int] = None
    filename: str = ""
    filepath: str = ""
    mode: str = "quick"
    total_score: float = 0.0
    pitch_score: float = 0.0
    rhythm_score: float = 0.0
    breath_score: float = 0.0
    technique_score: float = 0.0
    artistry_score: float = 0.0
    level: str = ""
    grade: str = ""
    advice: list[str] = field(default_factory=list)
    created_at: str = ""
    duration: float = 0.0
    is_voice: bool = True
    basic_info: dict = field(default_factory=dict)
