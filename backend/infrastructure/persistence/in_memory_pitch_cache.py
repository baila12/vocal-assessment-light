"""
内存音高缓存 — v7.13 参考音高

进程内 F0 曲线缓存 (单例, 常驻内存)。歌曲删除时需 invalidate。
v7.14 审查 7.4 M7: 无界 dict → LRU 上限 (默认 50 条), 防长期运行内存增长。
"""

from __future__ import annotations

import threading
from collections import OrderedDict

from backend.domain.songs_pitch.value_objects import SongPitchCurve


class InMemoryPitchCacheRepository:
    """F0 曲线内存缓存 — OrderedDict LRU (get/set 刷新访问序, 超限逐出最旧)"""

    def __init__(self, max_entries: int = 50) -> None:
        self.max_entries = max_entries
        self._cache: OrderedDict[str, SongPitchCurve] = OrderedDict()
        self._lock = threading.Lock()  # 单例跨请求共享, 并发安全

    def get(self, song_id: str) -> SongPitchCurve | None:
        with self._lock:
            curve = self._cache.pop(song_id, None)
            if curve is None:
                return None
            self._cache[song_id] = curve  # 置为最新访问
            return curve

    def set(self, song_id: str, curve: SongPitchCurve) -> None:
        with self._lock:
            self._cache.pop(song_id, None)
            self._cache[song_id] = curve
            while len(self._cache) > self.max_entries:
                self._cache.popitem(last=False)  # 逐出最久未访问

    def invalidate(self, song_id: str) -> None:
        with self._lock:
            self._cache.pop(song_id, None)
