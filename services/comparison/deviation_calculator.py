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
    # v7.18 P0 (O1): 双端有声 (std 和 user 都 voiced) — 聚合排除无声帧防稀释
    is_voiced: bool = True
    # v7.18 P1 (F2): 八度错误标记 (|raw_cents| > 600) — 独立于折叠后的评分
    octave_error: bool = False


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
    # v7.18 P1 (F2): 八度错误率 (跨八度帧占比) — 诊断/惩罚用, 不影响折叠后评分
    octave_error_rate: float = 0.0
    # v7.18 P1 (F1): 整体速度比 (warp 回归斜率, 相对参考) — tempo 独立报告
    tempo_ratio: float = 1.0


class DeviationCalculator:
    """
    逐帧偏差计算器

    基于DTW对齐路径计算各维度偏差
    """

    # 偏差阈值 — 经验值，未经实验校准
    PITCH_THRESHOLD_MINOR = 20      # 音分，轻微音准问题
    PITCH_THRESHOLD_MAJOR = 50      # 音分，严重音准问题
    RHYTHM_THRESHOLD_MINOR = 50     # 毫秒，轻微节奏偏移
    RHYTHM_THRESHOLD_MAJOR = 150    # 毫秒，严重节奏偏移
    BREATH_STABILITY_THRESHOLD = 0.7  # 气息稳定性阈值 (CV倒数归一化)

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
        user_times: Optional[np.ndarray] = None,
        std_voiced: Optional[np.ndarray] = None,
        user_voiced: Optional[np.ndarray] = None,
    ) -> DeviationResult:
        """
        计算逐帧偏差

        Args:
            std_pitch: 标准音频基频
            user_pitch: 用户音频基频
            std_energy: 标准音频能量
            user_energy: 用户音频能量
            warp_path: DTW对齐路径 [(std_idx, user_idx), ...] (全分辨率索引, v7.18 P0)
            std_times: 标准音频时间轴
            user_times: 用户音频时间轴
            std_voiced: 标准音频 voiced_flags (v7.18 P0 O1, 可选)
            user_voiced: 用户音频 voiced_flags (v7.18 P0 O1, 可选)

        Returns:
            DeviationResult
        """
        frames = []
        problem_frames = []

        # v7.18 P1 (F1): tempo 独立节奏 — 对 warp_path 拟合线性回归 (Molina ε_RMS)。
        # 非 45° 直线 = 整体速度不同 (tempo, 非错误); 残差 = 节拍不准。
        # slope = 整体速度比 (用户相对参考), 独立报告。
        if len(warp_path) >= 3:
            slope, intercept = np.polyfit(
                warp_path[:, 0].astype(float),
                warp_path[:, 1].astype(float),
                1,
            )
        else:
            slope, intercept = 1.0, 0.0
        tempo_ratio = float(slope)

        # v7.18 P1 (F3): 音量动态匹配 — z-score 参数用有声帧统计 (消除录音增益差异,
        # 测动态形状而非绝对电平; 静音帧 -200dB 会拉偏均值/标准差)。
        std_voiced_mask = (np.asarray(std_voiced, dtype=bool) if std_voiced is not None
                           else np.asarray(std_pitch, dtype=float) > 0)
        user_voiced_mask = (np.asarray(user_voiced, dtype=bool) if user_voiced is not None
                            else np.asarray(user_pitch, dtype=float) > 0)
        std_en_sel = std_energy[std_voiced_mask] if std_voiced_mask.any() else std_energy
        user_en_sel = user_energy[user_voiced_mask] if user_voiced_mask.any() else user_energy
        std_en_mean, std_en_std = float(np.mean(std_en_sel)), float(np.std(std_en_sel)) + 1e-6
        user_en_mean, user_en_std = float(np.mean(user_en_sel)), float(np.std(user_en_sel)) + 1e-6

        for i, (std_idx, user_idx) in enumerate(warp_path):
            std_idx = int(std_idx)
            user_idx = int(user_idx)

            # 边界检查
            if std_idx >= len(std_pitch) or user_idx >= len(user_pitch):
                continue
            if std_idx >= len(std_energy) or user_idx >= len(user_energy):
                continue

            # v7.18 P0 (O1): 双端有声判断 (无声帧不计入音准/音量/气息聚合, 防稀释)
            is_voiced = True
            if std_voiced is not None and user_voiced is not None:
                std_v = std_voiced[std_idx] if std_idx < len(std_voiced) else False
                user_v = user_voiced[user_idx] if user_idx < len(user_voiced) else False
                is_voiced = bool(std_v and user_v)

            # 计算音准偏差 (F2: 八度折叠 — 低/高八度用户音级对给分, 不误伤)
            raw_cents = self._calculate_pitch_cents(
                std_pitch[std_idx],
                user_pitch[user_idx]
            )
            pitch_cents = self._fold_octave(raw_cents)  # 映射到 [-600, 600)
            octave_error = bool(abs(raw_cents) > 600.0)  # 单列八度错误信号

            # v7.18 P1 (F3): 音量动态匹配 — z-score 归一化后逐帧差异 (动态形状偏差, 0-~2)
            std_n = (std_energy[std_idx] - std_en_mean) / std_en_std
            user_n = (user_energy[user_idx] - user_en_mean) / user_en_std
            volume_percent = abs(std_n - user_n)

            # v7.18 P1 (F1): 节奏偏差 = 相对回归线的残差 (tempo 独立)
            # 整体速度 (slope) 被剥离; 残差反映"跟不跟得上节拍"
            predicted_user = intercept + slope * std_idx
            rhythm_ms = (user_idx - predicted_user) * self.frame_duration * 1000

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
                breath_stability=breath_stability,
                is_voiced=is_voiced,
                octave_error=octave_error,
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
                problem_frames=[],
                tempo_ratio=tempo_ratio,
            )

        # v7.18 P0 (O1): 聚合只统计双端有声帧 (mir_eval RPA 标准: 分母=有声音帧)。
        # 无声帧 pitch=0 / 音量≈-100% / 气息静音窗=满分 → 会稀释/污染均值。
        voiced_frames = [f for f in frames if f.is_voiced]
        pitch_cents_list = [abs(f.pitch_cents) for f in voiced_frames if not np.isnan(f.pitch_cents)]
        rhythm_ms_list = [abs(f.rhythm_ms) for f in frames]  # 节奏是时间轴度量, 全统计
        volume_list = [abs(f.volume_percent) for f in voiced_frames]
        breath_list = [f.breath_stability for f in voiced_frames]

        # F2: 八度错误率 (跨八度帧占比) — 独立信号, 不并入折叠后音准评分
        octave_error_rate = (
            sum(1 for f in voiced_frames if f.octave_error) / len(voiced_frames)
            if voiced_frames else 0.0
        )

        # v7.18 P2 (S1): 鲁棒聚合 — 中位数替代均值 (崩溃点 0%→50%, 离群帧不拖偏)。
        # 文献: Mauch 2014 (JASA) 用中位绝对偏差; v7.17 六维 rhythm 已用 median+p75-p50。
        return DeviationResult(
            frames=frames,
            avg_pitch_cents=self._robust_median(pitch_cents_list),
            max_pitch_cents=np.max(pitch_cents_list) if pitch_cents_list else 0.0,  # P95 离群单独报
            avg_rhythm_ms=self._robust_median(rhythm_ms_list),
            avg_volume_percent=self._robust_median(volume_list),
            avg_breath_stability=self._robust_median(breath_list),
            problem_frames=problem_frames,
            octave_error_rate=round(octave_error_rate, 4),
            tempo_ratio=round(tempo_ratio, 4),
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

    @staticmethod
    def _robust_median(values) -> float:
        """中位数聚合 — 鲁棒 (崩溃点 50%), 离群帧不拖偏 (v7.18 P2 S1)"""
        if not values:
            return 0.0
        return float(np.median(np.asarray(values, dtype=float)))

    @staticmethod
    def _fold_octave(cents: float) -> float:
        """八度折叠: 音分偏差映射到 [-600, 600) 半八度内 (v7.18 P1 F2)。

        男声低八度/女声高八度翻唱 (1200c 偏差) → 折叠后 ~0 (音级匹配), 消除音域/性别不公平。
        文献: RCA (mir_eval) 用模 12 音级折叠; 男:女 F0 比 0.55-0.66 非整八度,
        %1200 折叠比整八度搬移更稳。八度错误本身由 FrameDeviation.octave_error 单列信号。
        """
        return ((cents + 600.0) % 1200.0) - 600.0

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
        window_size: int = 20
    ) -> float:
        """
        计算动态稳定性 (v7.18 P1 O2: 由"气息"诚实改名为"能量动态稳定性")

        基于局部能量的变异系数 — 注意: 这是能量/音量波动稳定性, 非声学"气息"测量
        (GNE/CPPS/HNR 需分离人声, 见 P2)。v7.18 窗口 10→20 帧 (~0.46s, 更稳)。

        Args:
            energy: 能量序列
            center_idx: 中心索引
            window_size: 窗口大小

        Returns:
            动态稳定性 (0-1)
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
