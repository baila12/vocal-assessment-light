"""
肌肉力量评分器 v7.0 — NEW ⚠️ 启发式代理指标

ADR-2: 仅凭麦克风音频，无法直接测量声门下压和身体肌肉力量。
使用代理指标间接估算，置信度为"中"级别。

代理指标:
  身体肌肉 (50%): max_db + low_freq_ratio + rms_decay
  面部肌肉 (50%): singers_formant + formant_cluster + overtone

v7.3: audiofeat 增强 — soft_phonation/vocal_fry/hammarberg 补充代理指标
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

from backend.domain.assessment.value_objects import MuscleStrengthScore

if TYPE_CHECKING:
    from backend.domain.audio.audiofeat_extractor import AudiofeatFeatures


@dataclass(frozen=True)
class MuscleFeatures:
    """肌肉力量特征输入 — 全部来自麦克风音频代理指标 (不可变)"""
    max_db_level: float = -20.0           # 最大声压级
    low_freq_energy_ratio: float = 0.30   # <500Hz能量比
    rms_decay_rate: float = 1.0           # 长音衰减率 dB/s
    singers_formant_energy: float = 0.0   # 2.5-3.5kHz能量比
    formant_clustering_quality: float = 0.0  # 0-100
    overtone_richness: float = 0.0        # 泛音数量
    dynamic_range_db: float = 15.0


class MuscleStrengthScorer:
    """肌肉力量评分器 — ⚠️ HEURISTIC: 代理指标，非直接生理测量

    v7.3: 可选 audiofeat 增强:
      - soft_phonation_mean → 身体支撑质量 (越低越好)
      - vocal_fry_ratio → 支撑不足指示 (越高越差)
      - hammarberg_index → 共鸣平衡 (低频/高频比)
    """

    # ---- audiofeat 阈值 (v7.3) ----
    SOFT_PHONATION_HIGH = 0.6    # > 0.6 = 软发声过多 → 支撑不足
    VOCAL_FRY_HIGH = 0.3         # > 0.3 = 气泡音过多 → 支撑不足
    BODY_AUDIOFEAT_WEIGHT = 0.20 # audiofeat 在身体维度中的混合权重

    SOFT_PHONATION_PENALTY = 10.0
    VOCAL_FRY_PENALTY = 8.0

    def calculate(
        self,
        features: MuscleFeatures,
        audiofeat: 'AudiofeatFeatures | None' = None,
    ) -> MuscleStrengthScore:
        # 1. 身体肌肉力量 (50%)
        # HEURISTIC: Proxy metric from microphone audio — not direct physiological measurement
        body = self._calc_body_strength(
            features.max_db_level,
            features.low_freq_energy_ratio,
            features.rms_decay_rate,
            features.dynamic_range_db,
        )

        # 2. 面部肌肉力量 (50%)
        # HEURISTIC: Proxy metric from microphone audio — not direct physiological measurement
        facial = self._calc_facial_strength(
            features.singers_formant_energy,
            features.formant_clustering_quality,
            features.overtone_richness,
        )

        # 3. v7.3: audiofeat 增强
        if audiofeat is not None:
            body, facial = self._apply_audiofeat_enhancement(body, facial, audiofeat)

        # 加权合成
        score = body * 0.50 + facial * 0.50
        score = max(0.0, min(100.0, score))

        diagnosis: list[str] = []
        if body < 40:
            diagnosis.append("身体支撑偏弱")
        if facial < 40:
            diagnosis.append("面部共鸣偏弱")
        if features.dynamic_range_db > 30:
            diagnosis.append("动态范围宽广")

        return MuscleStrengthScore(
            raw_score=round(score, 1),
            body_muscle_strength=round(body, 1),
            facial_muscle_strength=round(facial, 1),
            is_heuristic=True,  # ⚠️ ALWAYS heuristic
            diagnosis=tuple(diagnosis),
        )

    @staticmethod
    def _calc_body_strength(
        max_db: float,
        low_freq: float,
        rms_decay: float,
        dynamic_range_db: float,
    ) -> float:
        # HEURISTIC: Proxy metric from microphone audio — not direct physiological measurement

        # max_db_level: -30→0, -20→25, -10→50, 0→100
        if max_db >= 0:
            max_db_score = 100.0
        elif max_db <= -30:
            max_db_score = 0.0
        else:
            max_db_score = (max_db + 30) / 30 * 100  # linear in [-30, 0]

        # low_freq_energy: >0.40→100, 0.20→60, 0.10→30
        if low_freq >= 0.40:
            low_freq_score = 100.0
        elif low_freq >= 0.20:
            low_freq_score = 60.0 + (low_freq - 0.20) / 0.20 * 40
        elif low_freq >= 0.10:
            low_freq_score = 30.0 + (low_freq - 0.10) / 0.10 * 30
        else:
            low_freq_score = max(0.0, low_freq / 0.10 * 30)

        # rms_decay_rate: <0.5→100, 1.0→70, 2.0→30, >3.0→10
        if rms_decay <= 0.5:
            decay_score = 100.0
        elif rms_decay >= 3.0:
            decay_score = 10.0
        elif rms_decay <= 2.0:
            decay_score = 70.0 + (2.0 - rms_decay) / 1.5 * 30  # 1.0→90, 2.0→70
        else:
            decay_score = 30.0 - (rms_decay - 2.0) / 1.0 * 20  # 2.0→30, 3.0→10

        body = max_db_score * 0.40 + low_freq_score * 0.35 + decay_score * 0.25

        # dynamic_range bonus
        if dynamic_range_db > 30:
            body += 10.0

        return max(0.0, min(100.0, body))

    @staticmethod
    def _calc_facial_strength(
        formant_energy: float,
        formant_cluster: float,
        overtone: float,
    ) -> float:
        # HEURISTIC: Proxy metric from microphone audio — not direct physiological measurement

        # singers_formant_energy: >0.15→100, 0.08→60, 0.03→30
        if formant_energy >= 0.15:
            formant_score = 100.0
        elif formant_energy >= 0.08:
            formant_score = 60.0 + (formant_energy - 0.08) / 0.07 * 40
        elif formant_energy >= 0.03:
            formant_score = 30.0 + (formant_energy - 0.03) / 0.05 * 30
        else:
            formant_score = max(10.0, formant_energy / 0.03 * 30)

        # formant_clustering_quality: 0-100 direct
        cluster_score = max(0.0, min(100.0, formant_cluster))

        # overtone_richness: >8→100, 5→60, 3→30, <1→10
        if overtone >= 8:
            overtone_score = 100.0
        elif overtone >= 5:
            overtone_score = 60.0 + (overtone - 5) / 3.0 * 40
        elif overtone >= 3:
            overtone_score = 30.0 + (overtone - 3) / 2.0 * 30
        elif overtone >= 1:
            overtone_score = 10.0 + (overtone - 1) / 2.0 * 20
        else:
            overtone_score = max(0.0, overtone * 10)

        return max(0.0, min(100.0,
            formant_score * 0.40 + cluster_score * 0.35 + overtone_score * 0.25
        ))

    def _apply_audiofeat_enhancement(
        self,
        body: float,
        facial: float,
        af: 'AudiofeatFeatures',
    ) -> tuple[float, float]:
        """v7.3: audiofeat 增强 — soft_phonation/vocal_fry → body 微调"""
        sp = af.soft_phonation_mean
        vf = af.vocal_fry_ratio

        # 所有值为 0 (默认/不可用) → 无增强
        if sp == 0.0 and vf == 0.0:
            return body, facial

        # Soft phonation: 高 = 气息声/弱支撑 → 身体分数惩罚
        audiofeat_body_adjust = 0.0
        if sp > self.SOFT_PHONATION_HIGH:
            penalty_ratio = min(1.0, (sp - self.SOFT_PHONATION_HIGH) / (1.0 - self.SOFT_PHONATION_HIGH))
            audiofeat_body_adjust -= self.SOFT_PHONATION_PENALTY * penalty_ratio

        # Vocal fry: 高 = 可能支撑不足 → 身体分数惩罚
        if vf > self.VOCAL_FRY_HIGH:
            penalty_ratio = min(1.0, (vf - self.VOCAL_FRY_HIGH) / (1.0 - self.VOCAL_FRY_HIGH))
            audiofeat_body_adjust -= self.VOCAL_FRY_PENALTY * penalty_ratio

        # 混合: audiofeat 权重 20%, 原启发式 80%
        body_enhanced = max(0.0, min(100.0, body + audiofeat_body_adjust))
        body = body * (1.0 - self.BODY_AUDIOFEAT_WEIGHT) + body_enhanced * self.BODY_AUDIOFEAT_WEIGHT

        return body, facial
