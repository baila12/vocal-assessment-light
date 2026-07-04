"""
Voicing Detection 评估模块 v5.18

评估 PYIN 基频检测的 voicing 决策质量。
使用自一致性检查 (无 ground truth 依赖) 评估:
1. 人声范围合规率 (65-1047Hz)
2. 八度跳跃检测 (常见 PYIN 错误模式)
3. 清/浊音切换一致性 (避免快速抖动)
4. 能量-基频一致性 (高能量低 f0 → 可能误检测)

输出诊断指标，帮助判断 f0 提取质量:
- detection_confidence: 整体置信度 (0-1)
- voicing_ratio: 有效有声帧比例
- octave_jump_rate: 八度跳跃发生率
- consistency_score: 切换一致性 (0-100)

当 enable_voicing_detection=True 时:
  - 评估指标写入日志
  - 低置信度 (<0.3) 自动触发 TorchCREPE fallback (如已启用)
"""
from dataclasses import dataclass
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class VoicingDetectionResult:
    """Voicing 检测评估结果"""
    voiced_frame_count: int = 0      # 有效有声帧数
    total_frame_count: int = 0       # 总帧数
    voicing_ratio: float = 0.0       # 有声帧比例
    detection_confidence: float = 0.0  # 整体置信度 (0-1)
    octave_jump_rate: float = 0.0    # 八度跳跃率
    consistency_score: float = 0.0   # 切换一致性 (0-100)
    energy_voicing_agreement: float = 0.0  # 能量-基频一致性 (0-1)


