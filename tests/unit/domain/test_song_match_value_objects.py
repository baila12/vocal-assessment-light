"""
song_match 领域值对象单元测试 — TDD RED (v7.14 auto-match)

MatchFeatures / SongMatchProfile / MatchCandidate / MatchResult
不可变 + 校验 + JSON 兼容序列化。
"""
import json
from dataclasses import FrozenInstanceError

import pytest

from backend.domain.song_match.value_objects import (
    MatchCandidate,
    MatchFeatures,
    MatchResult,
    SongMatchProfile,
)

CHROMA_C = (1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


class TestMatchFeatures:
    """用户音频匹配特征 — frozen + 校验"""

    def test_frozen_immutable(self):
        f = MatchFeatures(bpm=78.0, detected_key='C', key_confidence=0.8,
                          chroma=CHROMA_C, duration_seconds=180.0)
        with pytest.raises(FrozenInstanceError):
            f.bpm = 90.0  # type: ignore[misc]

    def test_valid_chroma_length(self):
        f = MatchFeatures(bpm=78.0, detected_key='C', key_confidence=0.8,
                          chroma=CHROMA_C, duration_seconds=180.0)
        assert len(f.chroma) == 12

    def test_chroma_length_must_be_12(self):
        with pytest.raises(ValueError):
            MatchFeatures(bpm=78.0, detected_key='C', key_confidence=0.8,
                          chroma=(1.0, 0.0), duration_seconds=180.0)

    def test_bpm_negative_rejected(self):
        with pytest.raises(ValueError):
            MatchFeatures(bpm=-1.0, detected_key='C', key_confidence=0.8,
                          chroma=CHROMA_C, duration_seconds=180.0)

    def test_key_confidence_out_of_range_rejected(self):
        with pytest.raises(ValueError):
            MatchFeatures(bpm=78.0, detected_key='C', key_confidence=1.5,
                          chroma=CHROMA_C, duration_seconds=180.0)


class TestSongMatchProfile:
    """歌曲匹配特征 profile — frozen + chroma JSON 往返"""

    def test_frozen_immutable(self):
        p = SongMatchProfile(song_id='s1', bpm=78.0, key='C', chroma=CHROMA_C,
                             duration_seconds=180.0)
        with pytest.raises(FrozenInstanceError):
            p.bpm = 100.0  # type: ignore[misc]

    def test_defaults(self):
        p = SongMatchProfile(song_id='s1', bpm=78.0, key='C', chroma=CHROMA_C,
                             duration_seconds=180.0)
        assert p.feature_version == '1.0'
        assert p.updated_at == ''

    def test_empty_song_id_rejected(self):
        with pytest.raises(ValueError):
            SongMatchProfile(song_id='', bpm=78.0, key='C', chroma=CHROMA_C,
                             duration_seconds=180.0)

    def test_chroma_length_must_be_12(self):
        with pytest.raises(ValueError):
            SongMatchProfile(song_id='s1', bpm=78.0, key='C', chroma=(0.5,),
                             duration_seconds=180.0)

    def test_to_dict_from_dict_roundtrip(self):
        p = SongMatchProfile(song_id='s1', bpm=78.0, key='C', chroma=CHROMA_C,
                             duration_seconds=180.0, feature_version='1.0',
                             updated_at='2026-08-09T00:00:00+00:00')
        data = json.loads(json.dumps(p.to_dict()))  # 经 JSON 再重建
        rebuilt = SongMatchProfile.from_dict(data)
        assert rebuilt == p
        assert isinstance(rebuilt.chroma, tuple)
        assert len(rebuilt.chroma) == 12


class TestMatchCandidate:
    """匹配候选 — frozen + dict 序列化"""

    def test_to_dict(self):
        c = MatchCandidate(
            song_id='s1', title='月亮代表我的心', artist='邓丽君',
            confidence=0.94,
            factors={'bpm': 0.9, 'chroma': 0.95, 'key': 1.0, 'duration': 0.87},
            bpm_diff=1.5, key_diff_semitones=0, detected_key='C',
        )
        d = c.to_dict()
        assert d['song_id'] == 's1'
        assert d['confidence'] == 0.94
        assert d['factors']['chroma'] == 0.95


class TestMatchResult:
    """匹配结果聚合 — 默认值与无匹配状态"""

    def test_defaults_no_match(self):
        r = MatchResult(matched=False)
        assert r.matched_song is None
        assert r.candidates == ()
        assert r.fallback_reason == ''
        assert r.partial is False
        assert r.elapsed_ms == 0.0

    def test_no_match_construct(self):
        r = MatchResult(matched=False, fallback_reason='no_match')
        assert r.matched is False
        assert r.fallback_reason == 'no_match'
