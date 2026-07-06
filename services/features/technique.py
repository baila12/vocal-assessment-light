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

            # 综合技巧评分 v6.1: 从 0 开始 (曾 50), 仅检测到的技巧加分
            # HNR(40%)+CPP(30%) 已独立贡献声带闭合质量, technique_score 仅衡量技巧运用
            technique_score = 0
            if result.vibrato_count > 0:
                technique_score += min(50, result.vibrato_count * 10)  # v6.1: 每颤音 +10, 上限 50
                if result.vibrato_quality > 50:
                    technique_score += min(20, int(result.vibrato_quality / 5))  # v6.1: quality 驱动的加分
            if result.slide_count > 0:
                technique_score += min(20, result.slide_count * 5)  # v6.1: 每滑音 +5, 上限 20
            if result.falsetto_segments > 0:
                technique_score += min(15, result.falsetto_segments * 5)  # v6.1: 假声转换加分

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
