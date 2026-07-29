"""
艺术表现特征提取器 — v7.1.2 对齐版

复用 FeatureAdapterRegistry.to_artistry() 推导逻辑。
"""
from __future__ import annotations
import logging

from backend.domain.assessment.artistry_scorer import ArtistryFeatures
from backend.domain.assessment.breath_scorer import BreathFeatures
from backend.domain.assessment.technique_scorer import TechniqueFeatures

logger = logging.getLogger(__name__)


class LibrosaArtistryExtractor:
    """艺术表现特征提取器 — Level 3, 与 FeatureAdapterRegistry 一致"""

    def extract(
        self,
        technique: TechniqueFeatures,
        breath: BreathFeatures,
        vibrato_quality: float = 0.0,
        vibrato_count: int = 0,
        pitch_cv: float = 0.0,
    ) -> ArtistryFeatures:
        """提取艺术表现特征 — 与 FeatureAdapterRegistry.to_artistry() 相同推导。"""

        # vibrato_quality: 优先使用传入值 (来自 TechniqueAnalyzer)
        # 回退: 从 technique + breath 推导
        if vibrato_quality <= 0:
            vibrato_quality = (
                float(technique.consonant_clarity) * 0.4 +
                float(breath.controlled_breathiness) * 0.3 +
                float(breath.long_note_support) * 0.3
            )

        # dynamic_range: 来自 breath (与 adapter 一致)
        dynamic_range = float(getattr(breath, 'dynamic_range', 15.0) or 15.0)

        # crescendo_quality: 来自 BreathStabilityResult.crescendo_quality (与 adapter 一致)
        crescendo_quality = float(getattr(breath, 'crescendo_quality', 50.0) or 50.0)

        # phrase_coherence: 来自 BreathStabilityResult.phrase_coherence (与 adapter 一致)
        phrase_coherence = float(getattr(breath, 'phrase_coherence', 50.0) or 50.0)

        # is_artistic_fluctuation (与 adapter 一致)
        is_artistic = bool(getattr(breath, 'is_artistic_fluctuation', False))
        # v7.6: 连续化分数 (优先)
        artistic_fluctuation = float(getattr(breath, 'artistic_fluctuation_score', 0.0) or 0.0)

        # long_note_count (与 adapter 一致)
        long_note_count = int(getattr(breath, 'long_note_count', 0) or 0)

        # v7.5: pitch_cv 应为 F0 变异系数 (0.01-0.20), 不是 vibrato_rate_avg (Hz)
        # 优先使用传入值 (来自 orchestrator 中真实 F0 CV 计算)
        # 回退: 从 technique onset_density 近似映射到 CV 范围
        if pitch_cv <= 0 or pitch_cv > 1.0:  # >1.0 说明传入了 Hz 旧值
            onset = float(technique.onset_density) if technique.onset_density > 0 else 2.0
            pitch_cv = max(0.01, min(0.30, onset * 0.03))

        return ArtistryFeatures(
            vibrato_quality=round(vibrato_quality, 2),
            vibrato_count=max(0, vibrato_count) if vibrato_count > 0 else long_note_count,
            dynamic_range=round(dynamic_range, 2),
            crescendo_quality=round(crescendo_quality, 2),
            phrase_coherence=round(phrase_coherence, 2),
            is_artistic_fluctuation=is_artistic,
            artistic_fluctuation_score=round(artistic_fluctuation, 2),  # v7.6: 连续化
            long_note_count=long_note_count,
            pitch_cv=round(pitch_cv, 4),
        )
