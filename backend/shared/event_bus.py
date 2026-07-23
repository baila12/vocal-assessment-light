"""
EventBus 最小原型 — 观察者模式

ADR-6: Phase 1 即实现 EventBus，避免后续在 API 路由里硬编码调用仓储。
"""

from __future__ import annotations
import logging
from typing import Callable, Type, Any

logger = logging.getLogger(__name__)


class DomainEvent:
    """领域事件基类"""
    pass


class EventBus:
    """轻量级事件总线 — 零外部依赖，单进程内存队列"""

    _handlers: dict[Type[DomainEvent], list[Callable[[DomainEvent], None]]]

    def __init__(self) -> None:
        self._handlers = {}

    def publish(self, event: DomainEvent) -> None:
        """发布事件 — 同步调用所有订阅的处理器。

        每个处理器有独立的错误隔离: 单个处理器崩溃不会阻止其他处理器执行。
        """
        for handler in self._handlers.get(type(event), []):
            try:
                handler(event)
            except Exception:
                logger.exception(
                    "EventBus handler %s failed for event %s",
                    handler.__qualname__ if hasattr(handler, '__qualname__') else handler,
                    type(event).__name__,
                )

    def subscribe(
        self,
        event_type: Type[DomainEvent],
        handler: Callable[[DomainEvent], None],
    ) -> None:
        """订阅事件类型"""
        self._handlers.setdefault(event_type, []).append(handler)

    def unsubscribe(
        self,
        event_type: Type[DomainEvent],
        handler: Callable[[DomainEvent], None],
    ) -> None:
        """取消订阅"""
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def clear(self) -> None:
        """清空所有订阅 (测试用)"""
        self._handlers.clear()
