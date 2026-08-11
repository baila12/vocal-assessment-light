"""SqliteSongRepository 单元测试 — TDD RED (内存数据库)"""

import threading

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


class TestListAllWithFilepath:
    """供匹配特征预算式预计算枚举 — 仅返回 filepath 非空且文件存在"""

    def test_returns_only_songs_with_existing_file(self, repo, tmp_path):
        audio = tmp_path / 'song.wav'
        audio.write_bytes(b'RIFF\x24\x00\x00\x00WAVE')  # 假 WAV 头, 仅测试文件存在性
        repo.add(Song(
            id='a', metadata=SongMetadata(title='有文件', artist='甲'),
            filepath=str(audio),
        ))
        repo.add(_song(title='无路径', song_id='b'))
        repo.add(Song(
            id='c', metadata=SongMetadata(title='路径失效', artist='丙'),
            filepath=str(tmp_path / 'missing.wav'),
        ))

        songs = repo.list_all_with_filepath()
        assert [s.id for s in songs] == ['a']

    def test_empty_repo_returns_empty(self, repo):
        assert repo.list_all_with_filepath() == []


class TestPragmas:
    """P0-2 (审查 C2): 文件库启用 WAL + busy_timeout — 并发安全基线"""

    def test_file_db_uses_wal_journal_mode(self, tmp_path):
        """文件库 journal_mode 应为 wal (并发读写下防 SQLITE_BUSY/死锁)"""
        repo = SqliteSongRepository(db_path=tmp_path / 'songs.db')
        mode = repo._conn.execute('PRAGMA journal_mode').fetchone()[0]
        assert mode == 'wal', f'文件库 journal_mode 应为 wal, 实际 {mode}'

    def test_busy_timeout_is_set(self, tmp_path):
        """busy_timeout=5000ms — 锁竞争时等待而非立即报 SQLITE_BUSY"""
        repo = SqliteSongRepository(db_path=tmp_path / 'songs.db')
        timeout = repo._conn.execute('PRAGMA busy_timeout').fetchone()[0]
        assert timeout == 5000

    def test_memory_db_unaffected(self, repo):
        """:memory: 库不受 WAL pragma 影响, 仍正常读写"""
        repo.add(_song(song_id='s1'))
        assert repo.get_by_id('s1') is not None


class TestConcurrency:
    """P0-2 (审查 C2): 读写并发 — 同一连接持锁串行化, 无异常/无脏读"""

    def test_concurrent_reads_and_writes_no_crash(self, tmp_path):
        """3 写线程 + 3 读线程并发 — 不抛异常且数据一致 (读锁缺失时可能崩溃)"""
        repo = SqliteSongRepository(db_path=tmp_path / 'songs.db')
        errors: list[Exception] = []
        lock = threading.Lock()

        def _writer(i: int) -> None:
            try:
                for k in range(10):
                    repo.add(_song(title=f'歌{i}-{k}', artist='邓丽君', song_id=f'w{i}_{k}'))
            except Exception as exc:  # pragma: no cover - 仅记录并发异常
                with lock:
                    errors.append(exc)

        def _reader() -> None:
            try:
                for _ in range(20):
                    repo.list(page=1, limit=50)
                    repo.get_by_id('w1_0')
                    repo.find_duplicate(SongMetadata(title='歌1-0', artist='邓丽君'))
            except Exception as exc:  # pragma: no cover - 仅记录并发异常
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=_writer, args=(i,)) for i in range(3)]
        threads += [threading.Thread(target=_reader) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f'并发访问异常: {errors}'
        items, total = repo.list(page=1, limit=200)
        assert total == 30
