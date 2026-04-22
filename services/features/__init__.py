"""
音频特征数据传输对象 (DTOs) 和分析器模块

定义音频特征提取结果的统一数据结构，以及各维度分析器
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PitchDeviationResult:
    """音分偏差分析结果"""
    mae_cents: float = 0.0
    max_cents: float = 0.0
    consecutive_off_notes: int = 0
    pitch_breaks: int = 0
    pitch_wobble: float = 0.0
    detection_rate: float = 0.0
    valid_frame_count: int = 0


@dataclass
class RhythmAlignmentResult:
    """节拍对齐分析结果"""
    avg_deviation_ratio: float = 0.0
    max_deviation_ratio: float = 0.0
    off_beat_segments: int = 0
    beats_per_second: float = 0.0
    onset_count: int = 0
    irregularity: float = 0.0


@dataclass
class BreathStabilityResult:
    """气息稳定性分析结果 - v4.1 专业气息评估"""
    # 基础指标
    rms_fluctuation: float = 0.0
    long_note_decay: float = 0.0
    breath_breaks: int = 0
    dynamic_range: float = 0.0
    sustain_quality: float = 0.0

    # v4.1 新增：专业气息评估细分维度
    # 1. 长音气息支撑稳定性 (40%)
    long_note_support_score: float = 0.0  # 长音气息支撑得分
    long_note_count: int = 0              # 长音数量
    long_note_avg_quality: float = 0.0    # 长音平均质量
    harmonic_stability: float = 0.0       # 泛音保持度
    pitch_stability_long: float = 0.0     # 长音基频稳定度

    # 2. 强弱动态的气息可控性 (25%)
    dynamic_control_score: float = 0.0    # 强弱控制得分
    soft_singing_quality: float = 0.0     # 弱唱质量
    crescendo_quality: float = 0.0        # 渐强渐弱质量
    soft_segment_count: int = 0           # 弱唱片段数

    # 3. 气口设计与乐句气息分配 (20%)
    breath_design_score: float = 0.0      # 气口设计得分
    clean_breath_count: int = 0           # 无痕换气次数
    phrase_coherence: float = 0.0         # 乐句连贯性

    # 4. 气声/气息技巧的精准运用 (15%)
    breath_technique_score: float = 0.0   # 气声技巧得分
    controlled_breathiness: float = 0.0   # 可控气声比例
    uncontrolled_leak: float = 0.0        # 无效漏气比例

    # 综合评估
    is_artistic_fluctuation: bool = False  # 是否为艺术化起伏
    professional_breath_score: float = 0.0  # 专业气息综合得分


@dataclass
class VocalTechniqueResult:
    """演唱技巧检测结果"""
    vibrato_count: int = 0
    vibrato_rate_avg: float = 0.0
    vibrato_extent_avg: float = 0.0
    vibrato_quality: float = 0.0
    slide_count: int = 0
    falsetto_segments: int = 0
    technique_score: float = 0.0


@dataclass
class AudioFeaturesResult:
    """音频特征提取综合结果"""
    success: bool = True
    pitch_deviation: PitchDeviationResult = field(default_factory=PitchDeviationResult)
    rhythm_alignment: RhythmAlignmentResult = field(default_factory=RhythmAlignmentResult)
    breath_stability: BreathStabilityResult = field(default_factory=BreathStabilityResult)
    vocal_technique: VocalTechniqueResult = field(default_factory=VocalTechniqueResult)
    hnr: float = 0.0
    cpp: float = 0.0
    error_message: Optional[str] = None


# 导出分析器
from .pitch import PitchAnalyzer
from .rhythm import RhythmAnalyzer
from .breath import BreathAnalyzer
from .technique import TechniqueAnalyzer
from .acoustic import AcousticAnalyzer

__all__ = [
    # DTOs
    'PitchDeviationResult',
    'RhythmAlignmentResult',
    'BreathStabilityResult',
    'VocalTechniqueResult',
    'AudioFeaturesResult',
    # Analyzers
    'PitchAnalyzer',
    'RhythmAnalyzer',
    'BreathAnalyzer',
    'TechniqueAnalyzer',
    'AcousticAnalyzer',
]
