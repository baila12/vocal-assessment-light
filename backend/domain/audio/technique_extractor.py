"""
发声技术特征提取器 — v7.1.3 自包含版

v7.1.3: 内移 TechniqueAnalyzer 全部算法 (vibrato/slide/falsetto/staccato/legato),
移除对 services/features/technique.py 的依赖。算法逐位一致。

检测项目: 颤音、滑音、假声、断音、连音 → technique_score。
"""
from __future__ import annotations
import logging
import numpy as np

from backend.domain.assessment.technique_scorer import TechniqueFeatures
from backend.domain.audio.feature_types import AcousticFeatures

logger = logging.getLogger(__name__)

_VOICE_FMIN, _VOICE_FMAX = 65.0, 1047.0
_VIBRATO_RATE_MIN, _VIBRATO_RATE_MAX = 4.5, 8.0
_VIBRATO_EXTENT_MIN, _VIBRATO_EXTENT_MAX = 0.3, 1.5


class LibrosaTechniqueExtractor:
    """发声技术特征提取器 — Level 2, v7.1.3 算法自包含"""

    def __init__(self, sample_rate: int = 22050, hop_length: int = 512):
        self.sample_rate = sample_rate
        self.hop_length = hop_length

    def extract(
        self,
        y: np.ndarray,
        sr: int,
        acoustic: AcousticFeatures,
        f0: np.ndarray | None = None,
        onset_density: float | None = None,
    ) -> TechniqueFeatures:
        """提取发声技术特征 — 内移自 TechniqueAnalyzer + adapter 公式。"""
        import librosa

        hnr = float(getattr(acoustic, 'hnr', 15.0) or 15.0)
        cpp = float(getattr(acoustic, 'cpp', 1.0) or 1.0)
        tilt = float(getattr(acoustic, 'spectral_tilt', 0.0) or 0.0)

        vibrato_quality = 0.0
        vibrato_rate = 5.0
        technique_score = 0.0

        try:
            # Onset density
            if onset_density is None or onset_density <= 0:
                onset_density = self._compute_onset_density(y, sr)

            # Technique detection (vibrato + slides + falsetto + staccato + legato)
            if f0 is not None and len(f0) > 0:
                valid_mask = (~np.isnan(f0)) & (f0 > _VOICE_FMIN) & (f0 < _VOICE_FMAX)
                valid_f0 = f0[valid_mask]

                if len(valid_f0) >= 30:
                    vibrato_result = _detect_vibrato(valid_f0, self.sample_rate, self.hop_length)
                    vibrato_count = vibrato_result['count']
                    vibrato_rate = vibrato_result['rate']
                    vibrato_quality = vibrato_result['quality']

                    slide_count = _detect_slides(valid_f0)
                    falsetto_segments = _detect_falsetto(
                        y, self.sample_rate, self.hop_length
                    )
                    staccato_count = _detect_staccato(
                        y, self.sample_rate, self.hop_length
                    )
                    legato_quality = _detect_legato(
                        valid_f0, y, self.sample_rate, self.hop_length
                    )

                    # Composite technique score (same as TechniqueAnalyzer)
                    technique_score = 0.0
                    if vibrato_count > 0:
                        technique_score += min(40.0, vibrato_count * 8.0)
                        if vibrato_quality > 50:
                            technique_score += min(15.0, vibrato_quality / 7.0)
                    if slide_count > 0:
                        technique_score += min(15.0, slide_count * 5.0)
                    if falsetto_segments > 0:
                        technique_score += min(10.0, falsetto_segments * 3.0)
                    if staccato_count > 0:
                        technique_score += min(10.0, staccato_count * 3.0)
                    if legato_quality > 30:
                        technique_score += min(10.0, legato_quality / 10.0)
                    technique_score = min(100.0, technique_score)
        except Exception:
            logger.debug("Technique detection failed, using defaults")

        spectral_flux = technique_score / 20.0

        consonant_clarity = max(0.0, min(100.0, hnr * 2.0))
        hf_energy_ratio = max(0.0, min(1.0, cpp / 5.0))

        return TechniqueFeatures(
            onset_density=round(onset_density, 2),
            spectral_flux=round(spectral_flux, 4),
            consonant_clarity=round(consonant_clarity, 2),
            hnr_mean=round(hnr, 2),
            spectral_tilt=round(tilt, 2),
            hf_energy_ratio=round(hf_energy_ratio, 4),
            cpp_mean=round(cpp, 4),
            vibrato_quality=round(vibrato_quality, 2),
            vibrato_rate_avg=round(vibrato_rate, 4),
        )

    @staticmethod
    def _compute_onset_density(y: np.ndarray, sr: int) -> float:
        try:
            import librosa
            onset_frames = librosa.onset.onset_detect(
                y=y, sr=sr, hop_length=512, backtrack=True, delta=0.07,
            )
            duration = len(y) / max(1, sr)
            return len(onset_frames) / max(0.001, duration)
        except Exception:
            return 2.0


