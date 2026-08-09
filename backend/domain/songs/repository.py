"""
歌曲库仓储接口 — 仓储模式

业务逻辑依赖抽象接口, 而非具体存储 (SQLite/JSON/内存可切换)。
"""

from __future__ import annotations

from typing import Protocol

from backend.domain.songs.entities import Song
from backend.domain.songs.value_objects import SongMetadata


class SongRepository(Protocol):
    """标准曲库仓储协议"""

    def add(self, song: Song) -> Song:
        """持久化歌曲, 返回存储后的实体"""
        ...

    def get_by_id(self, song_id: str) -> Song | None:
        """按 ID 查询, 不存在返回 None"""
        ...

    def list(
        self,
        *,
        page: int,
        limit: int,
        style: str | None = None,
        difficulty: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Song], int]:
        """分页列表 + 风格/难度筛选 + 歌名/歌手模糊搜索

        Returns:
            (当前页歌曲列表, 筛选后总数)
        """
        ...

    def delete(self, song_id: str) -> bool:
        """删除歌曲, 返回是否成功删除"""
        ...

    def find_duplicate(self, metadata: SongMetadata) -> Song | None:
        """按 (歌名+歌手) 查找重复歌曲, 无则返回 None"""
        ...

    def list_all_with_filepath(self) -> list[Song]:
        """列出所有 filepath 非空且文件存在的歌曲 (供匹配特征预算式预计算)"""
        ...
