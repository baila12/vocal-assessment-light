"""
匹配特征提取服务 — v7.14 上传音频自动匹配标准歌曲

从音频信号 (y, sr) 提取 MatchFeatures: BPM / 平均 chroma / K-S 调性检测。
纯函数式领域服务 (仅依赖 librosa/numpy), 与 songs_pitch/services.py 风格一致。
对静音/短音频/噪声容错, 绝不抛出影响整体评分流程的异常。
"""

from __future__ import annotations

import numpy as np

from backend.domain.song_match.services import KeyDetector
from backend.domain.song_match.value_objects import CHROMA_BINS, MatchFeatures

DEFAULT_SR = 22050
HOP_LENGTH = 512


class MatchFeatureExtractor:
    """匹配特征提取领域服务 — 无副作用纯函数"""

    @staticmethod
    def extract(y, sr: int = DEFAULT_SR, *, hop_length: int = HOP_LENGTH) -> MatchFeatures:
        """音频信号 → MatchFeatures

        Args:
            y: 单声道音频样本 (np.ndarray / list)
            sr: 采样率
            hop_length: STFT 帧移 (影响 chroma 分辨率)

        Returns:
            MatchFeatures — bpm(检测失败=0.0), 平均 chroma (峰值归一化),
            K-S 检测调性与置信度, 时长秒数。
        """
        import librosa

        y = np.asarray(y, dtype=np.float32)
        duration = len(y) / float(sr)
        if duration <= 0.0:
            return MatchFeatures(
                bpm=0.0, detected_key='C', key_confidence=0.0,
                chroma=(0.0,) * CHROMA_BINS, duration_seconds=0.0,
            )

        # BPM — librosa 0.10+ 返回 (tempo, beats), tempo 可能为数组; NaN→0.0
        try:
            tempo = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop_length)
            if isinstance(tempo, tuple):
                tempo = tempo[0]
            bpm = float(np.atleast_1d(tempo)[0])
            if not np.isfinite(bpm) or bpm < 0.0:
                bpm = 0.0
        except (ValueError, IndexError, TypeError):
            bpm = 0.0  # 超短/静音信号无法可靠估计节拍

        # 平均 chroma — 12-bin, 峰值归一化保留相对形状 (全零保持全零)
        chroma_mat = librosa.feature.chroma_stft(y=y, sr=sr, hop_length=hop_length)
        chroma = chroma_mat.mean(axis=1)
        peak = float(chroma.max()) if chroma.size else 0.0
        if peak > 0.0:
            chroma = chroma / peak
        else:
            chroma = np.zeros(CHROMA_BINS)

        detected_key, key_conf = KeyDetector.detect(tuple(float(v) for v in chroma))
        return MatchFeatures(
            bpm=bpm,
            detected_key=detected_key,
            key_confidence=float(key_conf),
            chroma=tuple(float(v) for v in chroma),
            duration_seconds=duration,
        )
