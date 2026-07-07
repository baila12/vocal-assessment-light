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

from .types import BreathStabilityResult

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

            # v6.1: 连续线性映射 (替代 v5.19 步进加分, 基于真实声学测量)
            # pitch_stability (0-100) → linear bonus 0-40
            # harmonic_stability (0-100) → linear bonus 0-30
            # total note duration → linear bonus 0-30 (total across all notes, not per-note)
            score = 0
            if result.pitch_stability_long > 0:
                score += result.pitch_stability_long * 0.40  # 连续映射: 100→40
            if result.harmonic_stability > 0:
                score += result.harmonic_stability * 0.30    # 连续映射: 100→30

            # 总长音时长累积 (非单句累加, 避免上限压缩)
            total_long_duration = sum(
                duration_frames * frame_duration
                for _, _, duration_frames in long_notes
            )
            score += min(30, total_long_duration * 2.0)  # 0s→0, 15s→30

            if long_notes:
                result.long_note_avg_quality = (result.pitch_stability_long + result.harmonic_stability) / 2

            result.long_note_support_score = max(0, min(100, score))
        except Exception:
            result.long_note_support_score = 0  # v6.1: 基线 0

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

            # v6.1: 连续线性映射 (替代 v5.19 步进加分)
            # soft_singing_quality (0-100) → 0-40
            # crescendo_quality (0-100) → 0-30
            # dynamic_range (dB) → 0-30
            score = 0
            if result.soft_singing_quality > 0:
                score += result.soft_singing_quality * 0.40    # 连续: 100→40
            if result.crescendo_quality > 0:
                score += result.crescendo_quality * 0.30       # 连续: 100→30
            if result.dynamic_range > 0:
                score += min(30, result.dynamic_range * 1.0)   # 连续: 30dB→30

            result.dynamic_control_score = max(0, min(100, score))
        except Exception:
            result.dynamic_control_score = 0  # v6.1: 基线 0

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

            # v6.1: 连续线性映射 (替代 v5.19 步进加分)
            # clean_breaths → 0-30 (每干净气口 +5, 上限 30)
            # phrase_coherence (0-100) → 0-50
            score = 0
            if clean_breaths > 0:
                score += min(30, clean_breaths * 5)
            if result.phrase_coherence > 0:
                score += result.phrase_coherence * 0.50   # 连续: 100→50

            result.breath_design_score = max(0, min(100, score))
        except Exception:
            result.breath_design_score = 0  # v6.1: 基线 0

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
            # v6.1: 连续线性映射替代步进加分
            # HNR 在 min_acceptable→max_excellent 区间线性增长 0→70
            # HPSS harmonic_ratio 贡献额外 0→30
            score = 0

            if hnr < thresholds['min_acceptable']:
                result.uncontrolled_leak = float(100 - hnr * 10)
                # 漏气惩罚: 连续衰减 (hnr 越低惩罚越重)
                score -= min(40, (thresholds['min_acceptable'] - hnr) * 8)
            elif hnr <= thresholds['max_excellent']:
                result.controlled_breathiness = float(hnr * 5)
                # 连续线性: hnr 从 min_acceptable 到 max_excellent → 10 到 70
                hnr_range = thresholds['max_excellent'] - thresholds['min_acceptable']
                hnr_progress = (hnr - thresholds['min_acceptable']) / max(hnr_range, 1)
                score += 10 + hnr_progress * 60  # 连续映射
            else:
                result.controlled_breathiness = 80
                score += 70  # 优秀 HNR

            # v6.2 perf: 使用预计算的 harmonic_ratio (从 HPSS 缓存), 避免重复 HPSS
            try:
                # 尝试从 result 获取缓存的 harmonic_ratio
                cached_ratio = getattr(result, '_hpss_harmonic_ratio', None)
                if cached_ratio is not None and cached_ratio > 0:
                    harmonic_ratio = cached_ratio
                else:
                    harmonic, _ = librosa.effects.hpss(audio_data, margin=(1.0, 3.0))
                    harmonic_ratio = np.sum(harmonic ** 2) / (np.sum(audio_data ** 2) + 1e-10)
                if harmonic_ratio > 0.3:
                    score += min(30, (harmonic_ratio - 0.3) / 0.7 * 30)
            except Exception:
                pass

            result.breath_technique_score = max(0, min(100, score))
        except Exception:
            result.breath_technique_score = 0  # v6.1: 基线 0

    def _calculate_professional_breath_score(
        self,
        result: BreathStabilityResult,
        singing_style: str
    ):
        """
        计算专业气息综合得分 v6.2

        v6.1 改进:
        - 子维度连续线性映射 (曾步进加分)
        - 波动惩罚连续衰减
        - 加分项适度奖励

        v6.2 改进 (文献驱动):
        - 质量门控: breath_design 仅在基础气息控制达标时计全权重
          根因: clean_breath_count + phrase_coherence 与演唱质量弱相关
          (简单歌曲的规律换气也能得高分, 而专业歌手的气口设计在复杂歌曲中评分反低)
        - 当 long_note_support ≤ 40 且 dynamic_control ≤ 40 时:
          breath_design 权重 20%→5%, 差值重分配给诊断力更强的子维度
        - 文献: Titze (1994) — 长音支撑是气息控制的基石;
          Sundberg (1987) — 动态控制是衡量气息能力的主要指标
        """
        try:
            # v6.2: 质量门控 — 基础气息控制未达标时, 降低 breath_design 权重
            has_basic_breath = (
                result.long_note_support_score > 40 or
                result.dynamic_control_score > 40
            )

            if has_basic_breath:
                # 标准权重
                weights = (0.40, 0.25, 0.20, 0.15)
            else:
                # 降低 breath_design 权重, 重分配给诊断力更强的子维度
                # breath_design: 20%→5% (其与演唱质量弱相关)
                # long_note: 40%→47%, dynamic: 25%→28%
                weights = (0.47, 0.28, 0.05, 0.15)
                logger.debug(
                    f"Breath quality gate: low basic control "
                    f"(long_note={result.long_note_support_score:.0f}, "
                    f"dynamic={result.dynamic_control_score:.0f}), "
                    f"breath_design weight reduced 20%→5%"
                )

            score = (
                result.long_note_support_score * weights[0] +
                result.dynamic_control_score * weights[1] +
                result.breath_design_score * weights[2] +
                result.breath_technique_score * weights[3]
            )

            # 非艺术波动惩罚 (连续)
            fluctuation_penalty = 0
            if not result.is_artistic_fluctuation and result.rms_fluctuation > 0.15:
                fluctuation_penalty = min(40, (result.rms_fluctuation - 0.15) * 80)
            score -= fluctuation_penalty

            # 加分项 (连续, 上限)
            if result.long_note_count >= 1:
                score += min(10, result.long_note_count * 2)
            if result.clean_breath_count >= 1:
                score += min(8, result.clean_breath_count * 2)

            result.professional_breath_score = max(0, min(100, score))
        except Exception:
            result.professional_breath_score = 0  # v6.1: 基线 0

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
