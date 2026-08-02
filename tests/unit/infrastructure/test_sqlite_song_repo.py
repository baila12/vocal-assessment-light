"""SqliteSongRepository 单元测试 — TDD RED (内存数据库)"""

import pytest

from backend.domain.songs.value_objects import SongMetadata
from backend.domain.songs.entities import Song
from backend.infrastructure.persistence.sqlite_song_repo import SqliteSongRepository


@pytest.fixture
def repo() -> SqliteSongRepository:
    return SqliteSongRepository(db_path=':memory:')


def _song(
    title: str = '月亮代表我的心',
    artist: str = '邓丽君',
    style: str = 'pop',
    difficulty: str = 'beginner',
    song_id: str = 's1',
) -> Song:
    return Song(
        id=song_id,
        metadata=SongMetadata(
            title=title, artist=artist, style=style, difficulty=difficulty,
        ),
    )


class TestCrud:
    def test_add_and_get(self, repo):
        repo.add(_song(song_id='song_001'))
        got = repo.get_by_id('song_001')
        assert got is not None
        assert got.metadata.title == '月亮代表我的心'
        assert got.metadata.artist == '邓丽君'

    def test_get_missing_returns_none(self, repo):
        assert repo.get_by_id('nope') is None

    def test_add_persists_full_fields(self, repo):
        repo.add(Song(
            id='song_x',
            metadata=SongMetadata(title='a', artist='b', key='D', bpm=100, difficulty='advanced', style='classical'),
            filepath='/data/songs/song_x.wav',
            duration_seconds=180.5,
            feature_status='ready',
            scoring_config={'pitch': 30},
            created_at='2026-08-02T10:00:00',
        ))
        got = repo.get_by_id('song_x')
        assert got.metadata.bpm == 100
        assert got.metadata.key == 'D'
        assert got.duration_seconds == 180.5
        assert got.feature_status == 'ready'
        assert got.scoring_config == {'pitch': 30}

    def test_delete(self, repo):
        repo.add(_song(song_id='s1'))
        assert repo.delete('s1') is True
        assert repo.delete('s1') is False
        assert repo.get_by_id('s1') is None


class TestList:
    def test_list_pagination(self, repo):
        for i in range(25):
            repo.add(_song(title=f'歌曲{i}', song_id=f's{i:03d}'))
        items, total = repo.list(page=2, limit=10)
        assert len(items) == 10
        assert total == 25

    def test_list_filter_by_style(self, repo):
        repo.add(_song(title='流行歌', style='pop', song_id='a'))
        repo.add(_song(title='美声歌', style='classical', song_id='b'))
        items, total = repo.list(page=1, limit=10, style='pop')
        assert len(items) == 1
        assert items[0].metadata.title == '流行歌'
        assert total == 1

    def test_list_filter_by_difficulty(self, repo):
        repo.add(_song(title='初级', difficulty='beginner', song_id='a'))
        repo.add(_song(title='高级', difficulty='advanced', song_id='b'))
        items, total = repo.list(page=1, limit=10, difficulty='advanced')
        assert len(items) == 1
        assert items[0].metadata.title == '高级'

    def test_list_search_matches_title(self, repo):
        repo.add(_song(title='月亮代表我的心', song_id='a'))
        repo.add(_song(title='小星星', song_id='b'))
        items, total = repo.list(page=1, limit=10, search='月亮')
        assert len(items) == 1
        assert items[0].metadata.title == '月亮代表我的心'

    def test_list_search_matches_artist_case_insensitive(self, repo):
        repo.add(_song(title='a', artist='Taylor Swift', song_id='a'))
        items, total = repo.list(page=1, limit=10, search='taylor')
        assert len(items) == 1

    def test_list_combined_filter_and_search(self, repo):
        repo.add(_song(title='流行歌', style='pop', difficulty='beginner', song_id='a'))
        repo.add(_song(title='流行高级', style='pop', difficulty='advanced', song_id='b'))
        repo.add(_song(title='美声歌', style='classical', difficulty='advanced', song_id='c'))
        items, total = repo.list(page=1, limit=10, style='pop', difficulty='advanced')
        assert len(items) == 1
        assert items[0].metadata.title == '流行高级'


class TestDuplicateDetection:
    def test_find_duplicate_matches_title_and_artist(self, repo):
        repo.add(_song(title='Moon Light', artist='Taylor Swift', song_id='a'))
        dup = repo.find_duplicate(SongMetadata(title='moon light', artist='taylor swift'))
        assert dup is not None
        assert dup.id == 'a'

    def test_find_duplicate_different_artist_returns_none(self, repo):
        repo.add(_song(title='月亮代表我的心', artist='邓丽君', song_id='a'))
        assert repo.find_duplicate(SongMetadata(title='月亮代表我的心', artist='王菲')) is None

    def test_find_duplicate_empty_repo_returns_none(self, repo):
        assert repo.find_duplicate(SongMetadata(title='a', artist='b')) is None
