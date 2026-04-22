"""
节奏分析模块 - 节拍对齐分析

核心算法：
1. 如果有基频信息，优先使用人声基频变化检测节奏
2. 否则使用传统onset检测
3. 追踪节拍 (beat tracking)
4. 计算每个起始点与最近节拍点的偏差
"""
from typing import Tuple
import numpy as np
import librosa
import logging

from . import RhythmAlignmentResult

logger = logging.getLogger(__name__)


class RhythmAnalyzer:
    """节奏分析器"""

    VOICE_FMIN = 65.0
    VOICE_FMAX = 1047.0

    def __init__(self, sample_rate: int = 22050, hop_length: int = 512):
        self.sample_rate = sample_rate
        self.hop_length = hop_length

    def calculate_rhythm_alignment(
        self,
        audio_data: np.ndarray,
        f0: np.ndarray = None,
        voiced_flags: np.ndarray = None
    ) -> RhythmAlignmentResult:
        """
        计算节拍对齐度

        Args:
            audio_data: 音频数据
            f0: 基频序列（可选）
            voiced_flags: 有声帧标记（可选）

        Returns:
            RhythmAlignmentResult: 节拍对齐分析结果
        """
        result = RhythmAlignmentResult()

        try:
            # 优先使用人声基频变化检测节奏（减少伴奏干扰）
            if f0 is not None and voiced_flags is not None:
                result = self._calculate_rhythm_from_pitch(audio_data, f0, voiced_flags)
                if result.onset_count > 0:
                    return result

            # 降级到传统onset检测
            result = self._calculate_rhythm_traditional(audio_data)

        except Exception as e:
            logger.warning(f"节拍对齐分析失败: {e}")

        return result

    def _calculate_rhythm_traditional(self, audio_data: np.ndarray) -> RhythmAlignmentResult:
        """传统onset检测方法"""
        result = RhythmAlignmentResult()

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
        result.off_beat_segments = self._count_off_beat_segments(deviations)

        # 节奏不规则度
        if len(beat_frames) > 2:
            beat_intervals = np.diff(beat_times)
            if len(beat_intervals) > 0:
                mean_interval = np.mean(beat_intervals)
                if mean_interval > 0:
                    result.irregularity = float(np.std(beat_intervals) / mean_interval)

        return result

    def _calculate_rhythm_from_pitch(
        self,
        audio_data: np.ndarray,
        f0: np.ndarray,
        voiced_flags: np.ndarray
    ) -> RhythmAlignmentResult:
        """基于人声基频变化检测节奏（减少伴奏干扰）"""
        result = RhythmAlignmentResult()

        try:
            valid_mask = ~np.isnan(f0) & (f0 > self.VOICE_FMIN) & (f0 < self.VOICE_FMAX)

            if np.sum(valid_mask) < 20:
                return result

            # 转换为音分（对数尺度）
            f0_cents = np.where(valid_mask, 1200 * np.log2(f0 / 440.0 + 1e-10), np.nan)

            # 检测显著的音高变化（>100音分）
            f0_diff = np.abs(np.diff(f0_cents))
            valid_diff_mask = valid_mask[:-1] & valid_mask[1:] & (~np.isnan(f0_diff))
            pitch_onset_frames = np.where(valid_diff_mask & (f0_diff > 100))[0]

            if len(pitch_onset_frames) < 5:
                return result

            # 获取全局节拍
            onset_env = librosa.onset.onset_strength(
                y=audio_data, sr=self.sample_rate, hop_length=self.hop_length
            )
            tempo, beat_frames = librosa.beat.beat_track(
                onset_envelope=onset_env,
                sr=self.sample_rate,
                hop_length=self.hop_length
            )

            result.beats_per_second = float(np.atleast_1d(tempo)[0]) / 60.0

            if len(beat_frames) < 2:
                return result

            pitch_onset_times = librosa.frames_to_time(
                pitch_onset_frames,
                sr=self.sample_rate,
                hop_length=self.hop_length
            )

            beat_times = librosa.frames_to_time(
                beat_frames, sr=self.sample_rate, hop_length=self.hop_length
            )

            result.onset_count = len(pitch_onset_times)

            if len(beat_times) < 2 or len(pitch_onset_times) < 2:
                return result

            beat_interval = np.mean(np.diff(beat_times))

            # 计算人声音符起始与节拍的对齐度
            first_beat = beat_times[0]
            last_beat = beat_times[-1]

            deviations = []
            for onset_t in pitch_onset_times:
                if onset_t < first_beat or onset_t > last_beat + beat_interval:
                    continue

                nearest_beat_idx = np.argmin(np.abs(beat_times - onset_t))
                nearest_beat = beat_times[nearest_beat_idx]
                deviation = abs(onset_t - nearest_beat)
                normalized_deviation = min(deviation / beat_interval, 1.0)
                deviations.append(normalized_deviation)

            if deviations:
                result.avg_deviation_ratio = float(np.mean(deviations))
                result.max_deviation_ratio = float(np.max(deviations))

            result.off_beat_segments = self._count_off_beat_segments(deviations)

            # 节奏不规则度
            if len(beat_frames) > 2:
                beat_intervals = np.diff(beat_times)
                if len(beat_intervals) > 0:
                    mean_interval = np.mean(beat_intervals)
                    if mean_interval > 0:
                        result.irregularity = float(np.std(beat_intervals) / mean_interval)

        except Exception as e:
            logger.warning(f"基于音高的节奏分析失败: {e}")

        return result

    def _count_off_beat_segments(self, deviations: list) -> int:
        """计算脱离节拍段数量"""
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
        return off_beat_count
