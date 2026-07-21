"""领域层 — 零框架依赖，Phase 1 实现"""

from .assessment.feature_flags import DimensionFlags
from ..shared.event_bus import EventBus, DomainEvent

__all__ = ["DimensionFlags", "EventBus", "DomainEvent"]
