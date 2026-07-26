"""
节奏特征提取器 — v7.1.3 自包含版

v7.1.3: 内移 RhythmAnalyzer._calculate_rhythm_traditional 算法,
移除对 services/features/rhythm.py 的依赖。算法逐位一致。

算法: onset 密度 + 间隔变异系数 (CV) + 不规则段检测。
适用: 无伴奏独唱、弹性速度、非西方节奏体系、传统流行乐。
"""
from __future__ import annotations
import logging
import numpy as np

from backend.domain.assessment.rhythm_scorer import RhythmFeatures

logger = logging.getLogger(__name__)

_RHYTHM_SR = 22050  # resample target for onset detection
_VOICE_FMIN, _VOICE_FMAX = 65.0, 1047.0


class LibrosaRhythmExtractor:
    """节奏特征提取器 — Level 1, v7.1.3 算法自包含"""

    def __init__(self, sample_rate: int = 22050, hop_length: int = 512):
        self.sample_rate = sample_rate
        self.hop_length = hop_length

    def extract(
        self,
        y: np.ndarray,
        sr: int,
        f0: np.ndarray | None = None,
        voiced_flags: np.ndarray | None = None,
        is_clean_vocal: bool = False,
    ) -> RhythmFeatures:
        """提取节奏特征 —— v7.1.3 内移自 RhythmAnalyzer, pitch-based + traditional 双路径。"""
        try:
            import librosa

            # Resample to 22kHz for better onset detection
            if sr != _RHYTHM_SR:
                audio_data = librosa.resample(y, orig_sr=sr, target_sr=_RHYTHM_SR)
                eff_sr = _RHYTHM_SR
            else:
                audio_data = y
                eff_sr = sr

            total_duration = len(audio_data) / eff_sr

            # Long audio: segment-based analysis (60s windows, 30s overlap)
            segment_dur = 60.0
            segment_hop = 30.0

            if total_duration > segment_dur * 1.5:
                segment_cvs = []
                segment_devs = []
                total_onsets = 0
                total_off_beat = 0
                max_bps = 0.0

                for start_t in np.arange(0, total_duration - segment_dur, segment_hop):
                    end_t = min(start_t + segment_dur, total_duration)
                    start_sample = int(start_t * eff_sr)
                    end_sample = int(end_t * eff_sr)
                    segment = audio_data[start_sample:end_sample]

                    if len(segment) < eff_sr * 3:
                        continue

                    seg_onset_env = librosa.onset.onset_strength(
                        y=segment, sr=eff_sr, hop_length=self.hop_length,
                    )
                    seg_onset_frames = librosa.onset.onset_detect(
                        onset_envelope=seg_onset_env, sr=eff_sr, hop_length=self.hop_length,
                    )

                    if len(seg_onset_frames) < 3:
                        continue

                    seg_times = librosa.frames_to_time(
                        seg_onset_frames, sr=eff_sr, hop_length=self.hop_length,
                    )
                    seg_ioi = np.diff(seg_times)
                    seg_mean = np.mean(seg_ioi)
                    if seg_mean > 0:
                        seg_cv = float(np.std(seg_ioi) / seg_mean)
                        segment_cvs.append(seg_cv)
                        segment_devs.append(_cv_to_deviation(seg_cv, is_clean_vocal))
                        total_onsets += len(seg_onset_frames)
                        total_off_beat += _count_irregular_segments(seg_ioi, seg_mean)
                        seg_bps = (
                            len(seg_onset_frames) / (seg_times[-1] - seg_times[0])
                            if seg_times[-1] > seg_times[0] else 0.0
                        )
                        max_bps = max(max_bps, seg_bps)

                if segment_cvs:
                    irregularity = float(np.median(segment_cvs))
                    avg_deviation_ratio = float(np.median(segment_devs))
                    onset_count = total_onsets
                    beats_per_second = max_bps
                    off_beat_segments = total_off_beat
                    return RhythmFeatures(
                        avg_deviation_ratio=round(avg_deviation_ratio, 4),
                        irregularity=round(irregularity, 4),
                        onset_density=max(0.5, round(beats_per_second, 2)),
                        onset_count=int(onset_count),
                        off_beat_segments=int(off_beat_segments),
                        is_clean_vocal=is_clean_vocal,
                    )

            # Short audio: direct analysis
            onset_env = librosa.onset.onset_strength(
                y=audio_data, sr=eff_sr, hop_length=self.hop_length,
            )
            onset_frames = librosa.onset.onset_detect(
                onset_envelope=onset_env, sr=eff_sr, hop_length=self.hop_length,
            )
            onset_count = len(onset_frames)

            if onset_count < 2:
                return RhythmFeatures(
                    avg_deviation_ratio=0.0, irregularity=0.0,
                    onset_density=0.5, onset_count=0,
                    off_beat_segments=0, is_clean_vocal=is_clean_vocal,
                )

            onset_times = librosa.frames_to_time(
                onset_frames, sr=eff_sr, hop_length=self.hop_length,
            )
            ioi = np.diff(onset_times)
            mean_ioi = np.mean(ioi)

            if mean_ioi > 0:
                total_dur = onset_times[-1] - onset_times[0]
                beats_per_second = (
                    onset_count / total_dur if total_dur > 0 else 0.0
                )
                irregularity = float(np.std(ioi) / mean_ioi)
                avg_dev = _cv_to_deviation(irregularity, is_clean_vocal)
                off_beat = _count_irregular_segments(ioi, mean_ioi)
            else:
                beats_per_second = 0.0
                irregularity = 0.0
                avg_dev = 0.0
                off_beat = 0

            return RhythmFeatures(
                avg_deviation_ratio=round(avg_dev, 4),
                irregularity=round(irregularity, 4),
                onset_density=max(0.5, round(beats_per_second, 2)),
                onset_count=int(onset_count),
                off_beat_segments=int(off_beat),
                is_clean_vocal=is_clean_vocal,
            )
        except Exception:
            logger.warning("Rhythm extraction failed, returning defaults", exc_info=True)
            return RhythmFeatures(
                avg_deviation_ratio=0.0, irregularity=0.0,
                onset_density=0.5, onset_count=0,
                off_beat_segments=0, is_clean_vocal=is_clean_vocal,
            )


