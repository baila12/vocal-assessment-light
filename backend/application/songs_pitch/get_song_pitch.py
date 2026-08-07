"""
获取歌曲音高用例 — v7.13 参考音高编排

查缓存 → 未命中则从歌曲文件提取 F0 + 写缓存。
"""

from __future__ import annotations

from backend.domain.songs_pitch.value_objects import SongPitchCurve
from backend.domain.songs_pitch.repository import PitchCacheRepository
from backend.domain.songs_pitch.services import PitchExtractionService


class GetSongPitchUseCase:
    """歌曲参考音高获取用例 — 缓存优先"""

    def __init__(
        self,
        repo: PitchCacheRepository,
        extractor: PitchExtractionService = PitchExtractionService,
    ) -> None:
        self._repo = repo
        self._extractor = extractor

    def execute(self, song_id: str, filepath: str) -> SongPitchCurve:
        """获取歌曲 F0 曲线 — 缓存命中直接返回, 否则提取并缓存"""
        cached = self._repo.get(song_id)
        if cached is not None:
            return cached

        curve = self._extractor.extract(filepath, song_id)
        self._repo.set(song_id, curve)
        return curve
