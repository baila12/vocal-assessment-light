"""
内存音高缓存 — v7.13 参考音高

进程内 F0 曲线缓存 (单例, 常驻内存)。歌曲删除时需 invalidate。
"""

from __future__ import annotations

from backend.domain.songs_pitch.value_objects import SongPitchCurve


class InMemoryPitchCacheRepository:
    """F0 曲线内存缓存 — 字典实现"""

    def __init__(self) -> None:
        self._cache: dict[str, SongPitchCurve] = {}

    def get(self, song_id: str) -> SongPitchCurve | None:
        return self._cache.get(song_id)

    def set(self, song_id: str, curve: SongPitchCurve) -> None:
        self._cache[song_id] = curve

    def invalidate(self, song_id: str) -> None:
        self._cache.pop(song_id, None)
