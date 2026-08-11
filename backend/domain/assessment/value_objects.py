"""
评分值对象 — 7 个不可变数据类

每个值对象:
- frozen=True 保证不可变
- 包含 weighted() 方法返回加权贡献分
- 包含原始诊断信息
"""

from __future__ import annotations
from dataclasses import dataclass, field
from backend.shared.domain_types import ScoreValue
from backend.domain.assessment.scoring_weights import ScoringWeights


# ============================================================
# 1. PitchScore — 音准评分 (13% 权重, v7.4)
# ============================================================
@dataclass(frozen=True)
class PitchScore:
    """音准评分 — v6.2 多指标体系: MAE指数衰减(40%)+RPA(25%)+RCA(10%)+Gross Error(15%)+Smoothness(5%)+Octave(5%)"""

    raw_score: ScoreValue
    mae_cents: float
    rpa: float
    rca: float
    gross_error_rate: float
    octave_error_rate: float
    smoothness_cv: float
    detection_rate: float
    pitch_breaks: int
    diagnosis: tuple[str, ...] = ()
    # v7.14 审查 6.3: 评分失败 fallback 时标记 True (默认 False — 真实评分非启发式)
    is_heuristic: bool = False

    def weighted(self) -> float:
        # v7.11: 委托 ScoringWeights 单一数据来源 (v7.4: 13%)
        return self.raw_score * ScoringWeights.default().pitch


# ============================================================
# 2. RhythmScore — 节奏评分 (12% 权重)
# ============================================================
@dataclass(frozen=True)
class RhythmScore:
    """节奏评分 — onset CV + irregularity 惩罚 + is_clean_vocal 重校准"""

    raw_score: ScoreValue
    onset_cv: float
    median_ioi_deviation: float
    irregularity_penalty: float
    is_clean_vocal: bool
    diagnosis: tuple[str, ...] = ()
    is_heuristic: bool = False  # v7.14 审查 6.3: 失败 fallback 标记

    def weighted(self) -> float:
        return self.raw_score * ScoringWeights.default().rhythm  # v7.4: 12%


# ============================================================
# 3. BreathScore — 气息评分 (22% 权重)
# ============================================================
@dataclass(frozen=True)
class BreathScore:
    """气息评分 — v6.3 四子维度连续线性映射"""

    raw_score: ScoreValue
    long_note_support: float
    dynamic_control: float
    breath_design: float
    breath_technique: float
    is_clean_vocal: bool
    hnr_stability: float | None = None
    dynamic_range_db: float = 0.0
    diagnosis: tuple[str, ...] = ()
    is_heuristic: bool = False  # v7.14 审查 6.3: 失败 fallback 标记

    def weighted(self) -> float:
        return self.raw_score * ScoringWeights.default().breath  # v7.4: 22%


# ============================================================
# 4. TechniqueScore — 发声技术评分 (25% 权重)
# ============================================================
@dataclass(frozen=True)
class TechniqueScore:
    """发声技术评分 — vNext: 拆分为咬字(50%)+气声比(50%)"""

    raw_score: ScoreValue
    articulation_clarity: float   # 咬字清晰度
    breath_voice_ratio: float     # 气声比
    hnr_mean: float = 0.0
    cpp_mean: float = 0.0
    diagnosis: tuple[str, ...] = ()
    is_heuristic: bool = False  # v7.14 审查 6.3: 失败 fallback 标记

    def weighted(self) -> float:
        return self.raw_score * ScoringWeights.default().technique  # 25%


# ============================================================
# 5. MuscleStrengthScore — 肌肉力量评分 (NEW, 15% 权重, v7.4)
# ============================================================
@dataclass(frozen=True)
class MuscleStrengthScore:
    """肌肉力量评分 — ⚠️ 启发式代理指标 (非直接生理测量)

    ADR-2: 仅凭麦克风音频，无法直接测量声门下压和身体肌肉力量。
    使用代理指标间接估算，置信度为"中"级别。
    """

    raw_score: ScoreValue
    body_muscle_strength: float    # 身体肌肉 (50%): max_db + low_freq_ratio + rms_decay
    facial_muscle_strength: float  # 面部肌肉 (50%): singers_formant + formant_cluster + overtone
    is_heuristic: bool = True      # ⚠️ 非直接生理测量
    diagnosis: tuple[str, ...] = ()

    def weighted(self) -> float:
        return self.raw_score * ScoringWeights.default().muscle  # v7.4: 15%


# ============================================================
# 6. ArtistryScore — 艺术表现评分 (13% 权重)
# ============================================================
@dataclass(frozen=True)
class ArtistryScore:
    """艺术表现评分 — v6.1 独立声学特征"""

    raw_score: ScoreValue
    vibrato_quality: float
    dynamic_control: float
    phrase_expression: float
    pitch_variation: float
    diagnosis: tuple[str, ...] = ()
    is_heuristic: bool = False  # v7.14 审查 6.3: 失败 fallback 标记

    def weighted(self) -> float:
        return self.raw_score * ScoringWeights.default().artistry  # v7.4: 13%


# ============================================================
# 7. TimbreAdjustment — 音色加减分 (不属于六维)
# ============================================================
@dataclass(frozen=True)
class TimbreAdjustment:
    """音色加减分 — ⚠️ 启发式代理指标

    最多 +3 / 最多 -5 (不对称设计 — 扣分比加分重)
    低置信度 (MFCC 聚类纯度 < 0.6) 自动归零
    """

    adjustment: float              # +3 ~ -5
    brightness_score: float
    warmth_score: float
    nasality_score: float
    confidence: float              # MFCC 聚类纯度
    is_heuristic: bool = True
    diagnosis: str | None = None

    def apply(self, total: float) -> float:
        """应用音色调整到总分 — 含置信度门控、不对称上限+3下限-5、和 clamp"""
        if self.confidence < 0.6:
            return max(0.0, min(100.0, total))
        # 安全钳: 确保调整值在 [-5, +3] 范围内
        clamped_adj = max(-5.0, min(3.0, self.adjustment))
        return max(0.0, min(100.0, total + clamped_adj))
