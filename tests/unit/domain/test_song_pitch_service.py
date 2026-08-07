"""
歌曲音高提取服务测试 — v7.13 参考音高

PitchExtractionService.extract(): WAV 文件 → SongPitchCurve (librosa.yin)
"""

import wave
import struct
import numpy as np
import pytest

from backend.domain.songs_pitch.value_objects import SongPitchCurve
from backend.domain.songs_pitch.services import PitchExtractionService


def _write_sine_wav(path, duration_s=1.0, sr=16000, freq=440.0):
    """写入最小正弦波 WAV (16-bit PCM mono)"""
    n = int(sr * duration_s)
    t = np.linspace(0, duration_s, n, endpoint=False)
    samples = (np.sin(2 * np.pi * freq * t) * 0.5 * 32767).astype(np.int16)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(samples.tobytes())


class TestPitchExtractionService:
    """PitchExtractionService — WAV → SongPitchCurve"""

    def test_extract_returns_song_pitch_curve(self, tmp_path):
        """440Hz 正弦波 → 返回 SongPitchCurve, 帧数 > 0"""
        wav = tmp_path / 'sine.wav'
        _write_sine_wav(wav, duration_s=1.0, freq=440.0)

        curve = PitchExtractionService.extract(str(wav), song_id='moon_love')

        assert isinstance(curve, SongPitchCurve)
        assert curve.song_id == 'moon_love'
        assert curve.frame_count > 0
        assert curve.sample_rate == 16000
        assert curve.hop_length == 512

    def test_extract_duration_matches_audio(self, tmp_path):
        """1s 音频 → duration ≈ 1s"""
        wav = tmp_path / 'sine.wav'
        _write_sine_wav(wav, duration_s=1.0)

        curve = PitchExtractionService.extract(str(wav), song_id='moon_love')

        assert curve.duration_seconds == pytest.approx(1.0, abs=0.1)

    def test_extract_detects_sine_frequency(self, tmp_path):
        """正弦波 → 检出帧大多接近 440Hz (非零频率占比高)"""
        wav = tmp_path / 'sine.wav'
        _write_sine_wav(wav, duration_s=1.0, freq=440.0)

        curve = PitchExtractionService.extract(str(wav), song_id='moon_love')

        voiced = [f for f in curve.frequencies if f > 0]
        assert len(voiced) / max(curve.frame_count, 1) > 0.5

    def test_extract_missing_file_raises(self, tmp_path):
        """不存在的文件 → 抛出异常 (不静默)"""
        with pytest.raises(Exception):
            PitchExtractionService.extract(str(tmp_path / 'nope.wav'), song_id='moon_love')
