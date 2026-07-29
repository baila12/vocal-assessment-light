"""
气息特征提取器 — v7.1.3 自包含版

v7.1.3: 内移 BreathAnalyzer 全部算法 (8 个子评估器),
移除对 services/features/breath.py 的依赖。算法逐位一致。

评估体系 (v4.1): 长音支撑(40%) + 动态控制(25%) + 气口设计(20%) + 气声技巧(15%)
"""
from __future__ import annotations
import logging
import numpy as np
from scipy.ndimage import uniform_filter1d
from scipy import signal

from backend.domain.assessment.breath_scorer import BreathFeatures
from backend.domain.audio.feature_types import AcousticFeatures

logger = logging.getLogger(__name__)


class LibrosaBreathExtractor:
    """气息特征提取器 — Level 2, v7.1.3 算法自包含"""

    def __init__(self, sample_rate: int = 22050, hop_length: int = 512):
        self.sample_rate = sample_rate
        self.hop_length = hop_length

    def extract(
        self,
        y: np.ndarray,
        sr: int,
        acoustic: AcousticFeatures,
        f0: np.ndarray | None = None,
        is_clean_vocal: bool = False,
        singing_style: str = "pop",
    ) -> BreathFeatures:
        """
        提取气息特征 — v7.1.3 内移自 BreathAnalyzer, 与旧路径完全一致。
        """
        import librosa

        n_samples = len(y)
        if n_samples < sr * 0.1:
            return BreathFeatures(is_clean_vocal=is_clean_vocal)

        try:
            # Re-init if SR changed
            if sr != self.sample_rate:
                self.sample_rate = sr

            # Filter to vocal segments
            breath_audio = y
            if f0 is not None and len(f0) > 0:
                try:
                    from backend.domain.audio.audio_utils import (
                        find_vocal_segments, filter_audio_to_vocal_segments,
                    )
                    segments = find_vocal_segments(f0, self.hop_length, sr)
                    if segments:
                        breath_audio = filter_audio_to_vocal_segments(y, segments, self.hop_length)
                except Exception:
                    logger.debug("vocal segment filter failed, using raw audio", exc_info=True)

            hnr = float(getattr(acoustic, 'hnr', 0.0) or 0.0)

            # ---- 计算 RMS ----
            rms = librosa.feature.rms(y=breath_audio, frame_length=2048, hop_length=self.hop_length)[0]
            valid_rms = rms[rms > 0]
            if len(valid_rms) < 10:
                return BreathFeatures(is_clean_vocal=is_clean_vocal)

            rms_mean = np.mean(valid_rms)
            rms_std = np.std(valid_rms)
            rms_fluctuation = float(rms_std / rms_mean) if rms_mean > 0 else 0.0

            # Dynamic range (p95/p5)
            if len(valid_rms) > 20:
                p95, p5 = np.percentile(valid_rms, 95), np.percentile(valid_rms, 5)
                dynamic_range = float(20 * np.log10(p95 / p5)) if p5 > 1e-10 else 0.0
            else:
                dynamic_range = 0.0

            voiced_flags = ~np.isnan(f0) if f0 is not None else np.array([])

            # Artistic fluctuation (v7.6: 连续化)
            is_artistic = _detect_artistic_fluctuation(rms, f0, voiced_flags)
            artistic_fluctuation = _calc_artistic_fluctuation_score(rms, f0, voiced_flags)

            # Sub-evaluators
            long_note_support, long_note_count, pitch_stability_long, harmonic_stability, long_note_avg_quality = _eval_long_note_support(
                breath_audio, rms, f0, self.hop_length, self.sample_rate,
            )
            dynamic_control, soft_segment_count, soft_singing_quality, crescendo_quality = _eval_dynamic_control(
                rms,
            )
            breath_design, clean_breath_count, phrase_coherence = _eval_breath_design(rms)
            breath_technique, controlled_breathiness, uncontrolled_leak = _eval_breath_technique(
                hnr, breath_audio, singing_style,
            )

            # Professional breath score
            professional_breath_score = _calc_professional_breath_score(
                long_note_support, dynamic_control, breath_design, breath_technique,
                is_artistic, rms_fluctuation, long_note_count, clean_breath_count,
            )

            # Long note decay
            long_note_decay = _calc_long_note_decay(rms, rms_mean)

            # Breath breaks
            rms_diff = np.diff(rms)
            breath_breaks = int(np.sum(rms_diff < -rms_mean * 0.8))

            return BreathFeatures(
                professional_breath_score=round(professional_breath_score, 2),
                long_note_support=round(long_note_support, 2),
                dynamic_control=round(dynamic_control, 2),
                breath_design=round(breath_design, 2),
                breath_technique=round(breath_technique, 2),
                rms_fluctuation=round(rms_fluctuation, 4),
                is_artistic_fluctuation=is_artistic,
                artistic_fluctuation_score=round(artistic_fluctuation, 2),  # v7.6: 连续化
                controlled_breathiness=round(controlled_breathiness, 2),
                uncontrolled_leak=round(uncontrolled_leak, 2),
                breath_breaks=breath_breaks,
                long_note_count=long_note_count,
                soft_segment_count=soft_segment_count,
                soft_singing_quality=round(soft_singing_quality, 2),
                clean_breath_count=clean_breath_count,
                dynamic_range=round(dynamic_range, 2),
                phrase_coherence=round(phrase_coherence, 2),
                crescendo_quality=round(crescendo_quality, 2),
                long_note_decay=round(long_note_decay, 4),
                pitch_stability_long=round(pitch_stability_long, 2),
                harmonic_stability=round(harmonic_stability, 2),
                is_clean_vocal=is_clean_vocal,
            )
        except Exception:
            logger.warning("Breath extraction failed, returning defaults", exc_info=True)
            return BreathFeatures(is_clean_vocal=is_clean_vocal)