class VoicingDetector:
    """
    Voicing 检测质量评估器

    使用自一致性方法评估 PYIN 的 voiced/unvoiced 决策质量。
    不需要 ground truth 标签，仅依赖信号自身特性。

    检查维度:
    1. 人声范围: f0 是否在 65-1047Hz (C2-C6)
    2. 八度跳跃: 相邻有声帧 f0 比值是否 > 1.8 (半八度以上)
    3. 切换一致性: 避免 < 3帧的短时清/浊切换 (噪声)
    4. 能量一致性: 高 RMS 低 f0 → 可能将低音乐器误判为人声
    """

    def __init__(self, sample_rate: int = 22050, hop_length: int = 512):
        """
        初始化 Voicing 检测评估器

        Args:
            sample_rate: 采样率
            hop_length: 帧移
        """
        self.sample_rate = sample_rate
        self.hop_length = hop_length

        # 人声范围
        self.f0_min = 65.0   # C2
        self.f0_max = 1047.0 # C6

        # 八度跳跃阈值 (f0 变化 > 1.8x 视为跳跃)
        self.octave_jump_ratio = 1.8

        # 短时切换阈值 (帧)
        self.min_voiced_duration = 3
        self.min_unvoiced_duration = 3

    def evaluate(
        self,
        f0: np.ndarray,
        voiced_flags: np.ndarray,
        rms: np.ndarray = None
    ) -> VoicingDetectionResult:
        """
        评估 voicing 检测质量

        Args:
            f0: 基频序列 (NaN = unvoiced)
            voiced_flags: PYIN 的 voiced 标记
            rms: RMS 能量序列 (可选, 用于能量一致性检查)

        Returns:
            VoicingDetectionResult: 评估指标
        """
        if len(f0) == 0:
            return VoicingDetectionResult()

        try:
            result = VoicingDetectionResult()
            result.total_frame_count = len(f0)

            # 1. 基本计数
            valid_voiced = voiced_flags & ~np.isnan(f0)
            result.voiced_frame_count = int(np.sum(valid_voiced))
            result.voicing_ratio = float(
                result.voiced_frame_count / max(result.total_frame_count, 1)
            )

            if result.voiced_frame_count == 0:
                result.detection_confidence = 0.0
                return result

            # 2. 人声范围合规率
            valid_f0 = f0[valid_voiced]
            in_range = (valid_f0 >= self.f0_min) & (valid_f0 <= self.f0_max)
            range_compliance = float(np.mean(in_range))

            # 3. 八度跳跃率
            octave_jump_rate = self._compute_octave_jump_rate(f0, voiced_flags)

            # 4. 切换一致性
            consistency_score = self._compute_consistency(voiced_flags)

            # 5. 能量-基频一致性 (如果提供了 RMS)
            energy_agreement = 1.0  # 默认满分
            if rms is not None and len(rms) == len(f0):
                energy_agreement = self._compute_energy_agreement(f0, voiced_flags, rms)

            # 综合置信度: 加权平均
            result.detection_confidence = float(
                0.30 * range_compliance +
                0.20 * (1.0 - min(octave_jump_rate, 1.0)) +
                0.25 * (consistency_score / 100.0) +
                0.25 * energy_agreement
            )
            result.detection_confidence = max(0.0, min(1.0, result.detection_confidence))

            result.octave_jump_rate = float(octave_jump_rate)
            result.consistency_score = float(consistency_score)
            result.energy_voicing_agreement = float(energy_agreement)

            logger.debug(
                f"Voicing 评估: confidence={result.detection_confidence:.2f}, "
                f"voicing_ratio={result.voicing_ratio:.2f}, "
                f"octave_jumps={result.octave_jump_rate:.2f}, "
                f"consistency={result.consistency_score:.0f}"
            )

            return result

        except Exception as e:
            logger.warning(f"Voicing 评估失败: {e}")
            return VoicingDetectionResult()

    def _compute_octave_jump_rate(
        self, f0: np.ndarray, voiced_flags: np.ndarray
    ) -> float:
        """计算八度跳跃率 (矢量化版本)"""
        voiced_indices = np.where(voiced_flags & ~np.isnan(f0))[0]
        if len(voiced_indices) < 2:
            return 0.0

        # 矢量化: 相邻有声帧的间隔和 f0 比值
        gaps = np.diff(voiced_indices)
        adjacent_mask = gaps <= 3

        if not np.any(adjacent_mask):
            return 0.0

        # 相邻帧对: indices[i] 和 indices[i+1] where gap <= 3
        adj_pairs = np.where(adjacent_mask)[0]
        ratios = f0[voiced_indices[adj_pairs + 1]] / np.maximum(
            f0[voiced_indices[adj_pairs]], 1e-6
        )
        jumps = np.sum(
            (ratios > self.octave_jump_ratio) |
            (ratios < (1.0 / self.octave_jump_ratio))
        )

        return float(jumps / max(len(voiced_indices) - 1, 1))

    def _compute_consistency(self, voiced_flags: np.ndarray) -> float:
        """
        计算清/浊切换一致性 (0-100)

        修复 v5.18 review bugs:
        - 时长计算使用 offset-onset+1 (正确帧数)
        - 初始未计段 (索引0到首个onset) 和末尾段 (末个offset到末尾) 纳入统计
        """
        n_frames = len(voiced_flags)
        if n_frames < 2:
            return 0.0

        transitions = np.diff(voiced_flags.astype(int))
        onset_indices = np.where(transitions == 1)[0]   # unvoiced → voiced
        offset_indices = np.where(transitions == -1)[0]  # voiced → unvoiced

        short_segments = 0
        total_segments = 0

        # 处理初始段 (索引0到首个 onset 或首个 offset)
        all_transitions = np.sort(np.concatenate([onset_indices, offset_indices]))
        if len(all_transitions) > 0:
            first_transition = all_transitions[0]
            if first_transition > 0:
                total_segments += 1
                duration = first_transition + 1  # frame 0 to first_transition inclusive
                is_voiced = voiced_flags[0]
                min_dur = self.min_voiced_duration if is_voiced else self.min_unvoiced_duration
                if duration < min_dur:
                    short_segments += 1

        # 有声段分析 (onset → next offset)
        for onset in onset_indices:
            total_segments += 1
            next_offsets = offset_indices[offset_indices > onset]
            if len(next_offsets) > 0:
                # 时长 = 段内帧数 = (offset_idx - onset_idx + 1)
                duration = next_offsets[0] - onset + 1
                if duration < self.min_voiced_duration:
                    short_segments += 1

        # 无声段分析 (offset → next onset)
        for offset in offset_indices:
            total_segments += 1
            next_onsets = onset_indices[onset_indices > offset]
            if len(next_onsets) > 0:
                duration = next_onsets[0] - offset + 1
                if duration < self.min_unvoiced_duration:
                    short_segments += 1

        # 处理末尾段 (末个 transition 到末尾)
        if len(all_transitions) > 0:
            last_transition = all_transitions[-1]
            if last_transition < n_frames - 1:
                total_segments += 1
                duration = n_frames - last_transition
                is_voiced = voiced_flags[-1]
                min_dur = self.min_voiced_duration if is_voiced else self.min_unvoiced_duration
                if duration < min_dur:
                    short_segments += 1

        if total_segments == 0:
            return 100.0

        consistency = 100.0 * (1.0 - short_segments / max(total_segments, 1))
        return max(0.0, consistency)

    def _compute_energy_agreement(
        self, f0: np.ndarray, voiced_flags: np.ndarray, rms: np.ndarray
    ) -> float:
        """计算能量-基频一致性 (矢量化版本)"""
        if len(rms) < 2:
            return 1.0

        rms_median = np.median(rms)
        total_voiced = max(np.sum(voiced_flags), 1)

        # 矢量化: 高能量 + 低 f0 → 可能误判为乐器
        suspicious_mask = (
            voiced_flags
            & ~np.isnan(f0)
            & (rms > rms_median * 1.5)
            & (f0 < 100)
        )
        suspicious_frames = int(np.sum(suspicious_mask))

        agreement = 1.0 - (suspicious_frames / total_voiced)
        return max(0.0, agreement)
