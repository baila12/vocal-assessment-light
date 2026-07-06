"""
评分结果数据传输对象 (DTOs)

从 __init__.py 分离，消除与子模块的循环导入
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
    positives: List[str] = field(default_factory=list)
    long_note_support: float = 0.0
    dynamic_control: float = 0.0
    breath_design: float = 0.0
    breath_technique: float = 0.0
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
    positives: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class ScoreResultV4:
    """评分结果 v5.0 - 深度学习增强"""
    pitch_score: float = 0.0
    rhythm_score: float = 0.0
    breath_score: float = 0.0
    technique_score: float = 0.0
    artistry_score: float = 0.0
    total_score: float = 0.0
    level: str = ""
    grade: str = ""
    stars: str = ""
    color: str = ""
    pitch_diagnosis: PitchDiagnosis = field(default_factory=PitchDiagnosis)
    rhythm_diagnosis: RhythmDiagnosis = field(default_factory=RhythmDiagnosis)
    breath_diagnosis: BreathDiagnosis = field(default_factory=BreathDiagnosis)
    technique_diagnosis: TechniqueDiagnosis = field(default_factory=TechniqueDiagnosis)
    artistry_diagnosis: ArtistryDiagnosis = field(default_factory=ArtistryDiagnosis)
    critical_issues: List[str] = field(default_factory=list)
    is_disqualified: bool = False
    dl_mos_score: float = 0.0
    dl_mos_normalized: float = 0.0
    dl_method: str = "none"
    dl_confidence: float = 0.0
    volume: float = 0.0
    pitch: float = 0.0
    rhythm: float = 0.0
    breath: float = 0.0
    emotion: float = 0.0
    total: float = 0.0
    penalties: Dict[str, float] = field(default_factory=dict)


# 向后兼容别名
ScoreResult = ScoreResultV4