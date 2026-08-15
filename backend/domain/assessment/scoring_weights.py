"""
六维权重值对象 — 权重的单一数据来源 (v7.11)

背景:
    v7.4 前权重硬编码在每个 Score.weighted() 方法里 (13/12/22/25/15/13)。
    为支持"评分权重可配置" (scoring-config.feature: 风格预设 + 用户自定义),
    将权重收敛为 ScoringWeights 值对象, 提供:
    - 默认权重 (v7.4 定稿) + 命名风格预设
    - 校验 (总和 100% + 单维 ≤50% + 非负)
    - 加权聚合 weighted_total() (不含音色)
    - 序列化 to_dict/from_dict (API + 前端滑块联动)

设计原则:
    - frozen=True 不可变 (符合领域值对象规范)
    - 权重的唯一权威来源 — Score.weighted() 委托到 ScoringWeights.default()
    - 维度内部子权重 (如 pitch MAE 40%) 不在此处, 属于各 scorer
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from backend.domain.assessment.errors import DomainError

# 权重校验误差容限 (浮点求和)
_EPSILON = 1e-9


class WeightsValidationError(DomainError):
    """权重配置校验失败 — 总和/单维上限/非负 任一不满足"""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"无效的评分权重: {reason}")


@dataclass(frozen=True)
class ScoringWeights:
    """六维权重 — 各值 ∈ [0, 0.5], 总和 = 1.0"""

    pitch: float
    rhythm: float
    breath: float
    technique: float
    muscle: float
    artistry: float

    # ============================================================
    # 工厂方法
    # ============================================================

    @classmethod
    def default(cls) -> "ScoringWeights":
        """默认权重 — v7.4 定稿 13/12/22/25/15/13.

        v7.4 依据: muscle 25%→15% (双文献建议, 启发式降权),
        释放 10% 分给 pitch(+3%)/rhythm(+2%)/breath(+2%)/artistry(+3%)。
        """
        return cls(pitch=0.13, rhythm=0.12, breath=0.22,
                   technique=0.25, muscle=0.15, artistry=0.13)

    # ============================================================
    # 风格预设 (scoring-config.feature 契约, 6 维适配)
    # ============================================================

    @classmethod
    def pop(cls) -> "ScoringWeights":
        """流行 — 均衡, 艺术表现权重较高.

        来源: feature 5 维 25/20/15/20/20 ×0.85 + muscle 15% (保持默认启发式权重)。
        """
        return cls(pitch=0.21, rhythm=0.17, breath=0.13,
                   technique=0.17, muscle=0.15, artistry=0.17)

    @classmethod
    def bel_canto(cls) -> "ScoringWeights":
        """美声 — 偏重音准和气息, 节奏次之 (feature 30/15/25/20/10 适配)."""
        return cls(pitch=0.25, rhythm=0.13, breath=0.21,
                   technique=0.17, muscle=0.15, artistry=0.09)

    @classmethod
    def ethnic(cls) -> "ScoringWeights":
        """民族 — 五维均衡, 音准略高 (feature 28/18/18/18/18 适配)."""
        return cls(pitch=0.24, rhythm=0.15, breath=0.15,
                   technique=0.15, muscle=0.15, artistry=0.16)

    @classmethod
    def rap(cls) -> "ScoringWeights":
        """说唱 — 节奏和艺术表现是核心, 音准次要 (feature 10/35/10/15/30 适配)."""
        return cls(pitch=0.08, rhythm=0.30, breath=0.09,
                   technique=0.13, muscle=0.15, artistry=0.25)

    @classmethod
    def presets(cls) -> dict[str, "ScoringWeights"]:
        """全部风格预设 {名称: 权重} — 默认使用 pop (feature 契约)."""
        return {
            "pop": cls.pop(),
            "bel_canto": cls.bel_canto(),
            "ethnic": cls.ethnic(),
            "rap": cls.rap(),
        }

    @classmethod
    def default_preset_name(cls) -> str:
        """scoring-config.feature: 默认使用 "流行" 预设 (如用户未指定)."""
        return "pop"

    @classmethod
    def from_preset(cls, name: str) -> "ScoringWeights":
        """按名称取预设 — 未知预设抛 WeightsValidationError."""
        if name not in cls.presets():
            raise WeightsValidationError(f"未知风格预设: {name}")
        return cls.presets()[name]

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> "ScoringWeights":
        """从 dict 构造并立即校验 — 系统边界入口 (API/前端)."""
        w = cls(
            pitch=float(data["pitch"]),
            rhythm=float(data["rhythm"]),
            breath=float(data["breath"]),
            technique=float(data["technique"]),
            muscle=float(data["muscle"]),
            artistry=float(data["artistry"]),
        )
        w.validate()
        return w

    # ============================================================
    # 校验
    # ============================================================

    def sum(self) -> float:
        return (self.pitch + self.rhythm + self.breath
                + self.technique + self.muscle + self.artistry)

    def validate(self) -> "ScoringWeights":
        """校验: 总和 = 100%, 单维 ∈ [0, 50%], 全部有限值, 返回 self 便于链式调用."""
        for name, w in self.components():
            # v7.19 整理: 先拒绝非有限值 (NaN/±Inf) — NaN 使 <0.0/>0.5/abs(sum-1) 三检查
            # 全为 False 而绕过校验, 导致 weighted_total 产出 NaN 总分
            if not math.isfinite(w):
                raise WeightsValidationError(f"[{name}] 权重必须为有限数值, 当前: {w}")
            if w < 0.0:
                raise WeightsValidationError(f"[{name}] 权重不能为负: {w}")
            if w > 0.5:
                raise WeightsValidationError(
                    f"[{name}] 单个维度权重不能超过 50%, 当前 {w * 100:.0f}%")
        if abs(self.sum() - 1.0) > _EPSILON:
            raise WeightsValidationError(
                f"权重总和必须为 100%, 当前为 {self.sum() * 100:.1f}%")
        return self

    # ============================================================
    # 聚合
    # ============================================================

    def weighted_total(
        self,
        pitch, rhythm, breath, technique, muscle, artistry,
    ) -> float:
        """六维加权总分 (不含音色加减分).

        各参数为对应 Score 值对象 (需有 .raw_score 属性).
        权重已保证总和 = 1.0, 输入分数 ∈ [0,100] ⇒ 结果天然 ∈ [0,100]。
        """
        return (
            pitch.raw_score * self.pitch
            + rhythm.raw_score * self.rhythm
            + breath.raw_score * self.breath
            + technique.raw_score * self.technique
            + muscle.raw_score * self.muscle
            + artistry.raw_score * self.artistry
        )

    def weighted_total_from_scores(self, scores: dict[str, float]) -> float:
        """从原始分数字典计算加权总分 — API apply-weights 纯重算用.

        scores 键: pitch/rhythm/breath/technique/muscle/artistry (0-100).
        """
        return (
            scores["pitch"] * self.pitch
            + scores["rhythm"] * self.rhythm
            + scores["breath"] * self.breath
            + scores["technique"] * self.technique
            + scores["muscle"] * self.muscle
            + scores["artistry"] * self.artistry
        )

    # ============================================================
    # 序列化
    # ============================================================

    def to_dict(self) -> dict[str, float]:
        return {
            "pitch": self.pitch,
            "rhythm": self.rhythm,
            "breath": self.breath,
            "technique": self.technique,
            "muscle": self.muscle,
            "artistry": self.artistry,
        }

    def components(self) -> list[tuple[str, float]]:
        """[(维度名, 权重)] — 校验与前端展示共用."""
        return [
            ("pitch", self.pitch),
            ("rhythm", self.rhythm),
            ("breath", self.breath),
            ("technique", self.technique),
            ("muscle", self.muscle),
            ("artistry", self.artistry),
        ]
