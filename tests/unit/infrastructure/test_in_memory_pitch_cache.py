"""
InMemoryPitchCacheRepository 单元测试 — P1-6 (审查 M7: 无界 dict → LRU 上限)

修复: set() 按 max_entries (默认 50) LRU 淘汰; get() 刷新访问序。
"""

from backend.domain.songs_pitch.value_objects import SongPitchCurve
from backend.infrastructure.persistence.in_memory_pitch_cache import (
    InMemoryPitchCacheRepository,
)


def _curve(song_id: str, n: int = 10) -> SongPitchCurve:
    return SongPitchCurve(
        song_id=song_id,
        frequencies=tuple([440.0] * n),
        times=tuple(i * 0.1 for i in range(n)),
        confidence=tuple([1.0] * n),
    )


class TestLruEviction:
    """LRU 淘汰 — 超上限时逐出最久未访问条目"""

    def test_exceeds_max_entries_evicts_oldest(self):
        repo = InMemoryPitchCacheRepository(max_entries=3)
        for i in range(3):
            repo.set(f's{i}', _curve(f's{i}'))
        repo.set('s3', _curve('s3'))
        assert repo.get('s0') is None, '最早插入的条目应被 LRU 淘汰'
        assert repo.get('s1') is not None
        assert repo.get('s3') is not None

    def test_recently_accessed_survives_eviction(self):
        """get() 刷新访问序 — 被读过的条目免于淘汰"""
        repo = InMemoryPitchCacheRepository(max_entries=3)
        for i in range(3):
            repo.set(f's{i}', _curve(f's{i}'))
        repo.get('s0')  # 访问 s0 → 置为最新
        repo.set('s3', _curve('s3'))
        assert repo.get('s0') is not None, '被访问过的 s0 应保留'
        assert repo.get('s1') is None, '未被访问的 s1 应被淘汰'

    def test_size_stays_within_max_after_burst(self):
        repo = InMemoryPitchCacheRepository(max_entries=3)
        for i in range(10):
            repo.set(f's{i}', _curve(f's{i}'))
        # 只能有 3 条
        present = [f's{i}' for i in range(10) if repo.get(f's{i}') is not None]
        assert len(present) == 3


class TestBasicOps:
    def test_get_missing_returns_none(self):
        repo = InMemoryPitchCacheRepository()
        assert repo.get('nope') is None

    def test_set_get_roundtrip(self):
        repo = InMemoryPitchCacheRepository()
        repo.set('s0', _curve('s0'))
        got = repo.get('s0')
        assert got is not None
        assert got.song_id == 's0'
        assert got.frequencies[0] == 440.0

    def test_invalidate_removes_entry(self):
        repo = InMemoryPitchCacheRepository()
        repo.set('s0', _curve('s0'))
        repo.invalidate('s0')
        assert repo.get('s0') is None

    def test_default_max_entries_is_50(self):
        repo = InMemoryPitchCacheRepository()
        assert repo.max_entries == 50
