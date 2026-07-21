"""共享内核 — 全项目可引用的零依赖基础类型"""

from .domain_types import PositiveFloat, ScoreValue, ScoreLevel
from .event_bus import EventBus, DomainEvent
from .result import Result

__all__ = [
    "PositiveFloat",
    "ScoreValue",
    "ScoreLevel",
    "EventBus",
    "DomainEvent",
    "Result",
]
