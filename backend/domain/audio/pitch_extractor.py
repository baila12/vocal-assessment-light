"""
音准特征提取器 — v7.1.3 自包含版

v7.1.3: 内移 PitchAnalyzer.calculate_pitch_deviation_cents 算法,
移除对 services/features/pitch.py 的依赖。算法逐位一致。

多指标体系 (v5.14, 移植自 pitch-benchmark):
  - MAE cents: 平均绝对音分偏差
  - RPA: Raw Pitch Accuracy
  - RCA: Raw Chroma Accuracy (octave-folded)
  - Gross Error Rate: >200 cents
  - Octave Error Rate: 相邻帧跳变检测
  - Relative Smoothness: 音高平滑度
  - Pitch Breaks: 连续有声帧间音高断层
"""
from __future__ import annotations
import logging
import numpy as np
from scipy.ndimage import uniform_filter1d, find_objects, label

from backend.domain.assessment.pitch_scorer import PitchFeatures

logger = logging.getLogger(__name__)

VOICE_FMIN = 65.0
VOICE_FMAX = 1047.0


class LibrosaPitchExtractor:
    """音准特征提取器 — Level 1, v7.1.3 算法自包含"""

    def __init__(self, sample_rate: int = 22050, hop_length: int = 256):
        self.sample_rate = sample_rate
        self.hop_length = hop_length

    def extract(
        self,
        y: np.ndarray,  # unused, kept for interface consistency
        sr: int,
        f0: np.ndarray,
        voiced_flags: np.ndarray,
    ) -> PitchFeatures:
        """提取音准特征 —— v7.1.3 内移自 PitchAnalyzer, 与旧路径完全一致。"""
        if f0 is None or len(f0) == 0:
            return PitchFeatures(
                mae_cents=0.0, rpa=0.0, rca=0.0,
                gross_error_rate=0.0, octave_error_rate=0.0,
                relative_smoothness=1.0, detection_rate=0.0,
                pitch_breaks=0, valid_frame_count=1, pitch_wobble=0.0,
            )

        if voiced_flags is None:
            voiced_flags = ~np.isnan(f0)

        try:
            valid_mask = voiced_flags & (f0 > VOICE_FMIN) & (f0 < VOICE_FMAX)
            valid_f0 = f0[valid_mask]

            if len(valid_f0) < 10:
                return PitchFeatures(
                    mae_cents=0.0, rpa=0.0, rca=0.0,
                    gross_error_rate=0.0, octave_error_rate=0.0,
                    relative_smoothness=1.0, detection_rate=0.0,
                    pitch_breaks=0, valid_frame_count=1, pitch_wobble=0.0,
                )

            valid_frame_count = len(valid_f0)
            detection_rate = valid_frame_count / len(f0)

            # === MIDI cents deviation ===
            midi_notes = 12 * np.log2(valid_f0 / 440.0) + 69
            nearest_midi = np.round(midi_notes)
            cents_deviation = (midi_notes - nearest_midi) * 100

            mae_cents = float(np.mean(np.abs(cents_deviation)))

            # === Consecutive off-note detection ===
            half_note_threshold = 50
            off_notes = np.abs(cents_deviation) > half_note_threshold
            consecutive_count = 0
            max_consecutive = 0
            for is_off in off_notes:
                if is_off:
                    consecutive_count += 1
                    max_consecutive = max(max_consecutive, consecutive_count)
                else:
                    consecutive_count = 0

            # === Pitch breaks (v6.2: only consecutive voiced frames) ===
            pitch_breaks = 0
            if len(valid_f0) > 10:
                voiced_in_full = ~np.isnan(f0) & (f0 > VOICE_FMIN) & (f0 < VOICE_FMAX)
                voiced_indices = np.where(voiced_in_full)[0]
                if len(voiced_indices) > 1:
                    consecutive_mask = np.diff(voiced_indices) == 1
                    consecutive_starts = voiced_indices[:-1][consecutive_mask]
                    consecutive_ends = voiced_indices[1:][consecutive_mask]
                    if len(consecutive_starts) > 0:
                        f0_starts = f0[consecutive_starts]
                        f0_ends = f0[consecutive_ends]
                        cents_starts = 1200 * np.log2(f0_starts / 440.0)
                        cents_ends = 1200 * np.log2(f0_ends / 440.0)
                        cents_jumps = np.abs(cents_ends - cents_starts)
                        is_octave_jump = (cents_jumps > 1000) & (cents_jumps < 1400)
                        real_breaks = (cents_jumps > 200) & ~is_octave_jump
                        pitch_breaks = int(np.sum(real_breaks))

            # === Pitch wobble (long-note pitch fluctuation) ===
            window_size = int(self.sample_rate / self.hop_length * 0.5)
            if len(cents_deviation) > window_size:
                windowed_std = uniform_filter1d(cents_deviation ** 2, window_size) ** 0.5
                pitch_wobble = float(np.max(windowed_std))
            else:
                pitch_wobble = 0.0

            # === Multimetric (RPA, RCA, gross_error, octave_error, smoothness) ===
            (
                rpa, rca, gross_error_rate, octave_error_rate, relative_smoothness,
            ) = self._calc_multimetric(cents_deviation, valid_f0, voiced_flags)

            return PitchFeatures(
                mae_cents=round(mae_cents, 2),
                rpa=round(rpa, 4),
                rca=round(rca, 4),
                gross_error_rate=round(gross_error_rate, 4),
                octave_error_rate=round(octave_error_rate, 4),
                relative_smoothness=round(relative_smoothness, 4),
                detection_rate=round(detection_rate, 4),
                pitch_breaks=pitch_breaks,
                valid_frame_count=max(1, valid_frame_count),
                pitch_wobble=round(pitch_wobble, 2),
            )
        except Exception:
            logger.warning("Pitch extraction failed, returning defaults", exc_info=True)
            return PitchFeatures(
                mae_cents=0.0, rpa=0.0, rca=0.0,
                gross_error_rate=0.0, octave_error_rate=0.0,
                relative_smoothness=1.0, detection_rate=0.0,
                pitch_breaks=0, valid_frame_count=1, pitch_wobble=0.0,
            )

    @staticmethod
    def _calc_multimetric(
        cents_deviation: np.ndarray,
        valid_f0: np.ndarray,
        voiced_flags: np.ndarray,
    ) -> tuple:
        """
        v5.14 多指标音准评估 — 内移自 PitchAnalyzer._calculate_pitch_multimetric.
        逐位一致, 无副作用。
        """
        epsilon = 50.0
        gross_threshold = 200.0

        # RPA: Raw Pitch Accuracy
        rpa = float(np.nanmean(np.abs(cents_deviation) < epsilon))

        # RCA: Raw Chroma Accuracy (octave-folded)
        wrapped_cents = np.abs(cents_deviation) % 1200
        chroma_diff = np.minimum(wrapped_cents, 1200 - wrapped_cents)
        rca = float(np.nanmean(chroma_diff < epsilon))

        # Gross Error Rate
        gross_error_rate = float(np.nanmean(np.abs(cents_deviation) > gross_threshold))

        # Octave Error Rate
        valid_diff = np.abs(np.diff(valid_f0))
        relative_jumps = valid_diff / (valid_f0[:-1] + np.finfo(float).eps)
        near_octave_jumps = (relative_jumps > 0.7) & (relative_jumps < 1.3)
        octave_error_rate = (
            float(np.nanmean(near_octave_jumps))
            if len(near_octave_jumps) > 0 else 0.0
        )

        # Relative Smoothness
        relative_smoothness = 0.0
        if len(valid_f0) >= 2:
            pitch_starts = valid_f0[:-1]
            pitch_ends = valid_f0[1:]
            valid_pairs = (pitch_starts > 0) & (pitch_ends > 0)
            if np.any(valid_pairs):
                starts = pitch_starts[valid_pairs]
                ends = pitch_ends[valid_pairs]
                rel_changes = np.abs(ends - starts) / (starts + 1e-8)
                mean_chg = np.mean(rel_changes)
                std_chg = np.std(rel_changes)
                if mean_chg > 1e-9:
                    relative_smoothness = float(std_chg / mean_chg)

        return (rpa, rca, gross_error_rate, octave_error_rate, relative_smoothness)
