"""
音准分析模块 - 音分偏差计算

核心算法：
1. 将每个检测到的频率转换为 MIDI 音符
2. 计算与最近标准音符的音分偏差
3. 统计平均绝对偏差、最大偏差、连续跑调等
"""
import numpy as np
from scipy.ndimage import uniform_filter1d
import logging

from . import PitchDeviationResult

logger = logging.getLogger(__name__)


class PitchAnalyzer:
    """音准分析器"""

    VOICE_FMIN = 65.0
    VOICE_FMAX = 1047.0

    def __init__(self, sample_rate: int = 22050, hop_length: int = 512):
        self.sample_rate = sample_rate
        self.hop_length = hop_length

    def calculate_pitch_deviation_cents(
        self,
        f0: np.ndarray,
        voiced_flags: np.ndarray
    ) -> PitchDeviationResult:
        """
        计算音分偏差

        Args:
            f0: 基频序列
            voiced_flags: 是否为有声帧

        Returns:
            PitchDeviationResult: 音分偏差分析结果
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
            f0_cents = 1200 * np.log2(valid_f0 / 440.0)
            f0_cents_diff = np.abs(np.diff(f0_cents))
            significant_breaks = f0_cents_diff > 200
            result.pitch_breaks = int(np.sum(significant_breaks))

        # 长音音高波动
        window_size = int(self.sample_rate / self.hop_length * 0.5)
        if len(cents_deviation) > window_size:
            windowed_std = uniform_filter1d(cents_deviation ** 2, window_size) ** 0.5
            result.pitch_wobble = float(np.max(windowed_std))

        return result
