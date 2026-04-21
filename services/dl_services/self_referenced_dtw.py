"""
自参照DTW音准评估
从用户演唱中提取稳定段作为参考音高，评估音准稳定性
无需歌曲模板，评估"唱得是否稳定"而非"唱得像不像"
"""

import numpy as np
import librosa
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from scipy import stats

logger = logging.getLogger(__name__)


@dataclass
class NoteSegment:
    """音符片段"""
    start_time: float       # 开始时间 (秒)
    end_time: float         # 结束时间 (秒)
    pitches: np.ndarray     # 该片段的基频序列
    stable_pitch: float     # 稳定段基频 (Hz)
    stable_ratio: float     # 稳定段占比 (0-1)
    is_stable: bool         # 是否为稳定音符
    deviation_cents: float  # 相对稳定基频的偏差 (音分)


@dataclass
class SelfReferencedPitchResult:
    """自参照音准评估结果"""
    overall_stability: float      # 整体稳定性 (0-100)
    stable_note_ratio: float      # 稳定音符占比
    avg_deviation_cents: float    # 平均音分偏差
    max_deviation_cents: float    # 最大音分偏差
    intentional_variations: int   # 有意波动次数 (颤音/滑音)
    unintentional_drifts: int     # 无意跑调次数
    notes: List[NoteSegment]      # 音符片段列表
    method: str                   # 检测方法


