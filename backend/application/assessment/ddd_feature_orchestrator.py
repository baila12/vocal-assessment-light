"""
DDD 特征提取编排器 — v7.1 Batch 5

绞杀者模式: 替代 AudioFeaturesService.extract_all_features()
从原始音频 → 7 个 DDD Features 数据类 (零中间 DTO)。
"""
from __future__ import annotations
from dataclasses import dataclass, field
import logging
from typing import Optional
import numpy as np

from backend.domain.audio.feature_types import AcousticFeatures
from backend.domain.audio.acoustic_feature_extractor import LibrosaAcousticExtractor
from backend.domain.audio.pitch_extractor import LibrosaPitchExtractor
from backend.domain.audio.rhythm_extractor import LibrosaRhythmExtractor
from backend.domain.audio.breath_extractor import LibrosaBreathExtractor
from backend.domain.audio.technique_extractor import LibrosaTechniqueExtractor
from backend.domain.audio.muscle_extractor import LibrosaMuscleExtractor
from backend.domain.audio.artistry_extractor import LibrosaArtistryExtractor
from backend.domain.audio.timbre_extractor import LibrosaTimbreExtractor
from backend.domain.audio.audiofeat_extractor import (
    AudiofeatExtractor, AudiofeatFeatures,
)

from backend.domain.assessment.pitch_scorer import PitchFeatures
from backend.domain.assessment.rhythm_scorer import RhythmFeatures
from backend.domain.assessment.breath_scorer import BreathFeatures
from backend.domain.assessment.technique_scorer import TechniqueFeatures
from backend.domain.assessment.muscle_scorer import MuscleFeatures
from backend.domain.assessment.artistry_scorer import ArtistryFeatures
from backend.domain.assessment.timbre_adjuster import TimbreFeatures
from backend.domain.assessment.feature_flags import DimensionFlags

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DddFeatureSet:
    """DDD 特征全集 — 7 个维度的所有特征"""
    acoustic: AcousticFeatures = field(default_factory=AcousticFeatures)
    pitch: PitchFeatures = field(default_factory=PitchFeatures)
    rhythm: RhythmFeatures = field(default_factory=RhythmFeatures)
    breath: BreathFeatures = field(default_factory=BreathFeatures)
    technique: TechniqueFeatures = field(default_factory=TechniqueFeatures)
    muscle: MuscleFeatures = field(default_factory=MuscleFeatures)
    artistry: ArtistryFeatures = field(default_factory=ArtistryFeatures)
    timbre: TimbreFeatures = field(default_factory=TimbreFeatures)

    # v7.2: audiofeat 增强特征 (可选, flag 控制)
    audiofeat: AudiofeatFeatures = field(default_factory=AudiofeatFeatures)


