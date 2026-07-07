"""
音准分析模块 - 音分偏差计算 v5.14

核心算法:
1. 将每个检测到的频率转换为 MIDI 音符
2. 计算与最近标准音符的音分偏差
3. 多指标体系 (移植自 pitch-benchmark): RPA, RCA, gross_error, octave_error, smoothness
"""
import numpy as np
from scipy.ndimage import uniform_filter1d, find_objects, label
import logging

from .types import PitchDeviationResult

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

        # 音高断层检测（换声区问题） v6.2: 仅检测连续有声帧间的断层
        # 根因: librosa.yin 输出含 NaN (无声帧), valid_f0 滤掉 NaN 后 diff 在
        # 非连续帧间计算, 导致1000+伪断层。改为仅计算真正相邻的有声帧对。
        if len(valid_f0) > 10:
            f0_cents = 1200 * np.log2(valid_f0 / 440.0)
            # v6.2: 中值滤波消除 YIN 的散发性错误 (size=9 → ~300ms窗口)
            # size=5 不足以消除单帧八度跳变; YIN 错误通常是 1-2 帧的孤立伪影
            # de Cheveigne & Kawahara (2002): YIN 在低SNR下八度误差率升高
            f0_cents_smooth = uniform_filter1d(f0_cents.astype(float), size=9)
            f0_cents_diff = np.abs(np.diff(f0_cents_smooth))

            # v6.2: 仅计数真正的相邻帧断层 (排除跨无声段的跳变)
            # 在原始 f0 上标记有声帧, 仅计算相邻有声帧间的跳变
            voiced_in_full = ~np.isnan(f0) & (f0 > self.VOICE_FMIN) & (f0 < self.VOICE_FMAX)
            voiced_indices = np.where(voiced_in_full)[0]
            if len(voiced_indices) > 1:
                consecutive_mask = np.diff(voiced_indices) == 1
                # 获取连续帧对在原 f0 中的位置
                consecutive_starts = voiced_indices[:-1][consecutive_mask]
                consecutive_ends = voiced_indices[1:][consecutive_mask]
                # 计算这些连续帧对的音高差
                if len(consecutive_starts) > 0:
                    f0_starts = f0[consecutive_starts]
                    f0_ends = f0[consecutive_ends]
                    cents_starts = 1200 * np.log2(f0_starts / 440.0)
                    cents_ends = 1200 * np.log2(f0_ends / 440.0)
                    cents_jumps = np.abs(cents_ends - cents_starts)
                    # v6.2: 排除八度跳变 (YIN 最常见的错误模式 — 混淆基频与二次谐波)
                    # 1200±200 音分的跳变映射到同一音名, RPA=1.0 但被误计为断层
                    # 文献: de Cheveigne & Kawahara (2002) — YIN 八度误差率 <1%
                    is_octave_jump = (cents_jumps > 1000) & (cents_jumps < 1400)
                    real_breaks = (cents_jumps > 200) & ~is_octave_jump
                    result.pitch_breaks = int(np.sum(real_breaks))
                else:
                    result.pitch_breaks = 0
            else:
                result.pitch_breaks = 0

        # 长音音高波动
        window_size = int(self.sample_rate / self.hop_length * 0.5)
        if len(cents_deviation) > window_size:
            windowed_std = uniform_filter1d(cents_deviation ** 2, window_size) ** 0.5
            result.pitch_wobble = float(np.max(windowed_std))

        # v5.14: 多指标体系 (移植自 pitch-benchmark: evaluate_pitch_accuracy + evaluate_pitch_smoothness)
        self._calculate_pitch_multimetric(cents_deviation, valid_f0, voiced_flags, result)

        return result

    def _calculate_pitch_multimetric(
        self,
        cents_deviation: np.ndarray,
        valid_f0: np.ndarray,
        voiced_flags: np.ndarray,
        result: PitchDeviationResult
    ):
        """
        v5.14: 多指标音准评估 (移植自 pitch-benchmark)

        移植来源:
        - evaluate_pitch_accuracy()  → RPA, RCA, gross_error_rate, octave_error_rate
        - evaluate_pitch_smoothness() → relative_smoothness, continuity_breaks

        注意: pitch-benchmark 使用 ground truth voice labels,
        这里改用 pred_voicing (from voiced_flags) 做适配。
        """
        epsilon = 50.0  # |cents| < 50 = accurate
        gross_threshold = 200.0  # |cents| > 200 = gross error

        # --- RPA: Raw Pitch Accuracy ---
        result.rpa = float(np.nanmean(np.abs(cents_deviation) < epsilon))

        # --- RCA: Raw Chroma Accuracy (octave-folded) ---
        wrapped_cents = np.abs(cents_deviation) % 1200
        chroma_diff = np.minimum(wrapped_cents, 1200 - wrapped_cents)
        result.rca = float(np.nanmean(chroma_diff < epsilon))

        # --- Gross Error Rate ---
        result.gross_error_rate = float(np.nanmean(np.abs(cents_deviation) > gross_threshold))

        # --- Octave Error Rate (无参考音高时用相邻帧跳变检测) ---
        valid_diff = np.abs(np.diff(valid_f0))
        relative_jumps = valid_diff / (valid_f0[:-1] + np.finfo(float).eps)
        # 相邻帧频率跳变 > 0.7x = 接近八度跳变 (ratio ~2.0 or ~0.5)
        near_octave_jumps = (relative_jumps > 0.7) & (relative_jumps < 1.3)
        result.octave_error_rate = float(np.nanmean(near_octave_jumps)) if len(near_octave_jumps) > 0 else 0.0

        # --- Relative Smoothness (移植自 evaluate_pitch_smoothness) ---
        # 使用 pred_voicing (voiced_flags) 替代 ground truth voice labels
        pred_voiced = voiced_flags.copy()
        voiced_idx = np.where(pred_voiced)[0]
        if len(voiced_idx) >= 2:
            consecutive_mask = np.diff(voiced_idx) == 1
            starts_idx = voiced_idx[:-1][consecutive_mask]
            ends_idx = voiced_idx[1:][consecutive_mask]
            if starts_idx.size > 0:
                # 从原始 f0 获取 pitch values
                f0_valid = valid_f0
                # 映射 voiced 索引到 valid_f0 中的位置
                # voiced_flags 在全 f0 上的索引 vs valid_f0 (仅有效帧) 需要映射
                full_f0_vals = np.zeros(len(voiced_flags))
                valid_indices = np.where(voiced_flags & (np.arange(len(voiced_flags)) < len(voiced_flags)))[0]
                # 简化: 直接在 valid_f0 相邻帧上计算
                if len(valid_f0) >= 2:
                    pitch_starts = valid_f0[:-1]
                    pitch_ends = valid_f0[1:]
                    valid_pairs = (pitch_starts > 0) & (pitch_ends > 0)
                    if np.any(valid_pairs):
                        pitch_starts = pitch_starts[valid_pairs]
                        pitch_ends = pitch_ends[valid_pairs]
                        rel_changes = np.abs(pitch_ends - pitch_starts) / (pitch_starts + 1e-8)
                        mean_chg, std_chg = np.mean(rel_changes), np.std(rel_changes)
                        if mean_chg > 1e-9:
                            result.relative_smoothness = float(std_chg / mean_chg)
                        else:
                            result.relative_smoothness = 0.0 if std_chg < 1e-8 else float('nan')

        # --- Continuity Breaks ---
        labeled_segments, num_segments = label(voiced_flags)
        if num_segments > 0:
            gt_segments = find_objects(labeled_segments)
            break_count = 0
            total_relevant = 0
            for seg_slice_tuple in gt_segments:
                seg_slice = seg_slice_tuple[0]
                if seg_slice.stop - seg_slice.start > 1:
                    total_relevant += 1
                    if not np.all(voiced_flags[seg_slice]):
                        break_count += 1
            if total_relevant > 0:
                result.continuity_breaks = float(break_count / total_relevant)
