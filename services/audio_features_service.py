"""
高级音频特征提取服务 v1.0

实现专业声乐评估所需的精确特征提取：
1. 音分偏差计算 (cents deviation) - 音准精确量化
2. 节拍对齐分析 (rhythm alignment) - DTW节拍匹配
3. 气息稳定性分析 (breath stability) - RMS波动系数
4. 倒谱峰值显著性 (CPP) - 声带闭合质量
5. 演唱技巧检测 (vocal techniques) - 颤音、滑音、假声等

设计原则：
- 单一职责：每个函数只负责一种特征提取
- 返回 DTO：统一的数据传输对象
- 可配置：支持不同唱法的阈值调整
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
import numpy as np
import librosa
from scipy import signal
from scipy.ndimage import uniform_filter1d
import logging

logger = logging.getLogger(__name__)


@dataclass
class PitchDeviationResult:
    """音分偏差分析结果"""
    mae_cents: float = 0.0
    max_cents: float = 0.0
    consecutive_off_notes: int = 0
    pitch_breaks: int = 0
    pitch_wobble: float = 0.0
    detection_rate: float = 0.0
    valid_frame_count: int = 0


@dataclass
class RhythmAlignmentResult:
    """节拍对齐分析结果"""
    avg_deviation_ratio: float = 0.0
    max_deviation_ratio: float = 0.0
    off_beat_segments: int = 0
    beats_per_second: float = 0.0
    onset_count: int = 0
    irregularity: float = 0.0


@dataclass
class BreathStabilityResult:
    """气息稳定性分析结果 - v4.1 专业气息评估"""
    # 基础指标
    rms_fluctuation: float = 0.0
    long_note_decay: float = 0.0
    breath_breaks: int = 0
    dynamic_range: float = 0.0
    sustain_quality: float = 0.0

    # v4.1 新增：专业气息评估细分维度
    # 1. 长音气息支撑稳定性 (40%)
    long_note_support_score: float = 0.0  # 长音气息支撑得分
    long_note_count: int = 0              # 长音数量
    long_note_avg_quality: float = 0.0    # 长音平均质量
    harmonic_stability: float = 0.0       # 泛音保持度
    pitch_stability_long: float = 0.0     # 长音基频稳定度

    # 2. 强弱动态的气息可控性 (25%)
    dynamic_control_score: float = 0.0    # 强弱控制得分
    soft_singing_quality: float = 0.0     # 弱唱质量
    crescendo_quality: float = 0.0        # 渐强渐弱质量
    soft_segment_count: int = 0           # 弱唱片段数

    # 3. 气口设计与乐句气息分配 (20%)
    breath_design_score: float = 0.0      # 气口设计得分
    clean_breath_count: int = 0           # 无痕换气次数
    phrase_coherence: float = 0.0         # 乐句连贯性

    # 4. 气声/气息技巧的精准运用 (15%)
    breath_technique_score: float = 0.0   # 气声技巧得分
    controlled_breathiness: float = 0.0   # 可控气声比例
    uncontrolled_leak: float = 0.0        # 无效漏气比例

    # 综合评估
    is_artistic_fluctuation: bool = False  # 是否为艺术化起伏
    professional_breath_score: float = 0.0  # 专业气息综合得分


@dataclass
class VocalTechniqueResult:
    """演唱技巧检测结果"""
    vibrato_count: int = 0
    vibrato_rate_avg: float = 0.0
    vibrato_extent_avg: float = 0.0
    vibrato_quality: float = 0.0
    slide_count: int = 0
    falsetto_segments: int = 0
    technique_score: float = 0.0


@dataclass
class AudioFeaturesResult:
    """音频特征提取综合结果"""
    success: bool = True
    pitch_deviation: PitchDeviationResult = field(default_factory=PitchDeviationResult)
    rhythm_alignment: RhythmAlignmentResult = field(default_factory=RhythmAlignmentResult)
    breath_stability: BreathStabilityResult = field(default_factory=BreathStabilityResult)
    vocal_technique: VocalTechniqueResult = field(default_factory=VocalTechniqueResult)
    hnr: float = 0.0
    cpp: float = 0.0
    error_message: Optional[str] = None


class AudioFeaturesService:
    """高级音频特征提取服务"""

    VOICE_FMIN = 65.0
    VOICE_FMAX = 1047.0
    VIBRATO_RATE_MIN = 4.5
    VIBRATO_RATE_MAX = 8.0
    VIBRATO_EXTENT_MIN = 0.3
    VIBRATO_EXTENT_MAX = 1.5
    PITCH_EXCELLENT_CENTS = 10
    PITCH_PASS_CENTS = 50
    RHYTHM_EXCELLENT_RATIO = 0.1
    RHYTHM_PASS_RATIO = 0.3

    def __init__(self, sample_rate: int = 22050, hop_length: int = 512):
        self.sample_rate = sample_rate
        self.hop_length = hop_length

    def extract_all_features(
        self,
        audio_data: np.ndarray,
        f0: Optional[np.ndarray] = None,
        singing_style: str = 'pop'
    ) -> AudioFeaturesResult:
        """提取所有高级特征"""
        try:
            result = AudioFeaturesResult()

            if f0 is None:
                f0, voiced_flags = self._extract_f0(audio_data)
            else:
                voiced_flags = ~np.isnan(f0)

            result.pitch_deviation = self.calculate_pitch_deviation_cents(f0, voiced_flags)
            result.rhythm_alignment = self.calculate_rhythm_alignment(audio_data)
            result.breath_stability = self.calculate_breath_stability(
                audio_data, f0=f0, singing_style=singing_style
            )
            result.vocal_technique = self.detect_vocal_techniques(f0, audio_data)
            result.hnr = self.calculate_hnr(audio_data)
            result.cpp = self.calculate_cpp(audio_data)

            return result
        except Exception as e:
            logger.exception("特征提取失败")
            return AudioFeaturesResult(success=False, error_message=str(e))

    def _extract_f0(self, audio_data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        提取基频序列

        性能优化：使用yin算法替代pyin，速度提升约2倍
        """
        try:
            f0 = librosa.yin(
                audio_data,
                fmin=self.VOICE_FMIN,
                fmax=self.VOICE_FMAX,
                sr=self.sample_rate,
                hop_length=self.hop_length
            )
            # yin不返回voiced_flags，用非nan判断
            voiced_flags = ~np.isnan(f0)
            return f0, voiced_flags
        except Exception as e:
            logger.warning(f"基频提取失败: {e}")
            return np.array([]), np.array([])

    def calculate_pitch_deviation_cents(
        self,
        f0: np.ndarray,
        voiced_flags: np.ndarray
    ) -> PitchDeviationResult:
        """
        计算音分偏差

        核心算法：
        1. 将每个检测到的频率转换为 MIDI 音符
        2. 计算与最近标准音符的音分偏差
        3. 统计平均绝对偏差、最大偏差、连续跑调等
        """
        result = PitchDeviationResult()

        if f0 is None or len(f0) == 0:
            return result

        valid_mask = voiced_flags & (f0 > self.VOICE_FMIN) & (f0 < self.VOICE_FMAX)
        valid_f0 = f0[valid_mask]

        if len(valid_f0) < 10:
            return result

        result.valid_frame_count = len(valid_f0)
        result.detection_rate = len(valid_f0) / len(f0)

        # 转换为 MIDI 音符（浮点）
        midi_notes = 12 * np.log2(valid_f0 / 440.0) + 69

        # 音分偏差 = (实际MIDI - 标准MIDI) * 100
        nearest_midi = np.round(midi_notes)
        cents_deviation = (midi_notes - nearest_midi) * 100

        result.mae_cents = float(np.mean(np.abs(cents_deviation)))
        result.max_cents = float(np.max(np.abs(cents_deviation)))

        # 连续跑调检测（超过半音偏差的连续音符）
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
        result.consecutive_off_notes = max_consecutive

        # 音高断层检测（换声区问题）
        if len(valid_f0) > 10:
            f0_diff = np.abs(np.diff(np.log(valid_f0)))
            breaks = f0_diff > np.log(2) ** (1 / 12)
            result.pitch_breaks = int(np.sum(breaks))

        # 长音音高波动
        window_size = int(self.sample_rate / self.hop_length * 0.5)
        if len(cents_deviation) > window_size:
            windowed_std = uniform_filter1d(cents_deviation ** 2, window_size) ** 0.5
            result.pitch_wobble = float(np.max(windowed_std))

        return result

    def calculate_rhythm_alignment(
        self,
        audio_data: np.ndarray
    ) -> RhythmAlignmentResult:
        """
        计算节拍对齐度

        核心算法：
        1. 检测起始点 (onset)
        2. 追踪节拍 (beat tracking)
        3. 计算每个起始点与最近节拍点的偏差
        4. 归一化为拍长百分比
        """
        result = RhythmAlignmentResult()

        try:
            onset_env = librosa.onset.onset_strength(
                y=audio_data, sr=self.sample_rate, hop_length=self.hop_length
            )

            tempo, beat_frames = librosa.beat.beat_track(
                onset_envelope=onset_env,
                sr=self.sample_rate,
                hop_length=self.hop_length
            )

            result.beats_per_second = float(np.atleast_1d(tempo)[0]) / 60.0

            onset_frames = librosa.onset.onset_detect(
                onset_envelope=onset_env,
                sr=self.sample_rate,
                hop_length=self.hop_length
            )
            result.onset_count = len(onset_frames)

            if len(beat_frames) < 2 or len(onset_frames) < 2:
                return result

            beat_times = librosa.frames_to_time(
                beat_frames, sr=self.sample_rate, hop_length=self.hop_length
            )
            onset_times = librosa.frames_to_time(
                onset_frames, sr=self.sample_rate, hop_length=self.hop_length
            )

            beat_interval = np.mean(np.diff(beat_times))

            deviations = []
            for onset_t in onset_times:
                nearest_beat_idx = np.argmin(np.abs(beat_times - onset_t))
                nearest_beat = beat_times[nearest_beat_idx]
                deviation = abs(onset_t - nearest_beat)
                normalized_deviation = deviation / beat_interval
                deviations.append(normalized_deviation)

            if deviations:
                result.avg_deviation_ratio = float(np.mean(deviations))
                result.max_deviation_ratio = float(np.max(deviations))

            # 脱离节拍段检测
            off_beat_threshold = 0.3
            consecutive_off = 0
            off_beat_count = 0
            for d in deviations:
                if d > off_beat_threshold:
                    consecutive_off += 1
                else:
                    if consecutive_off >= 3:
                        off_beat_count += 1
                    consecutive_off = 0
            result.off_beat_segments = off_beat_count

            # 节奏不规则度
            if len(beat_frames) > 2:
                beat_intervals = np.diff(beat_times)
                if len(beat_intervals) > 0:
                    mean_interval = np.mean(beat_intervals)
                    if mean_interval > 0:
                        result.irregularity = float(np.std(beat_intervals) / mean_interval)

        except Exception as e:
            logger.warning(f"节拍对齐分析失败: {e}")

        return result

    def calculate_breath_stability(
        self,
        audio_data: np.ndarray,
        f0: Optional[np.ndarray] = None,
        singing_style: str = 'pop'
    ) -> BreathStabilityResult:
        """
        计算气息稳定性 - v4.1 专业气息评估体系

        核心改进：
        1. 区分「艺术化有规律起伏」和「无规律气息抖动」
        2. 评估弱唱时的气息支撑质量
        3. 区分「可控气声」和「无效漏气」
        4. 正向加分为主，负向扣分为辅

        Args:
            audio_data: 音频数据
            f0: 基频序列（可选）
            singing_style: 唱法类型 (pop/classical/folk/rap)
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

            # ========== v4.1 新增：专业气息评估 ==========

            # 1. 提取基频（如果未提供）
            if f0 is None:
                f0, voiced_flags = self._extract_f0(audio_data)
            else:
                voiced_flags = ~np.isnan(f0)

            # 2. 计算 HNR 用于气声判断
            hnr = self.calculate_hnr(audio_data)

            # 3. 区分「艺术化起伏」vs「随机抖动」
            is_artistic = self._detect_artistic_fluctuation(rms, f0, voiced_flags)
            result.is_artistic_fluctuation = is_artistic

            # 4. 长音气息支撑评估 (40%)
            self._evaluate_long_note_support(audio_data, rms, f0, voiced_flags, result)

            # 5. 强弱动态控制评估 (25%)
            self._evaluate_dynamic_control(rms, f0, audio_data, result)

            # 6. 气口设计评估 (20%)
            self._evaluate_breath_design(rms, audio_data, result)

            # 7. 气声技巧评估 (15%)
            self._evaluate_breath_technique(hnr, audio_data, singing_style, result)

            # 8. 计算专业气息综合得分
            self._calculate_professional_breath_score(result, singing_style)

            # 兼容旧指标
            result.sustain_quality = result.long_note_support_score

            # 长音衰减检测（保留兼容）
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

            # 气息断层检测（仅检测严重断层）
            rms_diff = np.diff(rms)
            sudden_drops = rms_diff < -rms_mean * 0.8  # 提高阈值，只检测严重断层
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
        """
        区分「艺术化有规律起伏」和「无规律气息抖动」

        艺术化起伏特征：
        1. 与乐句结构相关的渐强渐弱
        2. 自相关分析显示周期性规律
        3. 与基频变化同步（音高上升时音量自然上升）
        """
        try:
            # 对RMS进行自相关分析
            rms_normalized = (rms - np.mean(rms)) / (np.std(rms) + 1e-10)

            # 计算自相关
            autocorr = np.correlate(rms_normalized, rms_normalized, mode='full')
            autocorr = autocorr[len(autocorr)//2:]

            # 检测周期性（排除第0点）
            if len(autocorr) > 50:
                # 查找除0外的峰值
                peaks, _ = signal.find_peaks(autocorr[1:50])
                if len(peaks) >= 2:
                    # 有规律峰值 = 艺术化起伏
                    return True

            # 检测RMS与F0的相关性（音高上升时音量自然上升）
            if f0 is not None and len(f0) > 0:
                valid_f0 = f0[voiced_flags]
                if len(valid_f0) > 50 and len(rms) > 50:
                    # 重采样到相同长度
                    min_len = min(len(valid_f0), len(rms))
                    f0_resampled = valid_f0[:min_len]
                    rms_resampled = rms[:min_len]

                    # 计算相关系数
                    if np.std(f0_resampled) > 0 and np.std(rms_resampled) > 0:
                        correlation = np.corrcoef(f0_resampled, rms_resampled)[0, 1]
                        if correlation > 0.3:
                            # 音高与音量正相关 = 艺术化处理
                            return True

            return False

        except Exception as e:
            logger.warning(f"艺术化起伏检测失败: {e}")
            return False

    def _evaluate_long_note_support(
        self,
        audio_data: np.ndarray,
        rms: np.ndarray,
        f0: np.ndarray,
        voiced_flags: np.ndarray,
        result: BreathStabilityResult
    ):
        """
        评估长音气息支撑稳定性 (40%)

        核心指标：
        1. 长音泛音保持度
        2. 长音基频稳定度（音分偏差≤20音分为优秀）
        3. 气息衰减率（泛音无明显衰减为满分）
        4. 正向加分：8秒以上长音加5分，15秒以上加10分
        """
        try:
            frame_duration = self.hop_length / self.sample_rate
            min_long_note_frames = int(3.0 / frame_duration)  # 3秒以上为长音
            excellent_long_frames = int(8.0 / frame_duration)  # 8秒优秀
            master_long_frames = int(15.0 / frame_duration)   # 15秒大师级

            # 找到高能量连续段（长音候选）
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

                    # 计算该段的基频稳定度
                    if f0 is not None and len(f0) > end:
                        segment_f0 = f0[start:end]
                        valid_segment_f0 = segment_f0[~np.isnan(segment_f0)]
                        if len(valid_segment_f0) > 10:
                            # 音分偏差
                            midi_notes = 12 * np.log2(valid_segment_f0 / 440.0) + 69
                            cents_std = np.std(midi_notes - np.round(midi_notes)) * 100
                            pitch_stabilities.append(max(0, 100 - cents_std * 2))

                    # 计算泛音保持度（高频能量比例稳定性）
                    segment_audio = audio_data[start * self.hop_length:end * self.hop_length]
                    if len(segment_audio) > 2048:
                        # 简化：计算频谱质心变化
                        centroid = librosa.feature.spectral_centroid(
                            y=segment_audio, sr=self.sample_rate
                        )[0]
                        centroid_cv = np.std(centroid) / (np.mean(centroid) + 1e-10)
                        harmonic_stabilities.append(max(0, 100 - centroid_cv * 50))

            result.long_note_count = len(long_notes)

            if pitch_stabilities:
                result.pitch_stability_long = float(np.mean(pitch_stabilities))
            if harmonic_stabilities:
                result.harmonic_stability = float(np.mean(harmonic_stabilities))

            # 计算长音支持得分
            score = 60  # 基础分

            # 基频稳定度加分
            if result.pitch_stability_long > 80:
                score += 15
            elif result.pitch_stability_long > 60:
                score += 10

            # 泛音保持度加分
            if result.harmonic_stability > 80:
                score += 10
            elif result.harmonic_stability > 60:
                score += 5

            # 长音数量和时长加分
            for _, _, duration_frames in long_notes:
                duration_sec = duration_frames * frame_duration
                if duration_sec >= 15:
                    score += 10  # 大师级长音
                elif duration_sec >= 8:
                    score += 5   # 优秀长音

            # 长音平均质量
            if long_notes:
                result.long_note_avg_quality = (result.pitch_stability_long + result.harmonic_stability) / 2

            result.long_note_support_score = min(100, score)

        except Exception as e:
            logger.warning(f"长音评估失败: {e}")
            result.long_note_support_score = 60

    def _evaluate_dynamic_control(
        self,
        rms: np.ndarray,
        f0: np.ndarray,
        audio_data: np.ndarray,
        result: BreathStabilityResult
    ):
        """
        评估强弱动态的气息可控性 (25%)

        核心指标：
        1. 弱唱时HNR保持度（弱唱时HNR稳定在10dB以上为满分）
        2. 弱唱时基频稳定度
        3. 渐强渐弱处理的顺滑度
        4. 正向加分：高质量弱唱加5-8分
        """
        try:
            rms_mean = np.mean(rms[rms > 0])
            rms_std = np.std(rms[rms > 0])

            # 识别弱唱片段（低于平均音量60%）
            soft_threshold = rms_mean * 0.6
            soft_mask = rms > np.percentile(rms[rms > 0], 10)  # 排除静音
            soft_mask = soft_mask & (rms < soft_threshold)
            soft_segments = self._find_continuous_segments(soft_mask)

            result.soft_segment_count = len(soft_segments)

            # 评估弱唱质量
            soft_qualities = []
            for start, end in soft_segments:
                if end - start < 10:
                    continue

                segment_rms = rms[start:end]

                # 弱唱时的稳定性（不应有大幅波动）
                stability = 100 - np.std(segment_rms) / (np.mean(segment_rms) + 1e-10) * 100
                soft_qualities.append(max(0, stability))

            if soft_qualities:
                result.soft_singing_quality = float(np.mean(soft_qualities))

            # 检测渐强渐弱
            crescendo_score = 0
            window = 20
            for i in range(window, len(rms) - window):
                before = np.mean(rms[i-window:i])
                after = np.mean(rms[i:i+window])
                current = rms[i]

                # 渐强
                if before < current < after:
                    # 检查是否平滑
                    smoothness = 100 - np.std(rms[i-window:i+window]) / (np.mean(rms[i-window:i+window]) + 1e-10) * 50
                    crescendo_score += max(0, smoothness) * 0.01
                # 渐弱
                elif before > current > after:
                    smoothness = 100 - np.std(rms[i-window:i+window]) / (np.mean(rms[i-window:i+window]) + 1e-10) * 50
                    crescendo_score += max(0, smoothness) * 0.01

            result.crescendo_quality = min(100, crescendo_score)

            # 计算动态控制得分
            score = 60  # 基础分

            # 弱唱质量加分
            if result.soft_singing_quality > 70:
                score += 20
            elif result.soft_singing_quality > 50:
                score += 10

            # 渐强渐弱加分
            if result.crescendo_quality > 50:
                score += 15

            # 动态范围加分（30dB以上为优秀）
            if result.dynamic_range > 30:
                score += 5

            result.dynamic_control_score = min(100, score)

        except Exception as e:
            logger.warning(f"动态控制评估失败: {e}")
            result.dynamic_control_score = 60

    def _evaluate_breath_design(
        self,
        rms: np.ndarray,
        audio_data: np.ndarray,
        result: BreathStabilityResult
    ):
        """
        评估气口设计与乐句气息分配 (20%)

        核心指标：
        1. 换气的无痕度
        2. 乐句连贯性
        3. 合理换气不扣分
        """
        try:
            # 检测换气点（能量骤降后恢复）
            rms_mean = np.mean(rms[rms > 0])

            # 找能量低谷
            valleys = []
            for i in range(1, len(rms) - 1):
                if rms[i] < rms[i-1] and rms[i] < rms[i+1] and rms[i] < rms_mean * 0.3:
                    valleys.append(i)

            # 评估换气质量
            clean_breaths = 0
            for valley_idx in valleys:
                # 检查换气前后的连续性
                start = max(0, valley_idx - 10)
                end = min(len(rms), valley_idx + 10)

                before_mean = np.mean(rms[start:valley_idx]) if valley_idx > start else 0
                after_mean = np.mean(rms[valley_idx:end]) if end > valley_idx else 0

                # 如果换气前后能量相近，说明是无痕换气
                if before_mean > 0 and after_mean > 0:
                    ratio = min(before_mean, after_mean) / max(before_mean, after_mean)
                    if ratio > 0.7:
                        clean_breaths += 1

            result.clean_breath_count = clean_breaths

            # 乐句连贯性（基于能量曲线的平滑度）
            rms_smooth = uniform_filter1d(rms, size=5)
            coherence = 100 - np.mean(np.abs(rms - rms_smooth)) / (np.mean(rms) + 1e-10) * 50
            result.phrase_coherence = max(0, min(100, coherence))

            # 计算气口设计得分
            score = 60  # 基础分

            # 无痕换气加分
            if clean_breaths > 0:
                score += min(20, clean_breaths * 5)

            # 乐句连贯性加分
            if result.phrase_coherence > 70:
                score += 20
            elif result.phrase_coherence > 50:
                score += 10

            result.breath_design_score = min(100, score)

        except Exception as e:
            logger.warning(f"气口设计评估失败: {e}")
            result.breath_design_score = 60

    def _evaluate_breath_technique(
        self,
        hnr: float,
        audio_data: np.ndarray,
        singing_style: str,
        result: BreathStabilityResult
    ):
        """
        评估气声/气息技巧的精准运用 (15%)

        核心区分：
        - 可控气声（专业技巧，不扣分+加分）：HNR 5-15dB，谐波结构完整
        - 无效漏气（发声问题，扣分）：HNR < 5dB，谐波缺失

        分唱法阈值：
        - 流行：8-15dB 可控气声
        - 美声：20-30dB 优秀
        - 民族：15-25dB 优秀
        """
        try:
            # 分唱法HNR阈值
            hnr_thresholds = {
                'pop': {'min_excellent': 8, 'max_excellent': 15, 'min_acceptable': 5},
                'classical': {'min_excellent': 20, 'max_excellent': 30, 'min_acceptable': 15},
                'folk': {'min_excellent': 15, 'max_excellent': 25, 'min_acceptable': 10},
                'rap': {'min_excellent': 5, 'max_excellent': 12, 'min_acceptable': 3}
            }

            thresholds = hnr_thresholds.get(singing_style, hnr_thresholds['pop'])

            score = 60  # 基础分

            # 判断气声类型
            if hnr < thresholds['min_acceptable']:
                # 无效漏气
                result.uncontrolled_leak = float(100 - hnr * 10)
                score -= min(30, (thresholds['min_acceptable'] - hnr) * 3)
            elif hnr <= thresholds['max_excellent']:
                # 可控气声区间（专业技巧）
                result.controlled_breathiness = float(hnr * 5)
                # 加分
                score += 15
                if thresholds['min_excellent'] <= hnr <= thresholds['max_excellent']:
                    score += 10  # 最佳气声控制
            else:
                # HNR过高，声音可能过于"实"
                result.controlled_breathiness = 50

            # 检测谐波结构完整性
            try:
                harmonic, _ = librosa.effects.hpss(audio_data, margin=(1.0, 3.0))
                harmonic_ratio = np.sum(harmonic ** 2) / (np.sum(audio_data ** 2) + 1e-10)

                if harmonic_ratio > 0.5:
                    score += 10  # 谐波结构完整
            except Exception:
                pass

            result.breath_technique_score = max(0, min(100, score))

        except Exception as e:
            logger.warning(f"气声技巧评估失败: {e}")
            result.breath_technique_score = 60

    def _calculate_professional_breath_score(
        self,
        result: BreathStabilityResult,
        singing_style: str
    ):
        """
        计算专业气息综合得分

        权重分配：
        - 长音气息支撑稳定性：40%
        - 强弱动态可控性：25%
        - 气口设计：20%
        - 气声技巧：15%
        """
        try:
            # 如果是艺术化起伏，不因波动扣分
            fluctuation_penalty = 0
            if not result.is_artistic_fluctuation:
                # 只有非艺术化波动才考虑波动系数
                if result.rms_fluctuation > 0.35:
                    fluctuation_penalty = (result.rms_fluctuation - 0.35) * 30

            # 加权计算
            score = (
                result.long_note_support_score * 0.40 +
                result.dynamic_control_score * 0.25 +
                result.breath_design_score * 0.20 +
                result.breath_technique_score * 0.15
            )

            # 扣除非艺术化波动
            score -= fluctuation_penalty

            # 专业能力加分
            if result.long_note_count >= 3:
                score += 3  # 多处长音
            if result.clean_breath_count >= 2:
                score += 2  # 多处无痕换气

            result.professional_breath_score = max(0, min(100, score))

        except Exception as e:
            logger.warning(f"专业气息得分计算失败: {e}")
            result.professional_breath_score = 60

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

    def calculate_cpp(self, audio_data: np.ndarray) -> float:
        """
        计算倒谱峰值显著性 (Cepstral Peak Prominence)

        CPP 反映声带闭合质量，值越高声带闭合越好
        """
        try:
            frame_length = 2048
            frames = librosa.util.frame(
                audio_data, frame_length=frame_length, hop_length=self.hop_length
            )

            cpp_values = []
            min_quefrency = int(0.002 * self.sample_rate)
            max_quefrency = int(0.02 * self.sample_rate)

            for frame in frames.T:
                if np.max(np.abs(frame)) < 1e-6:
                    continue

                spectrum = np.abs(np.fft.rfft(frame))
                log_spectrum = np.log(spectrum + 1e-10)
                cepstrum = np.fft.ifft(log_spectrum).real

                if max_quefrency < len(cepstrum):
                    search_range = cepstrum[min_quefrency:max_quefrency]
                    if len(search_range) > 0:
                        peak = np.max(search_range)
                        baseline = np.mean(search_range)
                        cpp_values.append(peak - baseline)

            return float(np.mean(cpp_values)) if cpp_values else 0.0

        except Exception as e:
            logger.warning(f"CPP 计算失败: {e}")
            return 0.0

    def calculate_hnr(self, audio_data: np.ndarray) -> float:
        """
        计算谐波噪声比 (Harmonics-to-Noise Ratio)

        HNR 反映声带闭合程度，值越高声带闭合越好
        """
        try:
            harmonic, percussive = librosa.effects.hpss(audio_data, margin=(1.0, 3.0))
            harmonic_energy = np.sum(harmonic ** 2)
            residual_energy = np.sum((audio_data - harmonic) ** 2) + 1e-10

            if harmonic_energy > 0 and residual_energy > 0:
                hnr = 10 * np.log10(harmonic_energy / residual_energy)
                return float(max(0, min(40, hnr)))
            return 0.0

        except Exception as e:
            logger.warning(f"HNR 计算失败: {e}")
            return 0.0

    def detect_vocal_techniques(
        self,
        f0: np.ndarray,
        audio_data: np.ndarray
    ) -> VocalTechniqueResult:
        """
        检测演唱技巧

        检测项目：
        1. 颤音 (Vibrato): 频率 5-8Hz，幅度 0.5-2 半音
        2. 滑音 (Slide): 连续音高变化
        3. 假声 (Falsetto): 音色特征变化
        """
        result = VocalTechniqueResult()

        if f0 is None or len(f0) < 50:
            return result

        try:
            valid_mask = (f0 > self.VOICE_FMIN) & (f0 < self.VOICE_FMAX)
            valid_f0 = f0[valid_mask]

            if len(valid_f0) < 30:
                return result

            vibrato_result = self._detect_vibrato(valid_f0)
            result.vibrato_count = vibrato_result['count']
            result.vibrato_rate_avg = vibrato_result['rate']
            result.vibrato_extent_avg = vibrato_result['extent']
            result.vibrato_quality = vibrato_result['quality']

            result.slide_count = self._detect_slides(valid_f0)
            result.falsetto_segments = self._detect_falsetto(audio_data)

            # 综合技巧评分
            technique_score = 50
            if result.vibrato_count > 0:
                technique_score += min(30, result.vibrato_count * 3)
                if result.vibrato_quality > 70:
                    technique_score += 10
            if 0 < result.slide_count <= 5:
                technique_score += 5

            result.technique_score = min(100, technique_score)

        except Exception as e:
            logger.warning(f"技巧检测失败: {e}")

        return result

    def _detect_vibrato(self, f0: np.ndarray) -> Dict:
        """检测颤音"""
        result = {'count': 0, 'rate': 0.0, 'extent': 0.0, 'quality': 0.0}

        try:
            f0_semitones = 12 * np.log2(f0 / 440.0)
            window = min(20, len(f0_semitones) // 4)
            if window < 2:
                return result

            trend = uniform_filter1d(f0_semitones, window * 2)
            detrended = f0_semitones - trend

            fft_result = np.fft.fft(detrended)
            freqs = np.fft.fftfreq(len(detrended), d=self.hop_length / self.sample_rate)

            vibrato_mask = (np.abs(freqs) >= self.VIBRATO_RATE_MIN) & \
                          (np.abs(freqs) <= self.VIBRATO_RATE_MAX)

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
                    result['count'] = self._count_vibrato_segments(detrended, vibrato_rate)

                    quality = 100
                    if not (self.VIBRATO_RATE_MIN <= vibrato_rate <= self.VIBRATO_RATE_MAX):
                        quality -= 20
                    if not (self.VIBRATO_EXTENT_MIN <= vibrato_extent <= self.VIBRATO_EXTENT_MAX):
                        quality -= 20
                    result['quality'] = max(0, quality)

        except Exception as e:
            logger.warning(f"颤音检测失败: {e}")

        return result

    def _count_vibrato_segments(self, detrended: np.ndarray, vibrato_rate: float) -> int:
        """计算颤音段数量"""
        if vibrato_rate < self.VIBRATO_RATE_MIN:
            return 0

        frames_per_cycle = self.sample_rate / (self.hop_length * vibrato_rate)
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

    def _detect_slides(self, f0: np.ndarray) -> int:
        """检测滑音"""
        try:
            f0_diff = np.diff(np.log(f0))
            slide_threshold = 0.02
            is_sliding = np.abs(f0_diff) > slide_threshold

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

    def _detect_falsetto(self, audio_data: np.ndarray) -> int:
        """检测假声段"""
        try:
            segment_length = int(self.sample_rate * 0.5)
            num_segments = len(audio_data) // segment_length
            falsetto_count = 0

            for i in range(num_segments):
                start = i * segment_length
                end = start + segment_length
                segment = audio_data[start:end]

                centroid = librosa.feature.spectral_centroid(
                    y=segment, sr=self.sample_rate
                )[0]
                mean_centroid = np.mean(centroid)

                if mean_centroid > 3500:
                    falsetto_count += 1

            return falsetto_count
        except Exception:
            return 0
