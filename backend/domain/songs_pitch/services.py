"""
歌曲音高提取服务 — v7.13 参考音高

从歌曲 WAV 文件提取 F0 曲线, 返回 SongPitchCurve 值对象。
纯函数式领域服务 (仅依赖 librosa/numpy, 无项目层依赖)。
"""

from __future__ import annotations

import numpy as np

from backend.domain.songs_pitch.value_objects import SongPitchCurve

TARGET_SR = 16000


class PitchExtractionService:
    """F0 提取领域服务 — 无副作用纯函数"""

    @staticmethod
    def extract(
        wav_path: str,
        song_id: str,
        *,
        fmin: float = 65.0,
        fmax: float = 1047.0,
        hop_length: int = 512,
    ) -> SongPitchCurve:
        """WAV 文件 → SongPitchCurve (librosa.yin, NaN→0.0)"""
        import librosa

        y, sr = librosa.load(wav_path, sr=None, mono=True)
        if sr != TARGET_SR:
            y = librosa.resample(y, orig_sr=sr, target_sr=TARGET_SR)
            sr = TARGET_SR

        f0 = librosa.yin(y, fmin=fmin, fmax=fmax, sr=sr, hop_length=hop_length)
        times = librosa.times_like(f0, sr=sr, hop_length=hop_length)
        confidence = (~np.isnan(f0)).astype(float)

        return SongPitchCurve(
            song_id=song_id,
            frequencies=tuple(float(np.nan_to_num(v, nan=0.0)) for v in f0),
            times=tuple(float(t) for t in times),
            confidence=tuple(float(c) for c in confidence),
            sample_rate=sr,
            hop_length=hop_length,
        )
