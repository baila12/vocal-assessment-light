"""Song 领域实体与值对象单元测试"""

from dataclasses import FrozenInstanceError

import pytest

from backend.domain.songs.value_objects import SongMetadata
from backend.domain.songs.entities import Song


class TestSongMetadata:
    """歌曲元数据值对象 — frozen + 默认值 + duplicate_key"""

    def test_defaults(self):
        m = SongMetadata(title='月亮代表我的心', artist='邓丽君')
        assert m.title == '月亮代表我的心'
        assert m.artist == '邓丽君'
        assert m.key == 'C'
        assert m.bpm == 0
        assert m.difficulty == 'beginner'
        assert m.style == 'pop'

    def test_frozen_immutable(self):
        m = SongMetadata(title='x', artist='y')
        with pytest.raises(FrozenInstanceError):
            m.title = 'z'

    def test_custom_values(self):
        m = SongMetadata(
            title='我的太阳', artist='帕瓦罗蒂', key='D',
            bpm=90, difficulty='advanced', style='classical',
        )
        assert m.bpm == 90
        assert m.difficulty == 'advanced'
        assert m.style == 'classical'

    def test_duplicate_key_matches_same_title_artist(self):
        a = SongMetadata(title='月亮代表我的心', artist='邓丽君')
        b = SongMetadata(title='月亮代表我的心', artist='邓丽君')
        c = SongMetadata(title='月亮代表我的心', artist='王菲')
        assert a.duplicate_key() == b.duplicate_key()
        assert a.duplicate_key() != c.duplicate_key()

    def test_duplicate_key_normalizes_case_and_whitespace(self):
        a = SongMetadata(title='  Moon Light  ', artist='Taylor Swift')
        b = SongMetadata(title='moon light', artist='taylor swift')
        assert a.duplicate_key() == b.duplicate_key()

    def test_invalid_difficulty_raises(self):
        with pytest.raises(ValueError):
            SongMetadata(title='a', artist='b', difficulty='hacker_rank')

    def test_invalid_style_raises(self):
        with pytest.raises(ValueError):
            SongMetadata(title='a', artist='b', style='jazz')


class TestSong:
    """Song 聚合根实体 — frozen + 默认字段"""

    def test_defaults(self):
        s = Song(id='song_001', metadata=SongMetadata(title='t', artist='a'))
        assert s.feature_status == 'pending'
        assert s.duration_seconds == 0.0
        assert s.scoring_config == {}
        assert s.filepath == ''

    def test_frozen_immutable(self):
        s = Song(id='song_001', metadata=SongMetadata(title='t', artist='a'))
        with pytest.raises(FrozenInstanceError):
            s.id = 'other'

    def test_full_construction(self):
        s = Song(
            id='song_001',
            metadata=SongMetadata(title='t', artist='a', bpm=100),
            filepath='/data/songs/song_001.wav',
            duration_seconds=180.5,
            feature_status='ready',
            scoring_config={'pitch': 30, 'rhythm': 15},
            created_at='2026-08-02T10:00:00',
        )
        assert s.duration_seconds == 180.5
        assert s.feature_status == 'ready'
        assert s.scoring_config['pitch'] == 30
