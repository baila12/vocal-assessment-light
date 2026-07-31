"""
艺术表现特征提取器 — v7.6 增强版

v7.6: 新增 rubato (表现性节奏变化) + attack_slope (起音斜率) 特征提取。
文献: Kondo 2025 — SPR 是最显著预测特征; 表现性时间控制是核心表达维度。
"""
from __future__ import annotations
import logging
import numpy as np

from backend.domain.assessment.artistry_scorer import ArtistryFeatures
from backend.domain.assessment.breath_scorer import BreathFeatures
from backend.domain.assessment.technique_scorer import TechniqueFeatures

logger = logging.getLogger(__name__)


def _extract_rubato(y: np.ndarray, sr: int) -> float:
    """提取表现性节奏变化 (rubato) 分数 0-100。

    算法:
    1. 检测音符起始点 (onsets)
    2. 计算起音间隔 (IOI)
    3. IOI 变异系数 → rubato 分数 (更高 = 更有表现力的节奏自由)

    文献: rubato 是古典/爵士声乐的核心表达技巧 (Kondo 2025).
    """
    try:
        import librosa
        # 起始点检测
        onset_frames = librosa.onset.onset_detect(
            y=y, sr=sr, hop_length=512,
            backtrack=True, units='frames',
        )
        if len(onset_frames) < 3:
            return 0.0

        # 计算起音间隔 (IOI, 秒)
        onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=512)
        iois = np.diff(onset_times)

        if len(iois) < 2:
            return 0.0

        # IOI 变异系数 (CV = std/mean)
        ioi_mean = float(np.mean(iois))
        if ioi_mean <= 0:
            return 0.0

        ioi_cv = float(np.std(iois)) / ioi_mean

        # CV 映射到 0-100:
        # CV < 0.05 → 极规律 (节拍器式) → 0
        # CV 0.10-0.25 → 适度自由 (表现性) → 40-80
        # CV > 0.40 → 过乱 (失控) → 递减
        if ioi_cv < 0.05:
            rubato = 0.0
        elif ioi_cv < 0.10:
            rubato = (ioi_cv - 0.05) / 0.05 * 40.0        # 0.05→0, 0.10→40
        elif ioi_cv < 0.25:
            rubato = 40.0 + (ioi_cv - 0.10) / 0.15 * 40.0  # 0.10→40, 0.25→80
        elif ioi_cv < 0.40:
            rubato = 80.0 - (ioi_cv - 0.25) / 0.15 * 30.0  # 0.25→80, 0.40→50
        else:
            rubato = max(20.0, 50.0 - (ioi_cv - 0.40) * 60)

        # 起始点密度加成: 更多音符 → 更多 rubato 机会
        onset_density = len(onset_frames) / max(1.0, len(y) / sr)
        if onset_density > 1.5:
            rubato = min(100.0, rubato * 1.1)  # 密集音符 → 10% 加成

        return round(max(0.0, min(100.0, rubato)), 2)
    except Exception:
        logger.debug("Rubato extraction failed", exc_info=True)
        return 0.0


class LibrosaArtistryExtractor:
    """艺术表现特征提取器 — Level 3, 与 FeatureAdapterRegistry 一致"""

    def extract(
        self,
        technique: TechniqueFeatures,
        breath: BreathFeatures,
        vibrato_quality: float = 0.0,
        vibrato_count: int = 0,
        pitch_cv: float = 0.0,
        # v7.6: 原始音频用于 rubato 提取
        y: np.ndarray | None = None,
        sr: int = 22050,
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

        # v7.6: rubato (表现性节奏变化) — 需要原始音频
        rubato_score = 0.0
        if y is not None and len(y) > 0:
            rubato_score = _extract_rubato(y, sr)

        return ArtistryFeatures(
            vibrato_quality=round(vibrato_quality, 2),
            vibrato_count=max(0, vibrato_count) if vibrato_count > 0 else long_note_count,
            dynamic_range=round(dynamic_range, 2),
            crescendo_quality=round(crescendo_quality, 2),
            phrase_coherence=round(phrase_coherence, 2),
            is_artistic_fluctuation=is_artistic,
            artistic_fluctuation_score=round(artistic_fluctuation, 2),
            long_note_count=long_note_count,
            pitch_cv=round(pitch_cv, 4),
            rubato_score=rubato_score,  # v7.6: 表现性节奏变化
        )
