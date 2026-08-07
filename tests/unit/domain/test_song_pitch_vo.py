"""
歌曲音高曲线值对象测试 — v7.13 选歌录音参考音高

SongPitchCurve: 标准歌曲 F0 曲线 (frozen dataclass), 参考线叠加的数据源。
"""

import math
import pytest
from dataclasses import FrozenInstanceError

from backend.domain.songs_pitch.value_objects import SongPitchCurve


class TestSongPitchCurve:
    """SongPitchCurve 值对象 — 不可变 + 序列化"""

    def test_defaults(self):
        """默认 sample_rate/hop_length"""
        curve = SongPitchCurve(
            song_id='moon_love',
            frequencies=(261.6, 293.7),
            times=(0.0, 0.032),
            confidence=(0.9, 0.8),
        )
        assert curve.sample_rate == 16000
        assert curve.hop_length == 512

    def test_frozen_immutable(self):
        """frozen dataclass 不可修改"""
        curve = SongPitchCurve(
            song_id='moon_love',
            frequencies=(261.6,),
            times=(0.0,),
            confidence=(0.9,),
        )
        with pytest.raises(FrozenInstanceError):
            curve.song_id = 'other'

    def test_frame_count_and_duration(self):
        """frame_count = 帧数; duration_seconds = 末帧时间"""
        curve = SongPitchCurve(
            song_id='moon_love',
            frequencies=(261.6, 293.7, 329.6),
            times=(0.0, 0.032, 0.064),
            confidence=(0.9, 0.8, 0.7),
        )
        assert curve.frame_count == 3
        assert curve.duration_seconds == pytest.approx(0.064)

    def test_empty_curve_duration_zero(self):
        """空曲线 duration = 0"""
        curve = SongPitchCurve(
            song_id='moon_love',
            frequencies=(),
            times=(),
            confidence=(),
        )
        assert curve.duration_seconds == 0.0
        assert curve.frame_count == 0

    def test_rejects_mismatched_lengths(self):
        """frequencies/times/confidence 长度不一致 → ValueError"""
        with pytest.raises(ValueError, match='长度必须一致'):
            SongPitchCurve(
                song_id='moon_love',
                frequencies=(261.6, 293.7),
                times=(0.0,),
                confidence=(0.9, 0.8),
            )

    def test_normalizes_nan_frequency_to_zero(self):
        """NaN 频率在构造时归一化为 0.0 (JSON 兼容)"""
        curve = SongPitchCurve(
            song_id='moon_love',
            frequencies=(float('nan'), 293.7),
            times=(0.0, 0.032),
            confidence=(0.1, 0.8),
        )
        assert curve.frequencies[0] == 0.0
        assert math.isnan(curve.frequencies[0]) is False

    def test_to_dict_from_dict_round_trip(self):
        """to_dict/from_dict 往返一致 (JSON 兼容)"""
        original = SongPitchCurve(
            song_id='moon_love',
            frequencies=(261.6, 293.7),
            times=(0.0, 0.032),
            confidence=(0.9, 0.8),
        )
        data = original.to_dict()
        assert isinstance(data['frequencies'], list)
        restored = SongPitchCurve.from_dict(data)
        assert restored == original

    def test_from_dict_missing_song_id_raises(self):
        """from_dict 缺 song_id → ValueError"""
        with pytest.raises(ValueError, match='song_id'):
            SongPitchCurve.from_dict(
                {'frequencies': [1.0], 'times': [0.0], 'confidence': [1.0]}
            )
