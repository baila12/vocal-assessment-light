"""
气息分析模块 - 气息稳定性分析 v4.1

核心改进：
1. 区分「艺术化有规律起伏」和「无规律气息抖动」
2. 评估弱唱时的气息支撑质量
3. 区分「可控气声」和「无效漏气」
4. 正向加分为主，负向扣分为辅
"""
from typing import List, Tuple
import numpy as np
import librosa
from scipy import signal
from scipy.ndimage import uniform_filter1d
import logging

from . import BreathStabilityResult

logger = logging.getLogger(__name__)


class BreathAnalyzer:
    """气息分析器"""

    VOICE_FMIN = 65.0
    VOICE_FMAX = 1047.0

    def __init__(self, sample_rate: int = 22050, hop_length: int = 512):
        self.sample_rate = sample_rate
        self.hop_length = hop_length

    def calculate_breath_stability(
        self,
        audio_data: np.ndarray,
        f0: np.ndarray = None,
        singing_style: str = 'pop',
        hnr: float = 0.0
    ) -> BreathStabilityResult:
        """
        计算气息稳定性 - v4.1 专业气息评估体系

        Args:
            audio_data: 音频数据
            f0: 基频序列（可选）
            singing_style: 唱法类型 (pop/classical/folk/rap)
            hnr: 谐波噪声比

        Returns:
            BreathStabilityResult: 气息稳定性分析结果
        """
        result = BreathStabilityResult()

        try:
            # 计算 RMS 短时能量曲线
            rms = librosa.feature.rms(
                y=audio_data, frame_length=2048, hop_length=self.hop_length
            )[0]

            valid_rms = rms[rms > 0]
            if len(valid_rms) < 10:
                return result

            rms_mean = np.mean(valid_rms)
            rms_std = np.std(valid_rms)
            if rms_mean > 0:
                result.rms_fluctuation = float(rms_std / rms_mean)

            if np.min(valid_rms) > 0:
                result.dynamic_range = float(
                    20 * np.log10(np.max(valid_rms) / np.min(valid_rms))
                )

            # 提取基频（如果未提供）
            voiced_flags = ~np.isnan(f0) if f0 is not None else np.array([])

            # 区分「艺术化起伏」vs「随机抖动」
            is_artistic = self._detect_artistic_fluctuation(rms, f0, voiced_flags)
            result.is_artistic_fluctuation = is_artistic

            # 1. 长音气息支撑评估 (40%)
            self._evaluate_long_note_support(audio_data, rms, f0, voiced_flags, result)

            # 2. 强弱动态控制评估 (25%)
            self._evaluate_dynamic_control(rms, f0, audio_data, result)

            # 3. 气口设计评估 (20%)
            self._evaluate_breath_design(rms, audio_data, result)

            # 4. 气声技巧评估 (15%)
            self._evaluate_breath_technique(hnr, audio_data, singing_style, result)

            # 5. 计算专业气息综合得分
            self._calculate_professional_breath_score(result, singing_style)

            # 兼容旧指标
            result.sustain_quality = result.long_note_support_score

            # 长音衰减检测（保留兼容）
            self._calculate_long_note_decay(rms, rms_mean, result)

            # 气息断层检测（仅检测严重断层）
            rms_diff = np.diff(rms)
            sudden_drops = rms_diff < -rms_mean * 0.8
            result.breath_breaks = int(np.sum(sudden_drops))

        except Exception as e:
            logger.warning(f"气息稳定性分析失败: {e}")

        return result

    def _detect_artistic_fluctuation(
        self,
        rms: np.ndarray,
        f0: np.ndarray,
        voiced_flags: np.ndarray
    ) -> bool:
        """区分「艺术化有规律起伏」和「无规律气息抖动」"""
        try:
            rms_normalized = (rms - np.mean(rms)) / (np.std(rms) + 1e-10)
            autocorr = np.correlate(rms_normalized, rms_normalized, mode='full')
            autocorr = autocorr[len(autocorr)//2:]

            if len(autocorr) > 50:
                peaks, _ = signal.find_peaks(autocorr[1:50])
                if len(peaks) >= 2:
                    return True

            if f0 is not None and len(f0) > 0:
                valid_f0 = f0[voiced_flags] if len(voiced_flags) > 0 else f0[~np.isnan(f0)]
                if len(valid_f0) > 50 and len(rms) > 50:
                    min_len = min(len(valid_f0), len(rms))
                    if np.std(valid_f0[:min_len]) > 0 and np.std(rms[:min_len]) > 0:
                        correlation = np.corrcoef(valid_f0[:min_len], rms[:min_len])[0, 1]
                        if correlation > 0.3:
                            return True

            return False
        except Exception:
            return False

    def _evaluate_long_note_support(
        self,
        audio_data: np.ndarray,
        rms: np.ndarray,
        f0: np.ndarray,
        voiced_flags: np.ndarray,
        result: BreathStabilityResult
    ):
        """评估长音气息支撑稳定性 (40%)"""
        try:
            frame_duration = self.hop_length / self.sample_rate
            min_long_note_frames = int(3.0 / frame_duration)

            rms_mean = np.mean(rms[rms > 0])
            high_energy_mask = rms > rms_mean * 0.5
            segments = self._find_continuous_segments(high_energy_mask)

            long_notes = []
            pitch_stabilities = []
            harmonic_stabilities = []

            for start, end in segments:
                duration_frames = end - start
                if duration_frames >= min_long_note_frames:
                    long_notes.append((start, end, duration_frames))

                    if f0 is not None and len(f0) > end:
                        segment_f0 = f0[start:end]
                        valid_segment_f0 = segment_f0[~np.isnan(segment_f0)]
                        if len(valid_segment_f0) > 10:
                            midi_notes = 12 * np.log2(valid_segment_f0 / 440.0) + 69
                            cents_std = np.std(midi_notes - np.round(midi_notes)) * 100
                            pitch_stabilities.append(max(0, 100 - cents_std * 2))

                    segment_audio = audio_data[start * self.hop_length:end * self.hop_length]
                    if len(segment_audio) > 2048:
                        centroid = librosa.feature.spectral_centroid(y=segment_audio, sr=self.sample_rate)[0]
                        centroid_cv = np.std(centroid) / (np.mean(centroid) + 1e-10)
                        harmonic_stabilities.append(max(0, 100 - centroid_cv * 50))

            result.long_note_count = len(long_notes)

            if pitch_stabilities:
                result.pitch_stability_long = float(np.mean(pitch_stabilities))
            if harmonic_stabilities:
                result.harmonic_stability = float(np.mean(harmonic_stabilities))

            score = 40  # v5.12: 基线从60降到40
            if result.pitch_stability_long > 80:
                score += 12
            elif result.pitch_stability_long > 60:
                score += 8
            if result.harmonic_stability > 80:
                score += 8
            elif result.harmonic_stability > 60:
                score += 4

            for _, _, duration_frames in long_notes:
                duration_sec = duration_frames * frame_duration
                if duration_sec >= 15:
                    score += 8
                elif duration_sec >= 8:
                    score += 4

            if long_notes:
                result.long_note_avg_quality = (result.pitch_stability_long + result.harmonic_stability) / 2

            result.long_note_support_score = min(90, score)  # v5.12: 上限90
        except Exception:
            result.long_note_support_score = 40  # v5.12: 基线40

    def _evaluate_dynamic_control(
        self,
        rms: np.ndarray,
        f0: np.ndarray,
        audio_data: np.ndarray,
        result: BreathStabilityResult
    ):
        """评估强弱动态的气息可控性 (25%)"""
        try:
            rms_mean = np.mean(rms[rms > 0])
            soft_threshold = rms_mean * 0.6
            soft_mask = rms > np.percentile(rms[rms > 0], 10)
            soft_mask = soft_mask & (rms < soft_threshold)
            soft_segments = self._find_continuous_segments(soft_mask)

            result.soft_segment_count = len(soft_segments)

            soft_qualities = []
            for start, end in soft_segments:
                if end - start < 10:
                    continue
                segment_rms = rms[start:end]
                stability = 100 - np.std(segment_rms) / (np.mean(segment_rms) + 1e-10) * 100
                soft_qualities.append(max(0, stability))

            if soft_qualities:
                result.soft_singing_quality = float(np.mean(soft_qualities))

            crescendo_score = 0
            window = 20
            for i in range(window, len(rms) - window):
                before = np.mean(rms[i-window:i])
                after = np.mean(rms[i:i+window])
                current = rms[i]

                if before < current < after or before > current > after:
                    smoothness = 100 - np.std(rms[i-window:i+window]) / (np.mean(rms[i-window:i+window]) + 1e-10) * 50
                    crescendo_score += max(0, smoothness) * 0.01

            result.crescendo_quality = min(100, crescendo_score)

            score = 40  # v5.12: 基线从60降到40
            if result.soft_singing_quality > 70:
                score += 15
            elif result.soft_singing_quality > 50:
                score += 8
            if result.crescendo_quality > 50:
                score += 10
            if result.dynamic_range > 30:
                score += 3

            result.dynamic_control_score = min(90, score)  # v5.12: 上限90
        except Exception:
            result.dynamic_control_score = 40  # v5.12: 基线40

    def _evaluate_breath_design(
        self,
        rms: np.ndarray,
        audio_data: np.ndarray,
        result: BreathStabilityResult
    ):
        """评估气口设计与乐句气息分配 (20%)"""
        try:
            rms_mean = np.mean(rms[rms > 0])
            valleys = []
            for i in range(1, len(rms) - 1):
                if rms[i] < rms[i-1] and rms[i] < rms[i+1] and rms[i] < rms_mean * 0.3:
                    valleys.append(i)

            clean_breaths = 0
            for valley_idx in valleys:
                start = max(0, valley_idx - 10)
                end = min(len(rms), valley_idx + 10)
                before_mean = np.mean(rms[start:valley_idx]) if valley_idx > start else 0
                after_mean = np.mean(rms[valley_idx:end]) if end > valley_idx else 0

                if before_mean > 0 and after_mean > 0:
                    ratio = min(before_mean, after_mean) / max(before_mean, after_mean)
                    if ratio > 0.7:
                        clean_breaths += 1

            result.clean_breath_count = clean_breaths

            rms_smooth = uniform_filter1d(rms, size=5)
            coherence = 100 - np.mean(np.abs(rms - rms_smooth)) / (np.mean(rms) + 1e-10) * 50
            result.phrase_coherence = max(0, min(100, coherence))

            score = 40  # v5.12: 基线从60降到40
            if clean_breaths > 0:
                score += min(15, clean_breaths * 3)  # v5.12: 从*5降到*3
            if result.phrase_coherence > 70:
                score += 15  # v5.12: 20→15
            elif result.phrase_coherence > 50:
                score += 8   # v5.12: 10→8

            result.breath_design_score = min(90, score)  # v5.12: 上限90
        except Exception:
            result.breath_design_score = 40  # v5.12: 基线40

    def _evaluate_breath_technique(
        self,
        hnr: float,
        audio_data: np.ndarray,
        singing_style: str,
        result: BreathStabilityResult
    ):
        """评估气声/气息技巧的精准运用 (15%)"""
        try:
            hnr_thresholds = {
                'pop': {'min_excellent': 8, 'max_excellent': 15, 'min_acceptable': 5},
                'classical': {'min_excellent': 20, 'max_excellent': 30, 'min_acceptable': 15},
                'folk': {'min_excellent': 15, 'max_excellent': 25, 'min_acceptable': 10},
                'rap': {'min_excellent': 5, 'max_excellent': 12, 'min_acceptable': 3}
            }

            thresholds = hnr_thresholds.get(singing_style, hnr_thresholds['pop'])
            score = 40  # v5.12: 基线从60降到40

            if hnr < thresholds['min_acceptable']:
                result.uncontrolled_leak = float(100 - hnr * 10)
                score -= min(30, (thresholds['min_acceptable'] - hnr) * 3)
            elif hnr <= thresholds['max_excellent']:
                result.controlled_breathiness = float(hnr * 5)
                score += 12  # v5.12: 15→12
                if thresholds['min_excellent'] <= hnr <= thresholds['max_excellent']:
                    score += 8  # v5.12: 10→8
            else:
                result.controlled_breathiness = 50

            try:
                harmonic, _ = librosa.effects.hpss(audio_data, margin=(1.0, 3.0))
                harmonic_ratio = np.sum(harmonic ** 2) / (np.sum(audio_data ** 2) + 1e-10)
                if harmonic_ratio > 0.5:
                    score += 8  # v5.12: 10→8
            except Exception:
                pass

            result.breath_technique_score = max(0, min(90, score))  # v5.12: 上限90
        except Exception:
            result.breath_technique_score = 40  # v5.12: 基线40

    def _calculate_professional_breath_score(
        self,
        result: BreathStabilityResult,
        singing_style: str
    ):
        """
        计算专业气息综合得分 v5.12

        v5.12 修复:
        - 子维度基线从60降到40，避免所有演唱都拿满分
        - 非艺术波动惩罚加强（*30→*60）
        - 加分项设上限
        - sigmoid 拉伸拉开区分度
        """
        try:
            # 将子维度分数(原基线60)调整到0-80区间(新基线40)
            adjusted_long = max(0, result.long_note_support_score - 20)  # 60→40
            adjusted_dynamic = max(0, result.dynamic_control_score - 20)
            adjusted_design = max(0, result.breath_design_score - 20)
            adjusted_technique = max(0, result.breath_technique_score - 20)

            score = (
                adjusted_long * 0.40 +
                adjusted_dynamic * 0.25 +
                adjusted_design * 0.20 +
                adjusted_technique * 0.15
            )

            # 非艺术波动惩罚（v5.12: 加倍惩罚，*30→*60）
            fluctuation_penalty = 0
            if not result.is_artistic_fluctuation and result.rms_fluctuation > 0.25:
                # 阈值从0.35降到0.25，更早开始惩罚
                fluctuation_penalty = (result.rms_fluctuation - 0.25) * 60
            score -= fluctuation_penalty

            # 加分项设上限（v5.12: 原来无上限+3/+2）
            if result.long_note_count >= 3:
                score += min(5, result.long_note_count * 1)
            if result.clean_breath_count >= 2:
                score += min(3, result.clean_breath_count * 1)

            # v5.12: Sigmoid 拉伸 — 在50分处拐点，拉开区分度
            # 映射前: 0-100 → 映射后: 0-100，中间段被拉伸
            score = max(0, min(100, score))
            if score <= 50:
                stretched = score * 0.6  # 低分段压低
            else:
                stretched = 30 + (score - 50) * 1.0  # 高分段自然延伸，更难拿满分

            result.professional_breath_score = max(0, min(100, stretched))
        except Exception:
            result.professional_breath_score = 40

    def _calculate_long_note_decay(
        self,
        rms: np.ndarray,
        rms_mean: float,
        result: BreathStabilityResult
    ):
        """计算长音衰减"""
        high_energy_threshold = rms_mean * 0.7
        high_energy_segments = self._find_continuous_segments(rms > high_energy_threshold)

        decays = []
        for start, end in high_energy_segments:
            if end - start > 20:
                segment = rms[start:end]
                if len(segment) > 5:
                    x = np.arange(len(segment))
                    slope = np.polyfit(x, segment, 1)[0]
                    if slope < 0:
                        decay_rate = -slope / (np.mean(segment) + 1e-10)
                        decays.append(decay_rate)

        if decays:
            result.long_note_decay = float(np.mean(decays))

    def _find_continuous_segments(self, mask: np.ndarray) -> List[Tuple[int, int]]:
        """找到连续的True段"""
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
