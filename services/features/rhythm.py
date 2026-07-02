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

from .types import RhythmAlignmentResult

logger = logging.getLogger(__name__)


class RhythmAnalyzer:
    """节奏分析器"""

    VOICE_FMIN = 65.0
    VOICE_FMAX = 1047.0

    def __init__(self, sample_rate: int = 22050, hop_length: int = 512):
        self.sample_rate = sample_rate
        self.hop_length = hop_length
        # v5.11: 节奏分析使用22050Hz以获得更好的onset检测精度
        # 16kHz下onset检测产生更多误检(呼吸/辅音被误判为onset)
        self._rhythm_sr = 22050

    def calculate_rhythm_alignment(
        self,
        audio_data: np.ndarray,
        f0: np.ndarray = None,
        voiced_flags: np.ndarray = None,
        is_clean_vocal: bool = False
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
                result = self._calculate_rhythm_from_pitch(audio_data, f0, voiced_flags, is_clean_vocal)
                if result.onset_count > 0:
                    return result

            # 降级到传统onset检测
            result = self._calculate_rhythm_traditional(audio_data, is_clean_vocal)

        except Exception as e:
            logger.warning(f"节拍对齐分析失败: {e}")

        return result

    def _calculate_rhythm_traditional(self, audio_data: np.ndarray, is_clean_vocal: bool = False) -> RhythmAlignmentResult:
        """
        基于onset密度和规律性的节奏分析 v5.11

        替代原来基于librosa.beat.beat_track的方法，不再假设恒定BPM/4/4拍号。
        onset间隔的变异系数(CV)用于评估节奏规律性，适用于：
        - 无伴奏独唱
        - 弹性速度(Rubato)
        - 非西方节奏体系
        - 传统流行乐

        v5.11: 长音频分段分析，避免全程CV被段落密度差异污染
        """
        result = RhythmAlignmentResult()

        # v5.11: 重采样到22kHz以获得更好的onset检测精度
        if self.sample_rate != self._rhythm_sr:
            audio_data = librosa.resample(audio_data, orig_sr=self.sample_rate, target_sr=self._rhythm_sr)
            sr = self._rhythm_sr
        else:
            sr = self.sample_rate

        # v5.11: 长音频分段分析（60s窗口，30s步长），取中位数CV
        segment_dur = 60.0  # 60 second windows
        segment_hop = 30.0  # 30 second overlap
        total_duration = len(audio_data) / sr

        if total_duration > segment_dur * 1.5:
            # 长音频：分段分析
            segment_cvs = []
            segment_devs = []
            total_onsets = 0
            total_off_beat = 0
            max_bps = 0.0

            for start_t in np.arange(0, total_duration - segment_dur, segment_hop):
                end_t = min(start_t + segment_dur, total_duration)
                start_sample = int(start_t * sr)
                end_sample = int(end_t * sr)
                segment = audio_data[start_sample:end_sample]

                if len(segment) < sr * 3:  # skip segments < 3s
                    continue

                seg_onset_env = librosa.onset.onset_strength(
                    y=segment, sr=sr, hop_length=self.hop_length
                )
                seg_onset_frames = librosa.onset.onset_detect(
                    onset_envelope=seg_onset_env, sr=sr, hop_length=self.hop_length
                )

                if len(seg_onset_frames) < 3:
                    continue

                seg_times = librosa.frames_to_time(seg_onset_frames, sr=sr, hop_length=self.hop_length)
                seg_ioi = np.diff(seg_times)
                seg_mean = np.mean(seg_ioi)
                if seg_mean > 0:
                    seg_cv = float(np.std(seg_ioi) / seg_mean)
                    segment_cvs.append(seg_cv)
                    seg_dev = self._cv_to_deviation(seg_cv, is_clean_vocal)
                    segment_devs.append(seg_dev)
                    total_onsets += len(seg_onset_frames)
                    total_off_beat += self._count_irregular_segments(seg_ioi, seg_mean)
                    seg_bps = len(seg_onset_frames) / (seg_times[-1] - seg_times[0]) if seg_times[-1] > seg_times[0] else 0
                    max_bps = max(max_bps, seg_bps)

            if segment_cvs:
                # 使用中位数CV（比均值更鲁棒，不受极端段影响）
                result.irregularity = float(np.median(segment_cvs))
                result.avg_deviation_ratio = float(np.median(segment_devs))
                result.onset_count = total_onsets
                result.beats_per_second = max_bps
                result.off_beat_segments = total_off_beat
                return result

        # 短音频或分段失败：直接分析
        onset_env = librosa.onset.onset_strength(
            y=audio_data, sr=sr, hop_length=self.hop_length
        )

        onset_frames = librosa.onset.onset_detect(
            onset_envelope=onset_env,
            sr=sr,
            hop_length=self.hop_length
        )
        result.onset_count = len(onset_frames)

        if len(onset_frames) < 2:
            return result

        onset_times = librosa.frames_to_time(
            onset_frames, sr=sr, hop_length=self.hop_length
        )

        ioi = np.diff(onset_times)
        mean_ioi = np.mean(ioi)

        if mean_ioi > 0:
            total_dur = onset_times[-1] - onset_times[0]
            result.beats_per_second = result.onset_count / total_dur if total_dur > 0 else 0.0
            result.irregularity = float(np.std(ioi) / mean_ioi)
            result.avg_deviation_ratio = self._cv_to_deviation(result.irregularity, is_clean_vocal)
            result.off_beat_segments = self._count_irregular_segments(ioi, mean_ioi)

        return result

    @staticmethod
    def _cv_to_deviation(cv: float, is_clean_vocal: bool = False) -> float:
        """
        将CV（变异系数）映射到deviation_ratio (0-1) v5.13

        纯净人声(Demucs分离后)的onset间隔分布与混合音频完全不同:
        - 混合音频: 伴奏提供规律节奏线索, onset CV < 0.3 为专业级
        - 纯净人声: 只有咬字/气息切换, 句间天然长停顿, CV天然偏高

        CV解读 (混合音频):
          <0.3: 非常规律 / 0.3-0.5: 正常 / 0.5-0.8: 中等
          0.8-1.2: 较不规则 / >1.2: 严重不规则

        CV解读 (纯净人声, is_clean_vocal=True):
          <0.5: 非常规律 / 0.5-0.8: 正常 / 0.8-1.2: 中等
          1.2-1.8: 较不规则 / >1.8: 严重不规则
        """
        if is_clean_vocal:
            if cv < 0.5:
                return cv * 0.35
            elif cv < 0.8:
                return 0.175 + (cv - 0.5) * 0.5
            elif cv < 1.2:
                return 0.325 + (cv - 0.8) * 0.6
            elif cv < 1.8:
                return 0.565 + (cv - 1.2) * 0.5
            else:
                return min(1.0, 0.865 + (cv - 1.8) * 0.2)
        else:
            if cv < 0.3:
                return cv * 0.4
            elif cv < 0.5:
                return 0.12 + (cv - 0.3) * 0.6
            elif cv < 0.8:
                return 0.24 + (cv - 0.5) * 0.8
            elif cv < 1.2:
                return 0.48 + (cv - 0.8) * 1.0
            else:
                return min(1.0, 0.88 + (cv - 1.2) * 0.3)

    def _count_irregular_segments(self, ioi: np.ndarray, mean_ioi: float) -> int:
        """
        检测节奏不规则段

        将onset间隔远离平均值的区域标记为不规则段。
        这在概念上替代了原来的"脱离节拍"检测，更适合非严格拍子的音乐。

        Args:
            ioi: onset间隔数组
            mean_ioi: 平均onset间隔

        Returns:
            不规则段数量
        """
        if len(ioi) < 3 or mean_ioi <= 0:
            return 0

        # 标记偏离均值超过50%的间隔
        irregular_mask = np.abs(ioi - mean_ioi) > mean_ioi * 0.5

        # 找到连续的不规则段
        segments = []
        start = None
        for i, val in enumerate(irregular_mask):
            if val and start is None:
                start = i
            elif not val and start is not None:
                if i - start >= 2:  # 至少2个连续不规则间隔
                    segments.append((start, i))
                start = None
        if start is not None and len(irregular_mask) - start >= 2:
            segments.append((start, len(irregular_mask)))

        return len(segments)

    def _calculate_rhythm_from_pitch(
        self,
        audio_data: np.ndarray,
        f0: np.ndarray,
        voiced_flags: np.ndarray,
        is_clean_vocal: bool = False
    ) -> RhythmAlignmentResult:
        """
        基于人声基频变化检测节奏 v5.10

        使用音高变化onset替代传统onset检测，不受伴奏干扰。
        使用onset间隔变异系数评估节奏规律性，不再依赖beat_track。
        """
        result = RhythmAlignmentResult()

        try:
            # v5.11: 重采样到22kHz
            if self.sample_rate != self._rhythm_sr:
                audio_data = librosa.resample(audio_data, orig_sr=self.sample_rate, target_sr=self._rhythm_sr)
                sr = self._rhythm_sr
            else:
                sr = self.sample_rate

            valid_mask = ~np.isnan(f0) & (f0 > self.VOICE_FMIN) & (f0 < self.VOICE_FMAX)

            if np.sum(valid_mask) < 20:
                return result

            # 转换为音分（对数尺度）
            f0_cents = np.where(valid_mask, 1200 * np.log2(f0 / 440.0 + 1e-10), np.nan)

            # 检测显著的音高变化（>100音分）
            f0_diff = np.abs(np.diff(f0_cents))
            valid_diff_mask = valid_mask[:-1] & valid_mask[1:] & (~np.isnan(f0_diff))
            pitch_onset_frames = np.where(valid_diff_mask & (f0_diff > 100))[0]

            if len(pitch_onset_frames) < 3:
                return result

            pitch_onset_times = librosa.frames_to_time(
                pitch_onset_frames,
                sr=sr,
                hop_length=self.hop_length
            )

            result.onset_count = len(pitch_onset_times)

            if len(pitch_onset_times) < 2:
                return result

            # v5.10: 使用onset间隔变异系数评估节奏规律性
            ioi = np.diff(pitch_onset_times)
            mean_ioi = np.mean(ioi)

            if mean_ioi > 0:
                total_duration = pitch_onset_times[-1] - pitch_onset_times[0]
                result.beats_per_second = result.onset_count / total_duration if total_duration > 0 else 0.0

                # onset变异系数 = 节奏不规则度
                result.irregularity = float(np.std(ioi) / mean_ioi)

                # 映射到avg_deviation_ratio (v5.11 重新校准)
                result.avg_deviation_ratio = self._cv_to_deviation(result.irregularity, is_clean_vocal)

                # 检测不规则段
                result.off_beat_segments = self._count_irregular_segments(ioi, mean_ioi)

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
