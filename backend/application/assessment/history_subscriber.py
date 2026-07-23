"""
历史记录订阅者 — v7.1 Phase B

EventBus 订阅者: ScoreCalculated 事件 → 自动保存历史记录。

设计原则 (ADR-6):
- 依赖反转: 领域层不依赖仓储，订阅者实现桥接
- 错误隔离: 历史保存失败不影响评分结果返回
- 绞杀者模式: 与旧 _save_history() 共存，逐步替换
"""

from __future__ import annotations
import logging
from pathlib import Path
from typing import Optional

from backend.domain.assessment.events import ScoreCalculated

logger = logging.getLogger(__name__)


class HistoryEventSubscriber:
    """
    EventBus 订阅者 — 评分完成时自动保存历史。

    用法:
        from backend.shared.event_bus import EventBus
        from backend.application.assessment.history_subscriber import HistoryEventSubscriber

        bus = EventBus()
        subscriber = HistoryEventSubscriber(history_repo, upload_dir=str(config.upload_folder))
        subscriber.subscribe_to(bus)
    """

    def __init__(
        self,
        history_repo,
        upload_dir: str = "",
    ) -> None:
        self._repo = history_repo
        self._upload_dir = Path(upload_dir) if upload_dir else None

    def subscribe_to(self, event_bus) -> None:
        """注册到 EventBus"""
        event_bus.subscribe(ScoreCalculated, self._on_score_calculated)
        logger.info("HistoryEventSubscriber: registered on EventBus")

    def _on_score_calculated(self, event: ScoreCalculated) -> None:
        """ScoreCalculated 事件处理器 — 自动保存历史"""
        try:
            record = {
                "total_score": event.total_score,
                "level": event.level,
                "grade": event.grade,
                "scores": event.dimensions.copy(),
                "timbre_adjustment": event.timbre_adjustment,
                "timestamp": self._now_iso(),
            }
            self._repo.save(record)
            logger.debug("History auto-saved: total=%.1f, level=%s", event.total_score, event.level)
        except Exception as e:
            # ADR-6: 错误隔离 — 历史保存失败不传播
            logger.warning("History save failed (non-fatal): %s", e)

    @staticmethod
    def _now_iso() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