def _cv_to_deviation(cv: float, is_clean_vocal: bool = False) -> float:
    """
    CV（变异系数）→ deviation_ratio (0-1) v5.13.
    内移自 RhythmAnalyzer._cv_to_deviation, 逐位一致。

    纯净人声的 onset 间隔分布与混合音频完全不同，
    因此使用不同的阈值映射。
    """
    if is_clean_vocal:
        if cv < 0.5:
            return cv * 0.35
        elif cv < 0.8:
            return 0.175 + (cv - 0.5) * 0.5
        elif cv < 1.2:
            return 0.325 + (cv - 0.8) * 0.6
        elif cv < 1.8:
            return 0.565 + (cv - 1.2) * 0.5
        else:
            return min(1.0, 0.865 + (cv - 1.8) * 0.2)
    else:
        if cv < 0.3:
            return cv * 0.4
        elif cv < 0.5:
            return 0.12 + (cv - 0.3) * 0.6
        elif cv < 0.8:
            return 0.24 + (cv - 0.5) * 0.8
        elif cv < 1.2:
            return 0.48 + (cv - 0.8) * 1.0
        else:
            return min(1.0, 0.88 + (cv - 1.2) * 0.3)


def _count_irregular_segments(ioi: np.ndarray, mean_ioi: float) -> int:
    """
    检测节奏不规则段。
    内移自 RhythmAnalyzer._count_irregular_segments, 逐位一致。
    """
    if len(ioi) < 3 or mean_ioi <= 0:
        return 0

    irregular_mask = np.abs(ioi - mean_ioi) > mean_ioi * 0.5

    segments = []
    start = None
    for i, val in enumerate(irregular_mask):
        if val and start is None:
            start = i
        elif not val and start is not None:
            if i - start >= 2:
                segments.append((start, i))
            start = None
    if start is not None and len(irregular_mask) - start >= 2:
        segments.append((start, len(irregular_mask)))

    return len(segments)