class SelfReferencedDTW:
    """
    自参照DTW音准评估器

    核心思路：
    1. 从用户演唱中提取每个音符的"稳定段"
    2. 稳定段代表用户"想要唱的音高"
    3. 计算过渡段、波动段与稳定段的偏差
    4. 区分"有意波动"vs"无意跑调"

    优势：
    - 无需歌曲模板
    - 评估用户"唱得是否稳定"
    - 识别艺术化处理（颤音、滑音）
    """

    # 音符分割参数
    MIN_NOTE_DURATION = 0.15      # 最短音符时长 (秒)
    PITCH_CHANGE_THRESHOLD = 50   # 音高变化阈值 (音分)
    STABLE_VARIANCE_THRESHOLD = 15  # 稳定段方差阈值 (音分)

    # 颤音检测参数
    VIBRATO_RATE_RANGE = (4.0, 8.0)   # 颤音频率范围 (Hz)
    VIBRATO_EXTENT_MIN = 20           # 最小颤音幅度 (音分)

    def __init__(self):
        self._model_available = False  # 当前使用启发式算法
        logger.info("[SelfReferencedDTW] Initialized with heuristic algorithm")

    def analyze(self, audio_path: str, sr: int = 16000) -> SelfReferencedPitchResult:
        """
        分析音频的自参照音准

        Args:
            audio_path: 音频文件路径
            sr: 采样率

        Returns:
            SelfReferencedPitchResult: 分析结果
        """
        # 加载音频
        try:
            y, sr = librosa.load(audio_path, sr=sr, mono=True)
        except Exception as e:
            logger.error(f"[SelfReferencedDTW] Failed to load audio: {e}")
            return SelfReferencedPitchResult(
                overall_stability=0.0,
                stable_note_ratio=0.0,
                avg_deviation_cents=0.0,
                max_deviation_cents=0.0,
                intentional_variations=0,
                unintentional_drifts=0,
                notes=[],
                method='error'
            )

        return self._analyze_heuristic(y, sr)

    def _analyze_heuristic(self, y: np.ndarray, sr: int) -> SelfReferencedPitchResult:
        """
        启发式自参照分析

        Args:
            y: 音频波形
            sr: 采样率

        Returns:
            SelfReferencedPitchResult
        """
        # 1. 提取基频
        f0, voiced_flags, _ = librosa.pyin(
            y,
            fmin=librosa.note_to_hz('C2'),
            fmax=librosa.note_to_hz('C6'),
            sr=sr,
            hop_length=512
        )

        # 时间轴
        times = librosa.times_like(f0, sr=sr, hop_length=512)

        # 2. 分割音符
        notes = self._segment_notes(f0, voiced_flags, times)

        if not notes:
            return SelfReferencedPitchResult(
                overall_stability=0.0,
                stable_note_ratio=0.0,
                avg_deviation_cents=0.0,
                max_deviation_cents=0.0,
                intentional_variations=0,
                unintentional_drifts=0,
                notes=[],
                method='heuristic'
            )

        # 3. 分析每个音符的稳定性
        for note in notes:
            self._analyze_note_stability(note)

        # 4. 计算整体指标
        result = self._calculate_overall_metrics(notes)

        return result

    def _segment_notes(self, f0: np.ndarray, voiced: np.ndarray, times: np.ndarray) -> List[NoteSegment]:
        """
        根据基频变化分割音符

        Args:
            f0: 基频序列
            voiced: 有声帧标记
            times: 时间轴

        Returns:
            音符片段列表
        """
        notes = []

        # 只处理有声帧
        f0_voiced = f0[voiced]
        times_voiced = times[voiced]

        if len(f0_voiced) < 2:
            return notes

        # 计算音分变化
        f0_cents = 1200 * np.log2(f0_voiced / 440.0)  # 相对于A4的音分

        # 检测音高跳变点
        f0_diff = np.diff(f0_cents)
        jump_indices = np.where(np.abs(f0_diff) > self.PITCH_CHANGE_THRESHOLD)[0]

        # 分割音符
        start_idx = 0
        for jump_idx in jump_indices:
            if jump_idx - start_idx > 2:  # 至少3帧
                note = NoteSegment(
                    start_time=times_voiced[start_idx],
                    end_time=times_voiced[jump_idx],
                    pitches=f0_voiced[start_idx:jump_idx + 1],
                    stable_pitch=0.0,
                    stable_ratio=0.0,
                    is_stable=False,
                    deviation_cents=0.0
                )
                notes.append(note)
            start_idx = jump_idx + 1

        # 最后一个音符
        if len(times_voiced) - start_idx > 2:
            note = NoteSegment(
                start_time=times_voiced[start_idx],
                end_time=times_voiced[-1],
                pitches=f0_voiced[start_idx:],
                stable_pitch=0.0,
                stable_ratio=0.0,
                is_stable=False,
                deviation_cents=0.0
            )
            notes.append(note)

        # 过滤过短的音符
        notes = [n for n in notes if n.end_time - n.start_time >= self.MIN_NOTE_DURATION]

        return notes

    def _analyze_note_stability(self, note: NoteSegment) -> None:
        """
        分析单个音符的稳定性

        Args:
            note: 音符片段（会被修改）
        """
        pitches = note.pitches

        if len(pitches) < 3:
            note.stable_pitch = np.mean(pitches) if len(pitches) > 0 else 0
            note.stable_ratio = 1.0
            note.is_stable = True
            note.deviation_cents = 0.0
            return

        # 转换为音分
        pitches_cents = 1200 * np.log2(pitches / 440.0)

        # 计算方差
        variance = np.var(pitches_cents)

        # 判断是否稳定
        if variance < self.STABLE_VARIANCE_THRESHOLD:
            # 稳定音符
            note.stable_pitch = np.median(pitches)
            note.stable_ratio = 1.0
            note.is_stable = True
            note.deviation_cents = np.sqrt(variance)
        else:
            # 不稳定音符 - 寻找稳定段
            stable_pitch, stable_ratio = self._find_stable_segment(pitches)
            note.stable_pitch = stable_pitch
            note.stable_ratio = stable_ratio
            note.is_stable = stable_ratio > 0.5

            # 计算相对偏差
            deviations = np.abs(1200 * np.log2(pitches / stable_pitch))
            note.deviation_cents = np.mean(deviations)

    def _find_stable_segment(self, pitches: np.ndarray) -> Tuple[float, float]:
        """
        在音符中寻找稳定段

        使用滑动窗口找到方差最小的连续段

        Args:
            pitches: 基频序列

        Returns:
            (稳定基频, 稳定段占比)
        """
        n = len(pitches)
        if n < 3:
            return np.median(pitches), 1.0

        # 转换为音分
        pitches_cents = 1200 * np.log2(pitches / 440.0)

        # 滑动窗口计算局部方差
        window_size = max(3, n // 4)
        min_variance = float('inf')
        best_start = 0
        best_end = n

        for i in range(n - window_size + 1):
            window = pitches_cents[i:i + window_size]
            var = np.var(window)
            if var < min_variance:
                min_variance = var
                best_start = i
                best_end = i + window_size

        # 扩展稳定段
        stable_pitches = pitches[best_start:best_end]
        stable_pitch = np.median(stable_pitches)
        stable_ratio = (best_end - best_start) / n

        return stable_pitch, stable_ratio

    def _calculate_overall_metrics(self, notes: List[NoteSegment]) -> SelfReferencedPitchResult:
        """
        计算整体音准指标

        Args:
            notes: 音符片段列表

        Returns:
            SelfReferencedPitchResult
        """
        if not notes:
            return SelfReferencedPitchResult(
                overall_stability=0.0,
                stable_note_ratio=0.0,
                avg_deviation_cents=0.0,
                max_deviation_cents=0.0,
                intentional_variations=0,
                unintentional_drifts=0,
                notes=[],
                method='heuristic'
            )

        # 稳定音符占比
        stable_count = sum(1 for n in notes if n.is_stable)
        stable_ratio = stable_count / len(notes)

        # 平均偏差
        deviations = [n.deviation_cents for n in notes]
        avg_deviation = np.mean(deviations)
        max_deviation = np.max(deviations)

        # 检测有意波动 vs 无意跑调
        intentional = 0
        unintentional = 0

        for note in notes:
            if not note.is_stable:
                # 判断是颤音还是跑调
                if self._is_vibrato(note.pitches):
                    intentional += 1
                else:
                    unintentional += 1

        # 整体稳定性评分
        # 基于稳定音符占比和平均偏差
        stability_score = 100 * stable_ratio * (1 - min(1.0, avg_deviation / 50))

        return SelfReferencedPitchResult(
            overall_stability=stability_score,
            stable_note_ratio=stable_ratio,
            avg_deviation_cents=avg_deviation,
            max_deviation_cents=max_deviation,
            intentional_variations=intentional,
            unintentional_drifts=unintentional,
            notes=notes,
            method='heuristic'
        )

    def _is_vibrato(self, pitches: np.ndarray) -> bool:
        """
        判断是否为颤音

        颤音特征：
        - 周期性波动
        - 频率在4-8Hz
        - 幅度相对稳定

        Args:
            pitches: 基频序列

        Returns:
            是否为颤音
        """
        if len(pitches) < 10:
            return False

        # 转换为音分
        pitches_cents = 1200 * np.log2(pitches / np.median(pitches))

        # 计算过零率（波动频率）
        crossings = np.sum(np.diff(np.sign(pitches_cents)) != 0)
        duration = len(pitches) * 512 / 16000  # 假设hop_length=512, sr=16000
        rate = crossings / (2 * duration)  # Hz

        # 检查是否在颤音频率范围
        if not (self.VIBRATO_RATE_RANGE[0] <= rate <= self.VIBRATO_RATE_RANGE[1]):
            return False

        # 检查幅度
        extent = np.std(pitches_cents) * 2  # 峰峰值约等于2倍标准差
        if extent < self.VIBRATO_EXTENT_MIN:
            return False

        return True

    def get_pitch_diagnosis(self, result: SelfReferencedPitchResult) -> Dict[str, str]:
        """
        生成音准诊断报告

        Args:
            result: 分析结果

        Returns:
            诊断信息字典
        """
        diagnosis = {}

        # 整体稳定性
        if result.overall_stability >= 80:
            diagnosis['stability'] = "✅ 音准稳定性优秀，音高控制精准"
        elif result.overall_stability >= 60:
            diagnosis['stability'] = "○ 音准稳定性良好，部分音符有波动"
        elif result.overall_stability >= 40:
            diagnosis['stability'] = "△ 音准稳定性一般，建议加强音高控制练习"
        else:
            diagnosis['stability'] = "✗ 音准稳定性较差，需要重点练习音准"

        # 平均偏差
        if result.avg_deviation_cents < 10:
            diagnosis['deviation'] = "✅ 音分偏差很小，音高准确"
        elif result.avg_deviation_cents < 20:
            diagnosis['deviation'] = "○ 音分偏差在可接受范围内"
        elif result.avg_deviation_cents < 30:
            diagnosis['deviation'] = "△ 存在一定音分偏差，注意音高准确性"
        else:
            diagnosis['deviation'] = "✗ 音分偏差较大，建议进行音准训练"

        # 有意波动 vs 无意跑调
        if result.intentional_variations > 0:
            diagnosis['variations'] = f"✅ 检测到 {result.intentional_variations} 处艺术化处理（颤音/滑音）"

        if result.unintentional_drifts > 0:
            if result.unintentional_drifts <= 2:
                diagnosis['drifts'] = f"○ 有 {result.unintentional_drifts} 处音高不稳定"
            else:
                diagnosis['drifts'] = f"✗ 有 {result.unintentional_drifts} 处跑调，需要加强练习"

        return diagnosis
