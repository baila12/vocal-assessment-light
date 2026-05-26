"""
逐帧偏差计算器

计算对齐后的逐帧偏差：
- 音准偏差 (cents)
- 节奏偏差 (ms)
- 音量偏差 (%)
- 气息稳定性

输出问题帧标记，用于可视化标注
"""

import numpy as np
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FrameDeviation:
    """单帧偏差"""
    frame_idx: int
    time: float              # 时间 (秒)
    pitch_cents: float       # 音准偏差 (音分)
    rhythm_ms: float         # 节奏偏差 (毫秒)
    volume_percent: float    # 音量偏差 (百分比)
    breath_stability: float  # 气息稳定性 (0-1)

    # 问题标记
    problem_type: Optional[str] = None  # pitch_high, pitch_low, rhythm_fast, rhythm_slow, breath_unstable


@dataclass
class DeviationResult:
    """偏差计算结果"""
    frames: List[FrameDeviation]
    avg_pitch_cents: float
    max_pitch_cents: float
    avg_rhythm_ms: float
    avg_volume_percent: float
    avg_breath_stability: float
    problem_frames: List[FrameDeviation]  # 有问题的帧


class DeviationCalculator:
    """
    逐帧偏差计算器

    基于DTW对齐路径计算各维度偏差
    """

    # 偏差阈值
    PITCH_THRESHOLD_MINOR = 20      # 音分，小问题
    PITCH_THRESHOLD_MAJOR = 50      # 音分，大问题
    RHYTHM_THRESHOLD_MINOR = 50     # 毫秒，小问题
    RHYTHM_THRESHOLD_MAJOR = 150    # 毫秒，大问题
    BREATH_STABILITY_THRESHOLD = 0.7  # 气息稳定性阈值

    def __init__(self, sample_rate: int = 22050, hop_length: int = 512):
        self.sample_rate = sample_rate
        self.hop_length = hop_length
        self.frame_duration = hop_length / sample_rate  # 约23ms

    def calculate(
        self,
        std_pitch: np.ndarray,
        user_pitch: np.ndarray,
        std_energy: np.ndarray,
        user_energy: np.ndarray,
        warp_path: np.ndarray,
        std_times: Optional[np.ndarray] = None,
        user_times: Optional[np.ndarray] = None
    ) -> DeviationResult:
        """
        计算逐帧偏差

        Args:
            std_pitch: 标准音频基频
            user_pitch: 用户音频基频
            std_energy: 标准音频能量
            user_energy: 用户音频能量
            warp_path: DTW对齐路径 [(std_idx, user_idx), ...]
            std_times: 标准音频时间轴
            user_times: 用户音频时间轴

        Returns:
            DeviationResult
        """
        frames = []
        problem_frames = []

        for i, (std_idx, user_idx) in enumerate(warp_path):
            std_idx = int(std_idx)
            user_idx = int(user_idx)

            # 边界检查
            if std_idx >= len(std_pitch) or user_idx >= len(user_pitch):
                continue
            if std_idx >= len(std_energy) or user_idx >= len(user_energy):
                continue

            # 计算音准偏差
            pitch_cents = self._calculate_pitch_cents(
                std_pitch[std_idx],
                user_pitch[user_idx]
            )

            # 计算音量偏差
            volume_percent = self._calculate_volume_percent(
                std_energy[std_idx],
                user_energy[user_idx]
            )

            # 计算节奏偏差（基于对齐路径的时间差）
            rhythm_ms = self._calculate_rhythm_ms(i, warp_path)

            # 计算气息稳定性（基于局部能量方差）
            breath_stability = self._calculate_breath_stability(
                user_energy, user_idx
            )

            # 时间
            time = std_times[std_idx] if std_times is not None and std_idx < len(std_times) else i * self.frame_duration

            # 创建帧偏差对象
            frame = FrameDeviation(
                frame_idx=i,
                time=time,
                pitch_cents=pitch_cents,
                rhythm_ms=rhythm_ms,
                volume_percent=volume_percent,
                breath_stability=breath_stability
            )

            # 检测问题类型
            frame.problem_type = self._detect_problem(frame)
            if frame.problem_type:
                problem_frames.append(frame)

            frames.append(frame)

        # 计算统计指标
        if not frames:
            return DeviationResult(
                frames=[],
                avg_pitch_cents=0.0,
                max_pitch_cents=0.0,
                avg_rhythm_ms=0.0,
                avg_volume_percent=0.0,
                avg_breath_stability=0.0,
                problem_frames=[]
            )

        pitch_cents_list = [abs(f.pitch_cents) for f in frames if not np.isnan(f.pitch_cents)]
        rhythm_ms_list = [abs(f.rhythm_ms) for f in frames]
        volume_list = [abs(f.volume_percent) for f in frames]
        breath_list = [f.breath_stability for f in frames]

        return DeviationResult(
            frames=frames,
            avg_pitch_cents=np.mean(pitch_cents_list) if pitch_cents_list else 0.0,
            max_pitch_cents=np.max(pitch_cents_list) if pitch_cents_list else 0.0,
            avg_rhythm_ms=np.mean(rhythm_ms_list) if rhythm_ms_list else 0.0,
            avg_volume_percent=np.mean(volume_list) if volume_list else 0.0,
            avg_breath_stability=np.mean(breath_list) if breath_list else 0.0,
            problem_frames=problem_frames
        )

    def _calculate_pitch_cents(self, std_freq: float, user_freq: float) -> float:
        """
        计算音分偏差

        Args:
            std_freq: 标准频率 (Hz)
            user_freq: 用户频率 (Hz)

        Returns:
            音分偏差 (正数表示偏高，负数表示偏低)
        """
        # 无效值处理
        if std_freq <= 0 or user_freq <= 0:
            return 0.0

        # 计算音分
        # cents = 1200 * log2(user_freq / std_freq)
        with np.errstate(divide='ignore', invalid='ignore'):
            cents = 1200 * np.log2(user_freq / std_freq)

        if np.isnan(cents) or np.isinf(cents):
            return 0.0

        return float(cents)

    def _calculate_volume_percent(self, std_energy: float, user_energy: float) -> float:
        """
        计算音量偏差百分比

        Args:
            std_energy: 标准能量 (dB)
            user_energy: 用户能量 (dB)

        Returns:
            音量偏差百分比 (正数表示偏大)
        """
        # dB差值转换为百分比
        # 3dB 约等于 2倍功率
        db_diff = user_energy - std_energy
        percent = (10 ** (db_diff / 10) - 1) * 100

        return float(percent)

    def _calculate_rhythm_ms(self, frame_idx: int, warp_path: np.ndarray) -> float:
        """
        计算节奏偏差

        基于DTW路径的偏离程度

        Args:
            frame_idx: 当前帧索引
            warp_path: 对齐路径

        Returns:
            节奏偏差 (毫秒)
        """
        if frame_idx >= len(warp_path):
            return 0.0

        # 计算当前位置的对角线偏离
        std_idx, user_idx = warp_path[frame_idx]

        # 理想情况下 std_idx 和 user_idx 应该相同
        # 偏离表示节奏差异
        frame_diff = std_idx - user_idx

        # 转换为毫秒
        ms_diff = frame_diff * self.frame_duration * 1000

        return float(ms_diff)

    def _calculate_breath_stability(
        self,
        energy: np.ndarray,
        center_idx: int,
        window_size: int = 10
    ) -> float:
        """
        计算气息稳定性

        基于局部能量的变异系数

        Args:
            energy: 能量序列
            center_idx: 中心索引
            window_size: 窗口大小

        Returns:
            气息稳定性 (0-1)
        """
        start = max(0, center_idx - window_size)
        end = min(len(energy), center_idx + window_size)

        if end - start < 2:
            return 1.0

        local_energy = energy[start:end]

        # 计算变异系数
        mean = np.mean(local_energy)
        if mean < 1e-6:
            return 1.0

        std = np.std(local_energy)
        cv = std / mean  # 变异系数

        # 归一化到 0-1
        # cv 越小，稳定性越高
        stability = max(0, min(1, 1 - cv / 0.5))

        return float(stability)

    def _detect_problem(self, frame: FrameDeviation) -> Optional[str]:
        """
        检测问题类型

        Args:
            frame: 帧偏差

        Returns:
            问题类型字符串或None
        """
        # 音准问题
        if abs(frame.pitch_cents) > self.PITCH_THRESHOLD_MAJOR:
            if frame.pitch_cents > 0:
                return 'pitch_high'
            else:
                return 'pitch_low'
        elif abs(frame.pitch_cents) > self.PITCH_THRESHOLD_MINOR:
            if frame.pitch_cents > 0:
                return 'pitch_high_minor'
            else:
                return 'pitch_low_minor'

        # 节奏问题
        if abs(frame.rhythm_ms) > self.RHYTHM_THRESHOLD_MAJOR:
            if frame.rhythm_ms > 0:
                return 'rhythm_slow'
            else:
                return 'rhythm_fast'

        # 气息问题
        if frame.breath_stability < self.BREATH_STABILITY_THRESHOLD:
            return 'breath_unstable'

        return None