# ================================================================
# 子评估器 — 内移自 BreathAnalyzer, 逐位一致
# ================================================================

def _find_continuous_segments(mask: np.ndarray) -> list:
    segments = []
    start = None
    for i, val in enumerate(mask):
        if val and start is None:
            start = i
        elif not val and start is not None:
            segments.append((start, i))
            start = None
    if start is not None:
        segments.append((start, len(mask)))
    return segments


def _detect_artistic_fluctuation(rms, f0, voiced_flags) -> bool:
    """向后兼容: 保留旧布尔函数, 委托给 _calc_artistic_fluctuation_score()。

    v7.6: 内部调用连续化函数, 分数 > 20 视为 True。
    """
    score = _calc_artistic_fluctuation_score(rms, f0, voiced_flags)
    return score > 20.0


def _calc_artistic_fluctuation_score(rms, f0, voiced_flags) -> float:
    """计算艺术性波动分数 (0-100, 连续) — v7.6 P1-3 修复

    综合两个信息源:
    1. RMS 周期性: 自相关峰值数量和质量 → 0-50 分
    2. F0-RMS 耦合: 相关系数 → 0-50 分

    替代旧布尔函数 (阈值过低 + 无条件 +30 导致区分度低)。
    """
    try:
        score = 0.0

        # === 1. RMS 周期性 (0-50) ===
        rms_norm = (rms - np.mean(rms)) / (np.std(rms) + 1e-10)
        autocorr = np.correlate(rms_norm, rms_norm, mode='full')
        autocorr = autocorr[len(autocorr)//2:]
        if len(autocorr) > 50:
            # 用高度阈值 (0.15) 过滤噪声, 而非 prominence (纯周期信号峰等高 → prominence=0)
            peaks, properties = signal.find_peaks(autocorr[1:50], height=0.15)
            if len(peaks) >= 2:
                # 峰值数量映射: 2→25, 4→40, 6+→50
                peak_score = min(50.0, 25.0 + (len(peaks) - 2) * 6.25)
                # 峰值显著性加成 (噪声会有高 prominence, 但也被 height 过滤了)
                if properties is not None and 'prominences' in properties:
                    prom = np.asarray(properties['prominences'])
                    if len(prom) > 0:
                        avg_prominence = float(np.mean(prom))
                        # prominence 高 → 确信是真实周期性 → 小幅加成 (最多 10%)
                        bonus = min(0.10, avg_prominence * 0.05)
                        peak_score = min(50.0, peak_score * (1.0 + bonus))
                score += peak_score

        # === 2. F0-RMS 耦合 (0-50) ===
        if f0 is not None and len(f0) > 0:
            valid_f0 = f0[voiced_flags] if len(voiced_flags) > 0 else f0[~np.isnan(f0)]
            if len(valid_f0) > 50 and len(rms) > 50:
                ml = min(len(valid_f0), len(rms))
                if np.std(valid_f0[:ml]) > 0 and np.std(rms[:ml]) > 0:
                    corr = np.corrcoef(valid_f0[:ml], rms[:ml])[0, 1]
                    if not np.isnan(corr) and corr > 0:
                        # 相关系数映射: 0→0, 0.3→21, 0.5→36, 0.7+→50
                        corr_score = min(50.0, corr * 50.0 / 0.70)
                        score += corr_score

        return min(100.0, score)
    except Exception:
        return 0.0


def _eval_long_note_support(audio_data, rms, f0, hop_length, sample_rate):
    import librosa
    try:
        frame_duration = hop_length / sample_rate
        min_frames = int(3.0 / frame_duration)
        rms_mean = np.mean(rms[rms > 0])
        segments = _find_continuous_segments(rms > rms_mean * 0.5)

        long_notes = []
        pitch_stabilities = []
        harmonic_stabilities = []

        for start, end in segments:
            if end - start >= min_frames:
                long_notes.append((start, end, end - start))
                if f0 is not None and len(f0) > end:
                    seg_f0 = f0[start:end]
                    valid = seg_f0[~np.isnan(seg_f0)]
                    if len(valid) > 10:
                        midi = 12 * np.log2(valid / 440.0) + 69
                        cents_std = np.std(midi - np.round(midi)) * 100
                        pitch_stabilities.append(max(0.0, 100.0 - cents_std * 2))
                seg_audio = audio_data[start * hop_length:end * hop_length]
                if len(seg_audio) > 2048:
                    centroid = librosa.feature.spectral_centroid(y=seg_audio, sr=sample_rate)[0]
                    cv = np.std(centroid) / (np.mean(centroid) + 1e-10)
                    harmonic_stabilities.append(max(0.0, 100.0 - cv * 50))

        long_note_count = len(long_notes)
        pitch_stability_long = float(np.mean(pitch_stabilities)) if pitch_stabilities else 0.0
        harmonic_stability = float(np.mean(harmonic_stabilities)) if harmonic_stabilities else 0.0
        long_note_avg_quality = (pitch_stability_long + harmonic_stability) / 2 if long_notes else 0.0

        score = 0.0
        if pitch_stability_long > 0:
            score += pitch_stability_long * 0.40
        if harmonic_stability > 0:
            score += harmonic_stability * 0.30
        total_dur = sum(df * frame_duration for _, _, df in long_notes)
        score += min(30.0, total_dur * 2.0)
        long_note_support = max(0.0, min(100.0, score))
        return long_note_support, long_note_count, pitch_stability_long, harmonic_stability, long_note_avg_quality
    except Exception:
        return 0.0, 0, 0.0, 0.0, 0.0


def _eval_dynamic_control(rms):
    try:
        rms_mean = np.mean(rms[rms > 0])
        soft_mask = (rms > np.percentile(rms[rms > 0], 10)) & (rms < rms_mean * 0.6)
        soft_segments = _find_continuous_segments(soft_mask)
        soft_count = len(soft_segments)

        soft_qualities = []
        for s, e in soft_segments:
            if e - s >= 10:
                seg_rms = rms[s:e]
                stability = 100.0 - np.std(seg_rms) / (np.mean(seg_rms) + 1e-10) * 100
                soft_qualities.append(max(0.0, stability))
        soft_quality = float(np.mean(soft_qualities)) if soft_qualities else 0.0

        # v7.6: crescendo_quality 改为平均质量 × 覆盖率 (修复 P1-2 累积饱和)
        # 旧公式: crescendo = sum(smoothness * 0.01) → 长音频必然饱和到 100
        # 新公式: avg_quality × (0.5 + 0.5 × coverage) → 长度无关, 区分度提升
        crescendo_qualities = []
        w = 20
        for i in range(w, len(rms) - w):
            before = np.mean(rms[i-w:i])
            after = np.mean(rms[i:i+w])
            if before < rms[i] < after or before > rms[i] > after:
                smoothness = 100.0 - np.std(rms[i-w:i+w]) / (np.mean(rms[i-w:i+w]) + 1e-10) * 50
                crescendo_qualities.append(max(0.0, smoothness))

        if crescendo_qualities:
            avg_quality = float(np.mean(crescendo_qualities))
            coverage = min(1.0, len(crescendo_qualities) / max(1, (len(rms) - 2*w)))
            crescendo_quality = avg_quality * (0.5 + 0.5 * coverage)
        else:
            crescendo_quality = 0.0

        score = 0.0
        if soft_quality > 0:
            score += soft_quality * 0.40
        if crescendo_quality > 0:
            score += crescendo_quality * 0.30
        dynamic_range = 0.0
        if len(rms[rms > 0]) > 20:
            p95, p5 = np.percentile(rms[rms > 0], 95), np.percentile(rms[rms > 0], 5)
            dynamic_range = float(20 * np.log10(p95 / p5)) if p5 > 1e-10 else 0.0
        if dynamic_range > 0:
            score += min(30.0, dynamic_range)
        dynamic_control = max(0.0, min(100.0, score))
        return dynamic_control, soft_count, soft_quality, crescendo_quality
    except Exception:
        return 0.0, 0, 0.0, 0.0


def _eval_breath_design(rms):
    try:
        rms_mean = np.mean(rms[rms > 0])
        valleys = []
        for i in range(1, len(rms) - 1):
            if rms[i] < rms[i-1] and rms[i] < rms[i+1] and rms[i] < rms_mean * 0.3:
                valleys.append(i)
        clean_breaths = 0
        for vi in valleys:
            s, e = max(0, vi - 10), min(len(rms), vi + 10)
            before = np.mean(rms[s:vi]) if vi > s else 0
            after = np.mean(rms[vi:e]) if e > vi else 0
            if before > 0 and after > 0 and min(before, after) / max(before, after) > 0.7:
                clean_breaths += 1

        rms_smooth = uniform_filter1d(rms, size=5)
        coherence = 100.0 - np.mean(np.abs(rms - rms_smooth)) / (np.mean(rms) + 1e-10) * 50
        phrase_coherence = max(0.0, min(100.0, coherence))

        score = 0.0
        if clean_breaths > 0:
            score += min(30.0, clean_breaths * 5.0)
        if phrase_coherence > 0:
            score += phrase_coherence * 0.50
        breath_design = max(0.0, min(100.0, score))
        return breath_design, clean_breaths, phrase_coherence
    except Exception:
        return 0.0, 0, 0.0


def _eval_breath_technique(hnr, audio_data, singing_style):
    import librosa
    thresholds = {
        'pop': {'min_excellent': 8, 'max_excellent': 15, 'min_acceptable': 5},
        'classical': {'min_excellent': 20, 'max_excellent': 30, 'min_acceptable': 15},
        'folk': {'min_excellent': 15, 'max_excellent': 25, 'min_acceptable': 10},
        'rap': {'min_excellent': 5, 'max_excellent': 12, 'min_acceptable': 3},
    }
    t = thresholds.get(singing_style, thresholds['pop'])
    try:
        score = 0.0
        controlled_breathiness = 0.0
        uncontrolled_leak = 0.0
        if hnr < t['min_acceptable']:
            uncontrolled_leak = float(100.0 - hnr * 10)
            score -= min(40.0, (t['min_acceptable'] - hnr) * 8)
        elif hnr <= t['max_excellent']:
            controlled_breathiness = float(hnr * 5)
            hnr_range = t['max_excellent'] - t['min_acceptable']
            hnr_progress = (hnr - t['min_acceptable']) / max(hnr_range, 1)
            score += 10.0 + hnr_progress * 60
        else:
            controlled_breathiness = 80.0
            score += 70.0
        try:
            harmonic, _ = librosa.effects.hpss(audio_data, margin=(1.0, 3.0))
            harmonic_ratio = np.sum(harmonic ** 2) / (np.sum(audio_data ** 2) + 1e-10)
            if harmonic_ratio > 0.3:
                score += min(30.0, (harmonic_ratio - 0.3) / 0.7 * 30)
        except Exception:
            logger.debug("HPSS harmonic ratio failed in breath_technique", exc_info=True)
        breath_technique = max(0.0, min(100.0, score))
        return breath_technique, controlled_breathiness, uncontrolled_leak
    except Exception:
        return 0.0, 0.0, 0.0


def _calc_professional_breath_score(
    long_note_support, dynamic_control, breath_design, breath_technique,
    is_artistic, rms_fluctuation, long_note_count, clean_breath_count,
):
    try:
        has_basic = long_note_support > 40 or dynamic_control > 40
        if has_basic:
            w = (0.40, 0.25, 0.20, 0.15)
        else:
            w = (0.47, 0.28, 0.05, 0.15)
        score = (long_note_support * w[0] + dynamic_control * w[1] +
                 breath_design * w[2] + breath_technique * w[3])
        if not is_artistic and rms_fluctuation > 0.15:
            score -= min(40.0, (rms_fluctuation - 0.15) * 80)
        if long_note_count >= 1:
            score += min(10.0, long_note_count * 2.0)
        if clean_breath_count >= 1:
            score += min(8.0, clean_breath_count * 2.0)
        return max(0.0, min(100.0, score))
    except Exception:
        return 0.0


def _calc_long_note_decay(rms, rms_mean):
    try:
        segments = _find_continuous_segments(rms > rms_mean * 0.7)
        decays = []
        for s, e in segments:
            if e - s > 20:
                seg = rms[s:e]
                if len(seg) > 5:
                    slope = np.polyfit(np.arange(len(seg)), seg, 1)[0]
                    if slope < 0:
                        decays.append(-slope / (np.mean(seg) + 1e-10))
        return float(np.mean(decays)) if decays else 0.0
    except Exception:
        return 0.0
