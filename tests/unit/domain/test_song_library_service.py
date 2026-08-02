"""SongLibraryService 应用服务单元测试 — TDD RED (Fake 仓储)"""

import pytest

from backend.domain.songs.value_objects import SongMetadata
from backend.domain.songs.entities import Song, SongListPage
from backend.domain.songs.repository import SongRepository
from backend.application.songs.song_library_service import (
    SongLibraryService,
    SongNotFoundError,
    DuplicateSongError,
)


class FakeSongRepository:
    """内存版仓储 — 与服务测试相同的过滤/分页语义"""

    def __init__(self) -> None:
        self._songs: dict[str, Song] = {}

    def add(self, song: Song) -> Song:
        self._songs[song.id] = song
        return song

    def get_by_id(self, song_id: str) -> Song | None:
        return self._songs.get(song_id)

    def list(self, *, page, limit, style=None, difficulty=None, search=None):
        items = list(self._songs.values())
        if style:
            items = [s for s in items if s.metadata.style == style]
        if difficulty:
            items = [s for s in items if s.metadata.difficulty == difficulty]
        if search:
            q = search.lower().strip()
            items = [
                s for s in items
                if q in s.metadata.title.lower() or q in s.metadata.artist.lower()
            ]
        total = len(items)
        start = (page - 1) * limit
        return items[start:start + limit], total

    def delete(self, song_id: str) -> bool:
        return self._songs.pop(song_id, None) is not None

    def find_duplicate(self, metadata: SongMetadata) -> Song | None:
        key = metadata.duplicate_key()
        for s in self._songs.values():
            if s.metadata.duplicate_key() == key:
                return s
        return None


@pytest.fixture
def service() -> SongLibraryService:
    return SongLibraryService(FakeSongRepository())


class TestAddSong:
    def test_add_generates_unique_id(self, service):
        song = service.add_song(SongMetadata(title='月亮代表我的心', artist='邓丽君'))
        assert song.id
        assert song.metadata.title == '月亮代表我的心'
        # 连续两次生成不同 ID
        song2 = service.add_song(SongMetadata(title='小星星', artist='a'))
        assert song2.id != song.id

    def test_add_duplicate_raises(self, service):
        service.add_song(SongMetadata(title='月亮代表我的心', artist='邓丽君'))
        with pytest.raises(DuplicateSongError):
            service.add_song(SongMetadata(title='月亮代表我的心', artist='邓丽君'))

    def test_add_different_artist_not_duplicate(self, service):
        service.add_song(SongMetadata(title='月亮代表我的心', artist='邓丽君'))
        s2 = service.add_song(SongMetadata(title='月亮代表我的心', artist='王菲'))
        assert s2.id

    def test_add_persists_filepath_and_scoring_config(self, service):
        song = service.add_song(
            SongMetadata(title='a', artist='b'),
            filepath='/data/songs/a.wav',
            duration_seconds=120.0,
            scoring_config={'pitch': 30},
        )
        assert song.filepath == '/data/songs/a.wav'
        assert song.duration_seconds == 120.0
        assert song.scoring_config == {'pitch': 30}


class TestListSongs:
    def test_list_paginates(self, service):
        for i in range(25):
            service.add_song(SongMetadata(title=f'歌曲{i}', artist='a'))
        page = service.list_songs(page=2, limit=10)
        assert len(page.songs) == 10
        assert page.total == 25
        assert page.page == 2
        assert page.limit == 10

    def test_list_filter_by_style(self, service):
        service.add_song(SongMetadata(title='流行歌', artist='a', style='pop'))
        service.add_song(SongMetadata(title='美声歌', artist='b', style='classical'))
        page = service.list_songs(style='pop')
        assert len(page.songs) == 1
        assert page.songs[0].metadata.title == '流行歌'

    def test_list_filter_by_difficulty(self, service):
        service.add_song(SongMetadata(title='初级', artist='a', difficulty='beginner'))
        service.add_song(SongMetadata(title='高级', artist='b', difficulty='advanced'))
        page = service.list_songs(difficulty='advanced')
        assert len(page.songs) == 1
        assert page.songs[0].metadata.title == '高级'

    def test_list_search_by_title(self, service):
        service.add_song(SongMetadata(title='月亮代表我的心', artist='邓丽君'))
        service.add_song(SongMetadata(title='小星星', artist='a'))
        page = service.list_songs(search='月亮')
        assert len(page.songs) == 1
        assert '月亮' in page.songs[0].metadata.title

    def test_list_search_by_artist_case_insensitive(self, service):
        service.add_song(SongMetadata(title='a', artist='Taylor Swift'))
        service.add_song(SongMetadata(title='b', artist='Deng Lijun'))
        page = service.list_songs(search='TAYLOR')
        assert len(page.songs) == 1
        assert page.songs[0].metadata.artist == 'Taylor Swift'

    def test_list_search_no_match_returns_empty(self, service):
        service.add_song(SongMetadata(title='a', artist='b'))
        page = service.list_songs(search='zzzz')
        assert len(page.songs) == 0
        assert page.total == 0


class TestGetAndDelete:
    def test_get_song(self, service):
        s = service.add_song(SongMetadata(title='a', artist='b'))
        got = service.get_song(s.id)
        assert got.id == s.id

    def test_get_missing_raises(self, service):
        with pytest.raises(SongNotFoundError):
            service.get_song('not-exist')

    def test_delete_song(self, service):
        s = service.add_song(SongMetadata(title='a', artist='b'))
        assert service.delete_song(s.id) is True
        with pytest.raises(SongNotFoundError):
            service.get_song(s.id)

    def test_delete_missing_raises(self, service):
        with pytest.raises(SongNotFoundError):
            service.delete_song('not-exist')
