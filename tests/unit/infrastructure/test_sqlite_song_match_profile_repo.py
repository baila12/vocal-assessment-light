"""SqliteSongMatchProfileRepository 单元测试 — TDD RED (内存数据库)"""

import pytest

from backend.domain.song_match.value_objects import SongMatchProfile
from backend.infrastructure.persistence.sqlite_song_match_profile_repo import (
    SqliteSongMatchProfileRepository,
)

CHROMA_C = (1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


@pytest.fixture
def repo() -> SqliteSongMatchProfileRepository:
    return SqliteSongMatchProfileRepository(db_path=':memory:')


def _profile(
    song_id: str = 's1',
    title: str = '月亮代表我的心',
    artist: str = '邓丽君',
    bpm: float = 78.0,
    key: str = 'C',
    chroma: tuple[float, ...] = CHROMA_C,
    duration: float = 180.0,
) -> SongMatchProfile:
    return SongMatchProfile(
        song_id=song_id, title=title, artist=artist,
        bpm=bpm, key=key, chroma=chroma, duration_seconds=duration,
    )


class TestCrud:
    def test_save_and_get(self, repo):
        repo.save(_profile(song_id='song_001'))
        got = repo.get('song_001')
        assert got is not None
        assert got.title == '月亮代表我的心'
        assert got.artist == '邓丽君'
        assert got.bpm == pytest.approx(78.0)
        assert got.key == 'C'

    def test_get_missing_returns_none(self, repo):
        assert repo.get('nope') is None

    def test_list_all_empty(self, repo):
        assert repo.list_all() == []

    def test_list_all_returns_all(self, repo):
        repo.save(_profile('a', title='歌A'))
        repo.save(_profile('b', title='歌B'))
        repo.save(_profile('c', title='歌C'))
        items = repo.list_all()
        assert len(items) == 3
        assert {p.song_id for p in items} == {'a', 'b', 'c'}

    def test_save_upsert_overwrites(self, repo):
        repo.save(_profile(song_id='s1', bpm=78.0))
        repo.save(_profile(song_id='s1', bpm=120.0))
        got = repo.get('s1')
        assert got is not None
        assert got.bpm == pytest.approx(120.0)
        assert repo.list_all().__len__() == 1

    def test_chroma_json_roundtrip(self, repo):
        """chroma 经 JSON 存取后 tuple 往返一致"""
        repo.save(_profile(song_id='s1'))
        got = repo.get('s1')
        assert got is not None
        assert got.chroma == CHROMA_C
        assert isinstance(got.chroma, tuple)

    def test_delete(self, repo):
        repo.save(_profile(song_id='s1'))
        assert repo.delete('s1') is True
        assert repo.delete('s1') is False
        assert repo.get('s1') is None

    def test_non_12_dim_chroma_row_defaults_to_zero(self, repo):
        """防御: 库中异常 chroma (非 12 维) 行 → 零向量, 不抛 ValueError (审查修复)"""
        repo.save(_profile(song_id='s1', chroma=CHROMA_C))
        # 模拟手工改库: 写入非 12 维 chroma
        repo._conn.execute(
            'UPDATE song_match_profiles SET chroma = ? WHERE song_id = ?',
            ('[0.5, 0.5]', 's1'),
        )
        repo._conn.commit()
        got = repo.get('s1')
        assert got is not None
        assert got.chroma == (0.0,) * 12

    def test_empty_chroma_json_defaults_to_zero(self, repo):
        """防御: chroma 为默认空 JSON '[]' (列 DEFAULT) → 零向量 (审查修复)"""
        repo.save(_profile(song_id='s1'))
        repo._conn.execute(
            "UPDATE song_match_profiles SET chroma = '[]' WHERE song_id = ?",
            ('s1',),
        )
        repo._conn.commit()
        got = repo.get('s1')
        assert got is not None
        assert got.chroma == (0.0,) * 12
