"""
音色特征提取器 — v7.1.2 对齐版

复用 FeatureAdapterRegistry.to_timbre() 推导逻辑, ⚠️ HEURISTIC。
"""
from __future__ import annotations
import logging

from backend.domain.assessment.timbre_adjuster import TimbreFeatures
from backend.domain.audio.feature_types import AcousticFeatures

from backend.shared.math_utils import safe_clamp

logger = logging.getLogger(__name__)

# timbre 特征归一化到 [0, 1]
def _safe_clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return safe_clamp(value, lo, hi)


class LibrosaTimbreExtractor:
    """音色特征提取器 — Level 2 ⚠️ HEURISTIC, 与 FeatureAdapterRegistry 一致"""

    def extract(
        self,
        acoustic: AcousticFeatures,
        harmonic_stability: float = 50.0,
    ) -> TimbreFeatures:
        """提取音色特征 — 与 FeatureAdapterRegistry.to_timbre() 相同公式。"""
        # 当 harmonic_stability 从 BreathFeatures 传入时使用, 否则默认 50.0

        hnr = float(getattr(acoustic, 'hnr', 15.0) or 15.0)
        cpp = float(getattr(acoustic, 'cpp', 1.0) or 1.0)
        spectral_tilt = float(getattr(acoustic, 'spectral_tilt', 0.0) or 0.0)

        # spectral_centroid_deviation: abs(tilt) / 10 (与 adapter 一致)
        centroid_dev = abs(spectral_tilt) / 10.0

        # mfcc_cluster_distance: HNR / 30 (与 adapter 一致)
        cluster_dist = _safe_clamp(hnr / 30.0)

        # mfcc_cluster_purity: CPP / 6 (与 adapter 一致)
        cluster_purity = _safe_clamp(cpp / 6.0)

        # harmonic_richness: harmonic_stability/100 + HNR/60 (与 adapter 一致)
        harmonic_richness = _safe_clamp(harmonic_stability / 100.0 + hnr / 60.0)

        # nasality_index: abs(tilt + 5) / 10 (与 adapter 一致)
        nasality = _safe_clamp(abs(spectral_tilt + 5.0) / 10.0)

        return TimbreFeatures(
            spectral_centroid_deviation=round(centroid_dev, 4),
            mfcc_cluster_distance=round(cluster_dist, 4),
            mfcc_cluster_purity=round(cluster_purity, 4),
            harmonic_richness=round(harmonic_richness, 4),
            nasality_index=round(nasality, 4),
        )
