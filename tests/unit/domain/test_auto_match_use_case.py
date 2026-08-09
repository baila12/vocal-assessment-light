"""
AutoMatchUseCase 编排测试 — TDD RED (v7.14 auto-match)

mock song_repo/profile_repo/extractor, 验证用例编排:
缺失 profile 预算式生成 / 已有 profile 不重算 / 提取失败跳过 /
超时 partial / 空库 fallback / 用户音频缺失传播异常。
"""
import wave

import pytest

from backend.application.song_match.auto_match_use_case import AutoMatchUseCase
from backend.domain.song_match.value_objects import MatchFeatures, SongMatchProfile
from backend.domain.songs.entities import Song
from backend.domain.songs.value_objects import SongMetadata

SR = 22050
CHROMA_C = (1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

USER_FEATURES = MatchFeatures(
    bpm=78.0, detected_key='C', key_confidence=0.8,
    chroma=CHROMA_C, duration_seconds=180.0,
)


def _write_wav(path, duration=1.0, sr=SR):
    """写最小 16-bit PCM WAV — 供 librosa.load 读取"""
    import numpy as np
    n = int(sr * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    y = (np.sin(2 * np.pi * 220 * t) * 0.8 * 32767).astype('<i2')
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(y.tobytes())


class FakeSongRepo:
    def __init__(self, songs):
        self._songs = list(songs)

    def list_all_with_filepath(self):
        return list(self._songs)


class FakeProfileRepo:
    def __init__(self, profiles=None):
        self._profiles = {p.song_id: p for p in (profiles or [])}

    def get(self, song_id):
        return self._profiles.get(song_id)

    def list_all(self):
        return list(self._profiles.values())

    def save(self, profile):
        self._profiles[profile.song_id] = profile
        return profile


class FakeExtractor:
    """返回固定特征, 记录调用次数"""

    def __init__(self, features):
        self._features = features
        self.call_count = 0

    def extract(self, y, sr, **kwargs):
        self.call_count += 1
        return self._features


def _song(song_id, title, filepath):
    return Song(id=song_id, metadata=SongMetadata(title=title, artist='测试歌手'), filepath=filepath)


class TestAutoMatchUseCase:
    def test_ensure_profiles_generates_missing(self, tmp_path):
        """无 profile 的歌曲被提取并持久化, 匹配成功"""
        user_wav = tmp_path / 'user.wav'
        _write_wav(user_wav)
        good_wav = tmp_path / 'good.wav'
        _write_wav(good_wav)
        song_repo = FakeSongRepo([_song('good', '好歌', str(good_wav))])
        profile_repo = FakeProfileRepo()

        uc = AutoMatchUseCase(song_repo, profile_repo, extractor=FakeExtractor(USER_FEATURES))
        result = uc.execute(str(user_wav))

        assert result.matched is True
        assert result.matched_song['id'] == 'good'
        saved = profile_repo.list_all()
        assert len(saved) == 1
        assert saved[0].song_id == 'good'
        assert saved[0].title == '好歌'

    def test_existing_profiles_not_recomputed(self, tmp_path):
        """已有 profile 的歌曲不重复提取 (extractor 仅用户音频 1 次)"""
        user_wav = tmp_path / 'user.wav'
        _write_wav(user_wav)
        song_wav = tmp_path / 'song.wav'
        _write_wav(song_wav)
        existing = SongMatchProfile(
            song_id='s1', title='已有', artist='甲', bpm=78.0, key='C',
            chroma=CHROMA_C, duration_seconds=180.0,
        )
        extractor = FakeExtractor(USER_FEATURES)
        uc = AutoMatchUseCase(
            FakeSongRepo([_song('s1', '已有', str(song_wav))]),
            FakeProfileRepo([existing]),
            extractor=extractor,
        )
        result = uc.execute(str(user_wav))
        assert result.matched is True
        assert extractor.call_count == 1  # 仅用户音频

    def test_extraction_failure_skipped(self, tmp_path):
        """歌曲文件缺失 → 跳过该歌, 其余正常匹配"""
        user_wav = tmp_path / 'user.wav'
        _write_wav(user_wav)
        good_wav = tmp_path / 'good.wav'
        _write_wav(good_wav)
        profile_repo = FakeProfileRepo()
        uc = AutoMatchUseCase(
            FakeSongRepo([
                _song('good', '好歌', str(good_wav)),
                _song('bad', '坏歌', str(tmp_path / 'missing.wav')),
            ]),
            profile_repo,
            extractor=FakeExtractor(USER_FEATURES),
        )
        result = uc.execute(str(user_wav))
        assert result.matched is True
        assert result.matched_song['id'] == 'good'
        assert [p.song_id for p in profile_repo.list_all()] == ['good']

    def test_timeout_returns_partial(self, tmp_path):
        """timeout_s=0 → deadline 已过 → partial=True"""
        user_wav = tmp_path / 'user.wav'
        _write_wav(user_wav)
        song_wav = tmp_path / 'song.wav'
        _write_wav(song_wav)
        existing = SongMatchProfile(
            song_id='s1', title='已有', artist='甲', bpm=78.0, key='C',
            chroma=CHROMA_C, duration_seconds=180.0,
        )
        uc = AutoMatchUseCase(
            FakeSongRepo([_song('s1', '已有', str(song_wav))]),
            FakeProfileRepo([existing]),
            extractor=FakeExtractor(USER_FEATURES),
        )
        result = uc.execute(str(user_wav), timeout_s=0.0)
        assert result.partial is True

    def test_empty_library_returns_no_profiles(self, tmp_path):
        """曲库无歌曲 → no_profiles fallback"""
        user_wav = tmp_path / 'user.wav'
        _write_wav(user_wav)
        uc = AutoMatchUseCase(
            FakeSongRepo([]), FakeProfileRepo(), extractor=FakeExtractor(USER_FEATURES)
        )
        result = uc.execute(str(user_wav))
        assert result.matched is False
        assert result.fallback_reason == 'no_profiles'

    def test_user_audio_missing_propagates(self, tmp_path):
        """用户音频不存在 → 异常向上传播 (不静默)"""
        uc = AutoMatchUseCase(
            FakeSongRepo([]), FakeProfileRepo(), extractor=FakeExtractor(USER_FEATURES)
        )
        with pytest.raises((OSError, FileNotFoundError)):
            uc.execute(str(tmp_path / 'missing.wav'))
