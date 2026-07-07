"""
演唱技巧检测模块

检测项目：
1. 颤音 (Vibrato): 频率 5-8Hz，幅度 0.5-2 半音
2. 滑音 (Slide): 连续音高变化
3. 假声 (Falsetto): 音色特征变化
"""
from typing import Dict
import numpy as np
import librosa
from scipy.ndimage import uniform_filter1d
import logging

from .types import VocalTechniqueResult

logger = logging.getLogger(__name__)


class TechniqueAnalyzer:
    """演唱技巧分析器"""

    VOICE_FMIN = 65.0
    VOICE_FMAX = 1047.0
    VIBRATO_RATE_MIN = 4.5
    VIBRATO_RATE_MAX = 8.0
    VIBRATO_EXTENT_MIN = 0.3
    VIBRATO_EXTENT_MAX = 1.5

    def __init__(self, sample_rate: int = 22050, hop_length: int = 512):
        self.sample_rate = sample_rate
        self.hop_length = hop_length

    def detect_vocal_techniques(
        self,
        f0: np.ndarray,
        audio_data: np.ndarray
    ) -> VocalTechniqueResult:
        """
        检测演唱技巧

        Args:
            f0: 基频序列
            audio_data: 音频数据

        Returns:
            VocalTechniqueResult: 演唱技巧检测结果
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

            # v6.2: 新增技巧检测
            result.staccato_count = self._detect_staccato(audio_data)
            result.legato_quality = self._detect_legato(valid_f0, audio_data)

            # 综合技巧评分 v6.2: 从 0 开始, 7 种技巧检测加分
            technique_score = 0
            if result.vibrato_count > 0:
                technique_score += min(40, result.vibrato_count * 8)
                if result.vibrato_quality > 50:
                    technique_score += min(15, int(result.vibrato_quality / 7))
            if result.slide_count > 0:
                technique_score += min(15, result.slide_count * 5)
            if result.falsetto_segments > 0:
                technique_score += min(10, result.falsetto_segments * 3)
            # v6.2: staccato + legato 加分
            if result.staccato_count > 0:
                technique_score += min(10, result.staccato_count * 3)
            if result.legato_quality > 30:
                technique_score += min(10, int(result.legato_quality / 10))

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

    def _detect_staccato(self, audio_data: np.ndarray) -> int:
        """
        v6.2: 断音 (Staccato) 检测

        断音特征: 短促、分离的音符, RMS 包络呈脉冲状, 音符间有明显的能量谷。
        检测方法: 寻找 RMS 短脉冲 (< 300ms) 且相邻脉冲间 RMS 降到基线以下。

        文献: Sundberg (1987). Ch.3 — staccato 是声门快速闭合的基本技巧

        Returns:
            staccato_count: 检测到的断音数
        """
        try:
            rms = librosa.feature.rms(
                y=audio_data, frame_length=1024, hop_length=self.hop_length
            )[0]
            rms_mean = np.mean(rms[rms > 0])

            if rms_mean <= 0:
                return 0

            # 寻找 RMS 峰 (高于均值 1.5x)
            peaks_mask = rms > rms_mean * 1.5

            # 寻找独立的短峰
            max_pulse_frames = int(0.3 * self.sample_rate / self.hop_length)  # 300ms
            min_gap_frames = int(0.05 * self.sample_rate / self.hop_length)  # 50ms silence gap

            staccato_count = 0
            in_peak = False
            peak_start = 0

            for i, is_peak in enumerate(peaks_mask):
                if is_peak and not in_peak:
                    in_peak = True
                    peak_start = i
                elif not is_peak and in_peak:
                    peak_duration = i - peak_start
                    if peak_duration <= max_pulse_frames:
                        staccato_count += 1
                    in_peak = False

            if in_peak:
                peak_duration = len(peaks_mask) - peak_start
                if peak_duration <= max_pulse_frames:
                    staccato_count += 1

            return staccato_count

        except Exception:
            return 0

    def _detect_legato(self, f0: np.ndarray, audio_data: np.ndarray) -> float:
        """
        v6.2: 连音 (Legato) 质量检测

        连音特征: 音符间平滑过渡, 无明显的能量中断或音高跳变。
        检测方法:
        1. 评估相邻音符间的沉默段长度 (越短越好)
        2. 评估音高变化的平滑度 (f0 diff CV)

        文献: Sundberg (1987). Ch.3 — legato 是歌唱的基本要求
              Nakano et al. (2006) — note transition smoothness

        Returns:
            legato_quality: 0-100, 越高表示连音越流畅
        """
        try:
            rms = librosa.feature.rms(
                y=audio_data, frame_length=1024, hop_length=self.hop_length
            )[0]
            rms_mean = np.mean(rms[rms > 0])

            if rms_mean <= 0:
                return 0.0

            # 1. 沉默段评估: 低能量帧的比例和长度
            rms_baseline = rms_mean * 0.2  # 低于 20% 均值视为"沉没"
            silence_mask = rms < rms_baseline

            # 计算沉默段统计
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

            # 每个沉默段代表一次中断, 越少越好
            if silent_gaps:
                avg_gap_frames = np.mean(silent_gaps)
                # 将平均沉默帧数映射到 0-100 质量分
                gap_penalty = min(50, avg_gap_frames * 5)
                silence_score = max(0, 100 - gap_penalty)
            else:
                silence_score = 100

            # 2. 音高平滑度评估
            if f0 is not None and len(f0) > 20:
                valid_f0 = f0[(~np.isnan(f0)) & (f0 > 65) & (f0 < 1047)]
                if len(valid_f0) > 20:
                    f0_diffs = np.abs(np.diff(valid_f0))
                    # 小的音高变化 (滑音) 是好的, 大的跳变 (断音) 降低 legato
                    small_changes = np.sum(f0_diffs < 1.0)  # < 1Hz 变化
                    large_jumps = np.sum(f0_diffs > 10.0)  # > 10Hz 跳变
                    smoothness_ratio = small_changes / max(len(f0_diffs), 1)
                    jump_penalty = min(40, large_jumps * 5)
                    pitch_score = max(0, smoothness_ratio * 100 - jump_penalty)
                else:
                    pitch_score = 50
            else:
                pitch_score = 50

            # 综合: 沉默评估 (60%) + 音高平滑 (40%)
            legato_quality = silence_score * 0.60 + pitch_score * 0.40

            return max(0, min(100, legato_quality))

        except Exception:
            return 0.0