class DddFeatureExtractionOrchestrator:
    """
    DDD 特征提取编排器。

    按依赖拓扑排序运行所有 7 个提取器:
      Level 0: Acoustic
      Level 1: Pitch, Rhythm (独立)
      Level 2: Breath, Technique, Timbre (依赖 Acoustic)
      Level 3: Muscle, Artistry (依赖 Breath + Technique)

    用法:
        orchestrator = DddFeatureExtractionOrchestrator()
        features = orchestrator.extract_all(y, sr, f0, voiced_flags)
        # 直接传入 ScoringOrchestrator.calculate_ddd(features)
    """

    def __init__(self, flags: DimensionFlags | None = None):
        self._flags = flags or DimensionFlags()
        self._acoustic = LibrosaAcousticExtractor()
        self._pitch = LibrosaPitchExtractor()
        self._rhythm = LibrosaRhythmExtractor()
        self._breath = LibrosaBreathExtractor()
        self._technique = LibrosaTechniqueExtractor()
        self._muscle = LibrosaMuscleExtractor()
        self._artistry = LibrosaArtistryExtractor()
        self._timbre = LibrosaTimbreExtractor()
        # v7.2: audiofeat 增强提取器 (可选)
        self._audiofeat = AudiofeatExtractor() if self._flags.enable_audiofeat else None

    def extract_all(
        self,
        y: np.ndarray,
        sr: int,
        f0: Optional[np.ndarray] = None,
        voiced_flags: Optional[np.ndarray] = None,
        is_clean_vocal: bool = False,
    ) -> DddFeatureSet:
        """提取全部 7 个维度的特征。"""
        n_samples = len(y)

        # Default F0 if not provided
        if f0 is None or voiced_flags is None:
            f0 = np.array([], dtype=np.float64)
            voiced_flags = np.array([], dtype=bool)

        # v7.1.3: 响度归一化 (与 AudioFeaturesService.extract_all_features 一致)
        from backend.domain.audio.audio_utils import normalize_loudness
        y = normalize_loudness(y)

        # Level 0: Acoustic Foundation
        acoustic = self._acoustic.extract(
            y, sr,
            enable_multiscale_hnr=self._flags.enable_multiscale_hnr,
            enable_praat_cpp=self._flags.enable_praat_cpp,
            enable_voicing_detection=self._flags.enable_voicing_detection,
            enable_reverb_compensation=self._flags.enable_reverb_compensation,
        )

        # Level 1: Pitch + Rhythm (独立)
        pitch = self._pitch.extract(y, sr, f0, voiced_flags)
        rhythm = self._rhythm.extract(y, sr, f0=f0, voiced_flags=voiced_flags, is_clean_vocal=is_clean_vocal)

        # Level 2: Breath + Technique + Timbre (依赖 Acoustic)
        breath = self._breath.extract(y, sr, acoustic, f0=f0, is_clean_vocal=is_clean_vocal)
        technique = self._technique.extract(y, sr, acoustic, f0=f0,
                                            onset_density=rhythm.onset_density)
        timbre = self._timbre.extract(
            acoustic,
            harmonic_stability=breath.harmonic_stability,
        )

        # Level 3: Muscle (依赖 Breath + Acoustic + raw audio for v7.4 proxies)
        muscle = self._muscle.extract(breath, acoustic, y=y, sr=sr)

        # v7.1.3: vibrato 信息从 TechniqueFeatures 读取 (LibrosaTechniqueExtractor 已调用
        # TechniqueAnalyzer.detect_vocal_techniques, 避免重复计算)
        vibrato_q = technique.vibrato_quality

        # v7.5: 计算真正的 F0 变异系数 (而非 vibrato_rate_avg Hz)
        # _calc_pitch_variation() 期望 CV 范围 0.01-0.20, 而非颤音频率 4.5-8.0 Hz
        pitch_cv = self._compute_pitch_cv(f0)

        artistry = self._artistry.extract(technique, breath,
                                          vibrato_quality=vibrato_q,
                                          vibrato_count=0,
                                          pitch_cv=pitch_cv)

        # v7.2: audiofeat 增强特征 (flag 门控)
        audiofeat_features = AudiofeatFeatures()
        if self._audiofeat is not None and self._audiofeat.available:
            # audiofeat 需要 torch tensor
            import torch
            y_torch = torch.from_numpy(y.astype(np.float32))
            audiofeat_features = self._audiofeat.extract(y_torch, sr)

        return DddFeatureSet(
            acoustic=acoustic,
            pitch=pitch,
            rhythm=rhythm,
            breath=breath,
            technique=technique,
            muscle=muscle,
            artistry=artistry,
            timbre=timbre,
            audiofeat=audiofeat_features,
        )

    @staticmethod
    def _compute_pitch_cv(f0: np.ndarray) -> float:
        """计算真正的 F0 变异系数 (CV) 用于 pitch_variation 评分。

        文献: _calc_pitch_variation() 期望 pitch CV 范围 0.01-0.20。
        v7.5 修复: 之前传递的是 vibrato_rate_avg (Hz, 4.5-8.0),
        导致所有歌手都得到固定 30.0 分。

        Args:
            f0: F0 数组 (Hz), 0 = 无声音帧

        Returns:
            pitch_cv: F0 变异系数 std(f0_valid) / mean(f0_valid), 范围约 0.01-0.20
        """
        f0_valid = f0[f0 > 0] if len(f0) > 0 else np.array([])
        if len(f0_valid) < 10:
            return 0.02  # 数据不足时返回低 CV (中性偏低)

        f0_mean = float(np.mean(f0_valid))
        if f0_mean <= 0:
            return 0.02

        f0_std = float(np.std(f0_valid))
        cv = f0_std / f0_mean

        # clamp 到合理范围 [0.005, 0.50]
        return float(np.clip(cv, 0.005, 0.50))
