"""
SongLibraryService — 标准曲库应用服务

编排领域用例: 添加(去重) / 分页搜索列表 / 详情 / 删除。
业务逻辑依赖 SongRepository 抽象接口, 与存储实现解耦。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from backend.domain.songs.entities import Song, SongListPage
from backend.domain.songs.repository import SongRepository
from backend.domain.songs.value_objects import SongMetadata


class SongNotFoundError(Exception):
    """歌曲不存在 — 应用层异常"""

    def __init__(self, song_id: str) -> None:
        super().__init__(f'歌曲不存在: {song_id}')
        self.song_id = song_id


class DuplicateSongError(Exception):
    """重复歌曲 — 歌名+歌手已存在"""

    def __init__(self, metadata: SongMetadata) -> None:
        super().__init__(f'歌曲已存在: {metadata.title} - {metadata.artist}')
        self.metadata = metadata


class SongLibraryService:
    """标准曲库应用服务"""

    def __init__(self, repo: SongRepository) -> None:
        self._repo = repo

    def add_song(
        self,
        metadata: SongMetadata,
        *,
        filepath: str = '',
        duration_seconds: float = 0.0,
        scoring_config: dict | None = None,
    ) -> Song:
        """添加歌曲到曲库 — 先做重复检测

        Raises:
            DuplicateSongError: 歌名+歌手已存在
        """
        if self._repo.find_duplicate(metadata) is not None:
            raise DuplicateSongError(metadata)

        song = Song(
            id=uuid.uuid4().hex[:12],
            metadata=metadata,
            filepath=filepath,
            duration_seconds=duration_seconds,
            scoring_config=scoring_config or {},
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        return self._repo.add(song)

    def list_songs(
        self,
        *,
        page: int = 1,
        limit: int = 20,
        style: str | None = None,
        difficulty: str | None = None,
        search: str | None = None,
    ) -> SongListPage:
        """分页列出歌曲, 支持风格/难度筛选 + 歌名/歌手搜索"""
        songs, total = self._repo.list(
            page=max(1, page),
            limit=max(1, limit),
            style=style,
            difficulty=difficulty,
            search=search,
        )
        return SongListPage(
            songs=tuple(songs),
            total=total,
            page=max(1, page),
            limit=max(1, limit),
        )

    def get_song(self, song_id: str) -> Song:
        """按 ID 查询歌曲

        Raises:
            SongNotFoundError: 歌曲不存在
        """
        song = self._repo.get_by_id(song_id)
        if song is None:
            raise SongNotFoundError(song_id)
        return song

    def delete_song(self, song_id: str) -> bool:
        """删除歌曲

        Raises:
            SongNotFoundError: 歌曲不存在
        """
        if not self._repo.delete(song_id):
            raise SongNotFoundError(song_id)
        return True