# ================================================================
# 子检测器 — 内移自 TechniqueAnalyzer, 逐位一致
# ================================================================

def _detect_vibrato(f0: np.ndarray, sample_rate: int, hop_length: int) -> dict:
    """检测颤音 — FFT-based vibrato detection"""
    from scipy.ndimage import uniform_filter1d

    result = {'count': 0, 'rate': 0.0, 'extent': 0.0, 'quality': 0.0}
    try:
        f0_semitones = 12 * np.log2(f0 / 440.0)
        window = min(20, len(f0_semitones) // 4)
        if window < 2:
            return result

        trend = uniform_filter1d(f0_semitones, window * 2)
        detrended = f0_semitones - trend

        fft_result = np.fft.fft(detrended)
        freqs = np.fft.fftfreq(len(detrended), d=hop_length / sample_rate)

        vibrato_mask = (np.abs(freqs) >= _VIBRATO_RATE_MIN) & (np.abs(freqs) <= _VIBRATO_RATE_MAX)

        if np.sum(vibrato_mask) > 0:
            power = np.abs(fft_result) ** 2
            vibrato_power = power.copy()
            vibrato_power[~vibrato_mask] = 0

            max_idx = np.argmax(vibrato_power)
            vibrato_rate = abs(freqs[max_idx])

            if vibrato_rate > 0:
                result['rate'] = round(vibrato_rate, 2)
                vibrato_extent = np.std(detrended) * 2
                result['extent'] = round(vibrato_extent, 2)
                result['count'] = _count_vibrato_segments(
                    detrended, vibrato_rate, sample_rate, hop_length,
                )

                quality = 100.0
                if not (_VIBRATO_RATE_MIN <= vibrato_rate <= _VIBRATO_RATE_MAX):
                    quality -= 20
                if not (_VIBRATO_EXTENT_MIN <= vibrato_extent <= _VIBRATO_EXTENT_MAX):
                    quality -= 20
                result['quality'] = max(0.0, quality)
    except Exception:
        logger.debug("vibrato detection failed, returning defaults", exc_info=True)
    return result


def _count_vibrato_segments(
    detrended: np.ndarray, vibrato_rate: float,
    sample_rate: int, hop_length: int,
) -> int:
    from scipy.ndimage import uniform_filter1d

    if vibrato_rate < _VIBRATO_RATE_MIN:
        return 0
    frames_per_cycle = sample_rate / (hop_length * vibrato_rate)
    window_size = max(4, int(frames_per_cycle * 2))
    energy = uniform_filter1d(detrended ** 2, window_size)
    threshold = np.mean(energy) * 1.5
    above_threshold = energy > threshold

    count = 0
    in_segment = False
    min_frames = int(frames_per_cycle)
    segment_start = 0
    for i, val in enumerate(above_threshold):
        if val and not in_segment:
            in_segment = True
            segment_start = i
        elif not val and in_segment:
            if i - segment_start >= min_frames:
                count += 1
            in_segment = False
    return count


def _detect_slides(f0: np.ndarray) -> int:
    try:
        f0_diff = np.diff(np.log(f0))
        is_sliding = np.abs(f0_diff) > 0.02
        count = 0
        consecutive = 0
        for val in is_sliding:
            if val:
                consecutive += 1
            else:
                if consecutive >= 5:
                    count += 1
                consecutive = 0
        return count
    except Exception:
        return 0


def _detect_falsetto(audio_data: np.ndarray, sample_rate: int, hop_length: int) -> int:
    import librosa
    try:
        segment_length = int(sample_rate * 0.5)
        num_segments = len(audio_data) // segment_length
        falsetto_count = 0
        for i in range(num_segments):
            start = i * segment_length
            end = start + segment_length
            segment = audio_data[start:end]
            centroid = librosa.feature.spectral_centroid(y=segment, sr=sample_rate)[0]
            if np.mean(centroid) > 3500:
                falsetto_count += 1
        return falsetto_count
    except Exception:
        return 0


def _detect_staccato(audio_data: np.ndarray, sample_rate: int, hop_length: int) -> int:
    import librosa
    try:
        rms = librosa.feature.rms(y=audio_data, frame_length=1024, hop_length=hop_length)[0]
        rms_mean = np.mean(rms[rms > 0])
        if rms_mean <= 0:
            return 0
        peaks_mask = rms > rms_mean * 1.5
        max_pulse_frames = int(0.3 * sample_rate / hop_length)

        staccato_count = 0
        in_peak = False
        peak_start = 0
        for i, is_peak in enumerate(peaks_mask):
            if is_peak and not in_peak:
                in_peak = True
                peak_start = i
            elif not is_peak and in_peak:
                if i - peak_start <= max_pulse_frames:
                    staccato_count += 1
                in_peak = False
        if in_peak and len(peaks_mask) - peak_start <= max_pulse_frames:
            staccato_count += 1
        return staccato_count
    except Exception:
        return 0


def _detect_legato(
    f0: np.ndarray, audio_data: np.ndarray,
    sample_rate: int, hop_length: int,
) -> float:
    import librosa
    try:
        rms = librosa.feature.rms(y=audio_data, frame_length=1024, hop_length=hop_length)[0]
        rms_mean = np.mean(rms[rms > 0])
        if rms_mean <= 0:
            return 0.0

        rms_baseline = rms_mean * 0.2
        silence_mask = rms < rms_baseline
        silent_gaps = []
        gap_start = None
        for i, is_silent in enumerate(silence_mask):
            if is_silent and gap_start is None:
                gap_start = i
            elif not is_silent and gap_start is not None:
                silent_gaps.append(i - gap_start)
                gap_start = None
        if gap_start is not None:
            silent_gaps.append(len(silence_mask) - gap_start)

        if silent_gaps:
            silence_score = max(0.0, 100.0 - min(50.0, np.mean(silent_gaps) * 5))
        else:
            silence_score = 100.0

        if f0 is not None and len(f0) > 20:
            valid_f0 = f0[(~np.isnan(f0)) & (f0 > 65) & (f0 < 1047)]
            if len(valid_f0) > 20:
                f0_diffs = np.abs(np.diff(valid_f0))
                small_changes = np.sum(f0_diffs < 1.0)
                large_jumps = np.sum(f0_diffs > 10.0)
                smoothness_ratio = small_changes / max(len(f0_diffs), 1)
                pitch_score = max(0.0, smoothness_ratio * 100 - min(40.0, large_jumps * 5))
            else:
                pitch_score = 50.0
        else:
            pitch_score = 50.0

        return max(0.0, min(100.0, silence_score * 0.60 + pitch_score * 0.40))
    except Exception:
        return 0.0
