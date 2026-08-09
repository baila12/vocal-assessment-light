"""
song_match 匹配特征仓储接口 — 仓储模式

业务逻辑依赖抽象接口, 而非具体存储 (SQLite/内存可切换)。
"""

from __future__ import annotations

from typing import Protocol

from backend.domain.song_match.value_objects import SongMatchProfile


class SongMatchProfileRepository(Protocol):
    """歌曲匹配特征 profile 仓储协议"""

    def get(self, song_id: str) -> SongMatchProfile | None:
        """按歌曲 ID 查询, 不存在返回 None"""
        ...

    def list_all(self) -> list[SongMatchProfile]:
        """列出全部 profile (供匹配枚举)"""
        ...

    def save(self, profile: SongMatchProfile) -> SongMatchProfile:
        """保存/更新 profile (upsert), 返回存储后的实体"""
        ...

    def delete(self, song_id: str) -> bool:
        """删除 profile, 返回是否删除成功"""
        ...
