"""
肌肉力量特征提取器 — v7.1.2 对齐版

复用 FeatureAdapterRegistry.to_muscle() 推导逻辑, ⚠️ HEURISTIC。
"""
from __future__ import annotations
import logging

from backend.domain.assessment.muscle_scorer import MuscleFeatures
from backend.domain.audio.feature_types import AcousticFeatures
from backend.domain.assessment.breath_scorer import BreathFeatures
from backend.shared.math_utils import safe_clamp as _safe_clamp

logger = logging.getLogger(__name__)


class LibrosaMuscleExtractor:
    """肌肉力量特征提取器 — Level 3 ⚠️ HEURISTIC, 与 FeatureAdapterRegistry 一致"""

    def extract(
        self,
        breath: BreathFeatures,
        acoustic: AcousticFeatures,
    ) -> MuscleFeatures:
        """提取肌肉力量代理指标 — 与 FeatureAdapterRegistry.to_muscle() 相同公式。"""

        hnr = float(getattr(acoustic, 'hnr', 15.0) or 15.0)
        hpss_ratio = float(getattr(acoustic, 'hpss_harmonic_ratio', 0.30) or 0.30)
        dynamic_range = float(getattr(breath, 'dynamic_range', 15.0) or 15.0)
        # controlled_breathiness 作为 overtone_richness 的代理 (与 adapter 一致)
        controlled_breathiness = float(getattr(breath, 'controlled_breathiness', 50.0) or 50.0)
        # pitch_stability_long: 优先, 回退到 long_note_support (短音频 fallback)
        pitch_stability_long = float(getattr(breath, 'pitch_stability_long', 0.0) or 0.0)
        long_note_support = float(getattr(breath, 'long_note_support', 50.0) or 50.0)
        formant_source = pitch_stability_long if pitch_stability_long > 0 else long_note_support

        # body muscle proxies (与 adapter 一致)
        max_db = -20.0 + dynamic_range * 0.3
        low_freq_ratio = _safe_clamp(hpss_ratio, 0, 1)
        # rms_decay: 来自 BreathStabilityResult.long_note_decay (与 adapter 一致)
        long_note_decay = float(getattr(breath, 'long_note_decay', 1.0) or 1.0)
        rms_decay = _safe_clamp(long_note_decay, 0.1, 5.0)

        # facial muscle proxies (与 adapter 一致)
        singers_formant = _safe_clamp(hnr / 60.0, 0, 0.30)
        formant_cluster = _safe_clamp(formant_source, 0, 100)
        overtone = _safe_clamp(controlled_breathiness, 0, 100)

        return MuscleFeatures(
            max_db_level=round(max_db, 2),
            low_freq_energy_ratio=round(low_freq_ratio, 4),
            rms_decay_rate=round(rms_decay, 2),
            singers_formant_energy=round(singers_formant, 4),
            formant_clustering_quality=round(formant_cluster, 2),
            overtone_richness=round(overtone, 2),
            dynamic_range_db=round(dynamic_range, 2),
        )
