"""
GetSongPitchUseCase 测试 — v7.13 参考音高编排

用例职责: 查缓存 → 未命中则提取 + 写缓存。
"""

import pytest

from backend.domain.songs_pitch.value_objects import SongPitchCurve
from backend.domain.songs_pitch.repository import PitchCacheRepository
from backend.application.songs_pitch.get_song_pitch import GetSongPitchUseCase


class FakeExtractor:
    """Fake 提取器 — 记录调用次数, 返回固定曲线"""

    def __init__(self):
        self.call_count = 0
        self.calls: list[str] = []

    def extract(self, wav_path: str, song_id: str, **kwargs) -> SongPitchCurve:
        self.call_count += 1
        self.calls.append(wav_path)
        return SongPitchCurve(
            song_id=song_id,
            frequencies=(261.6, 293.7),
            times=(0.0, 0.032),
            confidence=(0.9, 0.8),
        )


class TestGetSongPitchUseCase:
    """GetSongPitchUseCase — 缓存编排"""

    def setup_method(self):
        self.repo = FakePitchCacheRepo()
        self.extractor = FakeExtractor()
        self.usecase = GetSongPitchUseCase(repo=self.repo, extractor=self.extractor)

    def test_cache_miss_extracts_and_caches(self):
        """首次调用 → 提取 + 写入缓存"""
        curve = self.usecase.execute('moon_love', '/songs/moon_love.wav')

        assert self.extractor.call_count == 1
        assert self.extractor.calls == ['/songs/moon_love.wav']
        assert curve.song_id == 'moon_love'
        assert self.repo.get('moon_love') is not None

    def test_cache_hit_skips_extraction(self):
        """缓存命中 → 不重复提取"""
        self.usecase.execute('moon_love', '/songs/moon_love.wav')
        curve2 = self.usecase.execute('moon_love', '/songs/moon_love.wav')

        assert self.extractor.call_count == 1  # 仅首次提取
        assert curve2.song_id == 'moon_love'

    def test_invalidate_triggers_reextract(self):
        """invalidate 后 → 下次重新提取"""
        self.usecase.execute('moon_love', '/songs/moon_love.wav')
        self.repo.invalidate('moon_love')
        self.usecase.execute('moon_love', '/songs/moon_love.wav')

        assert self.extractor.call_count == 2

    def test_different_song_ids_isolated(self):
        """不同歌曲互不影响"""
        self.usecase.execute('moon_love', '/songs/moon_love.wav')
        curve2 = self.usecase.execute('other', '/songs/other.wav')

        assert self.extractor.call_count == 2
        assert curve2.song_id == 'other'


class FakePitchCacheRepo:
    """测试用内存缓存仓储"""

    def __init__(self):
        self._cache: dict[str, SongPitchCurve] = {}

    def get(self, song_id: str) -> SongPitchCurve | None:
        return self._cache.get(song_id)

    def set(self, song_id: str, curve: SongPitchCurve) -> None:
        self._cache[song_id] = curve

    def invalidate(self, song_id: str) -> None:
        self._cache.pop(song_id, None)
