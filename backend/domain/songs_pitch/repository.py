"""
歌曲音高缓存仓储协议 — v7.13

F0 曲线缓存的抽象接口, 内存/文件/Redis 实现可切换。
"""

from __future__ import annotations

from typing import Protocol

from backend.domain.songs_pitch.value_objects import SongPitchCurve


class PitchCacheRepository(Protocol):
    """F0 曲线缓存仓储协议"""

    def get(self, song_id: str) -> SongPitchCurve | None:
        """按歌曲 ID 读取缓存, 未命中返回 None"""
        ...

    def set(self, song_id: str, curve: SongPitchCurve) -> None:
        """写入缓存"""
        ...

    def invalidate(self, song_id: str) -> None:
        """失效缓存 (歌曲删除时调用)"""
        ...
