"""
评分结果数据传输对象 (DTOs) 和评分器模块

定义评分和诊断结果的数据结构，以及各维度评分器
"""
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class PitchDiagnosis:
    """音准诊断详情"""
    score: float = 0.0
    mae_cents: float = 0.0
    level: str = ""
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class RhythmDiagnosis:
    """节奏诊断详情"""
    score: float = 0.0
    deviation_ratio: float = 0.0
    level: str = ""
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class BreathDiagnosis:
    """气息诊断详情 - v4.1 专业评估"""
    score: float = 0.0
    fluctuation: float = 0.0
    level: str = ""
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    positives: List[str] = field(default_factory=list)  # v5.6: 正面发现

    # v4.1 新增：细分维度得分
    long_note_support: float = 0.0
    dynamic_control: float = 0.0
    breath_design: float = 0.0
    breath_technique: float = 0.0

    # 专业能力标记
    is_artistic: bool = False
    has_controlled_breathiness: bool = False
    long_note_bonus: float = 0.0
    soft_singing_bonus: float = 0.0


@dataclass
class TechniqueDiagnosis:
    """发声技术诊断详情"""
    score: float = 0.0
    hnr: float = 0.0
    cpp: float = 0.0
    vibrato_quality: float = 0.0
    level: str = ""
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    is_mixed_audio: bool = False


@dataclass
class ArtistryDiagnosis:
    """艺术表现诊断详情"""
    score: float = 0.0
    emotion_score: float = 0.0
    dynamics_score: float = 0.0
    level: str = ""
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class ScoreResultV4:
    """评分结果 v5.0 - 深度学习增强"""
    # 五维评分
    pitch_score: float = 0.0
    rhythm_score: float = 0.0
    breath_score: float = 0.0
    technique_score: float = 0.0
    artistry_score: float = 0.0

    # 总分与等级
    total_score: float = 0.0
    level: str = ""
    grade: str = ""
    stars: str = ""
    color: str = ""

    # 详细诊断
    pitch_diagnosis: PitchDiagnosis = field(default_factory=PitchDiagnosis)
    rhythm_diagnosis: RhythmDiagnosis = field(default_factory=RhythmDiagnosis)
    breath_diagnosis: BreathDiagnosis = field(default_factory=BreathDiagnosis)
    technique_diagnosis: TechniqueDiagnosis = field(default_factory=TechniqueDiagnosis)
    artistry_diagnosis: ArtistryDiagnosis = field(default_factory=ArtistryDiagnosis)

    # 底线规则
    critical_issues: List[str] = field(default_factory=list)
    is_disqualified: bool = False

    # v5.0 深度学习增强
    dl_mos_score: float = 0.0
    dl_mos_normalized: float = 0.0
    dl_method: str = "none"
    dl_confidence: float = 0.0

    # 兼容旧接口
    volume: float = 0.0
    pitch: float = 0.0
    rhythm: float = 0.0
    breath: float = 0.0
    emotion: float = 0.0
    total: float = 0.0
    penalties: Dict[str, float] = field(default_factory=dict)


# 向后兼容别名
ScoreResult = ScoreResultV4


# 导出评分器
from .pitch_scorer import PitchScorer
from .rhythm_scorer import RhythmScorer
from .breath_scorer import BreathScorer
from .technique_scorer import TechniqueScorer
from .artistry_scorer import ArtistryScorer
from .critical_rules import CriticalRulesHandler

__all__ = [
    # DTOs
    'PitchDiagnosis',
    'RhythmDiagnosis',
    'BreathDiagnosis',
    'TechniqueDiagnosis',
    'ArtistryDiagnosis',
    'ScoreResultV4',
    'ScoreResult',
    # Scorers
    'PitchScorer',
    'RhythmScorer',
    'BreathScorer',
    'TechniqueScorer',
    'ArtistryScorer',
    'CriticalRulesHandler',
]