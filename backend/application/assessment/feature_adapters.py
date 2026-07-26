"""
特征适配器 — v7.1.4 适配器路径 (Path B 回退)

桥接旧特征类型到新 DDD 特征数据类 (backend/domain/assessment/)。

设计原则:
- 仅作为 flag 回退路径保留 (enable_ddd_feature_extraction=False 时使用)
- 零副作用: 纯数据映射, 无 I/O
- 宽松回退: 缺失字段使用合理默认值, 不崩溃
- 启发式标记: Muscle/Timbre 维度标记 is_heuristic=True
"""

from __future__ import annotations
import math
from typing import Optional


def _safe_float(value, default: float = 0.0) -> float:
    """安全转换为 float，NaN/Inf 回退到默认值"""
    if value is None:
        return default
    try:
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except (TypeError, ValueError):
        return default


def _safe_clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, _safe_float(value)))


class FeatureAdapterRegistry:
    """
    特征适配器注册表 — v7.1.4 仅用于 flag 回退路径。

    使用方式 (Path B 回退):
        from backend.application.assessment.feature_adapters import FeatureAdapterRegistry

        adapters = FeatureAdapterRegistry()
        pitch_features = adapters.to_pitch(features)
        score = PitchScorer().calculate(pitch_features)
    """

    # ================================================================
    # PitchFeatures
    # ================================================================
    @staticmethod
    def to_pitch(features) -> 'PitchFeatures':
        from backend.domain.assessment.pitch_scorer import PitchFeatures

        pd = getattr(features, 'pitch_deviation', None)
        if pd is None:
            return PitchFeatures()

        return PitchFeatures(
            mae_cents=_safe_float(pd.mae_cents),
            rpa=_safe_float(pd.rpa),
            rca=_safe_float(pd.rca),
            gross_error_rate=_safe_float(pd.gross_error_rate),
            octave_error_rate=_safe_float(pd.octave_error_rate),
            relative_smoothness=_safe_float(pd.relative_smoothness, default=1.0),
            detection_rate=_safe_float(pd.detection_rate, default=1.0),
            pitch_breaks=int(_safe_float(pd.pitch_breaks)),
            valid_frame_count=max(1, int(_safe_float(pd.valid_frame_count, default=100))),
            pitch_wobble=_safe_float(pd.pitch_wobble),
        )

    # ================================================================
    # RhythmFeatures
    # ================================================================
    @staticmethod
    def to_rhythm(features, is_clean_vocal: bool = False) -> 'RhythmFeatures':
        from backend.domain.assessment.rhythm_scorer import RhythmFeatures

        ra = getattr(features, 'rhythm_alignment', None)
        if ra is None:
            return RhythmFeatures(is_clean_vocal=is_clean_vocal)

        return RhythmFeatures(
            avg_deviation_ratio=_safe_float(ra.avg_deviation_ratio),
            irregularity=_safe_float(ra.irregularity),
            onset_density=max(0.5, _safe_float(ra.beats_per_second, default=2.0)),
            onset_count=max(1, int(_safe_float(ra.onset_count, default=100))),
            off_beat_segments=int(_safe_float(ra.off_beat_segments)),
            is_clean_vocal=is_clean_vocal,
        )

    # ================================================================
    # BreathFeatures
    # ================================================================
    @staticmethod
    def to_breath(features) -> 'BreathFeatures':
        from backend.domain.assessment.breath_scorer import BreathFeatures

        bs = getattr(features, 'breath_stability', None)
        if bs is None:
            return BreathFeatures()

        return BreathFeatures(
            professional_breath_score=_safe_float(bs.professional_breath_score),
            long_note_support=_safe_float(bs.long_note_support_score),
            dynamic_control=_safe_float(bs.dynamic_control_score),
            breath_design=_safe_float(bs.breath_design_score),
            breath_technique=_safe_float(bs.breath_technique_score),
            rms_fluctuation=_safe_float(bs.rms_fluctuation),
            is_artistic_fluctuation=bool(getattr(bs, 'is_artistic_fluctuation', False)),
            controlled_breathiness=_safe_float(bs.controlled_breathiness),
            uncontrolled_leak=_safe_float(bs.uncontrolled_leak),
            breath_breaks=int(_safe_float(bs.breath_breaks)),
            long_note_count=int(_safe_float(bs.long_note_count)),
        )

    # ================================================================
    # TechniqueFeatures (v7.0 重新设计: 咬字50% + 气声比50%)
    # ================================================================
    @staticmethod
    def to_technique(features) -> 'TechniqueFeatures':
        from backend.domain.assessment.technique_scorer import TechniqueFeatures

        vt = getattr(features, 'vocal_technique', None)

        # 从旧 DTO 推导新特征
        # onset_density: 从 rhythm_alignment 获取 beats_per_second
        onset_density = 0.0
        ra = getattr(features, 'rhythm_alignment', None)
        if ra is not None:
            onset_density = _safe_float(ra.beats_per_second, default=2.0)

        # spectral_flux: 近似值, 基于声学特征
        # hnr / cpp 从 AudioFeaturesResult 直接读取
        hnr = _safe_float(getattr(features, 'hnr', 15.0), default=15.0)
        cpp = _safe_float(getattr(features, 'cpp', 1.0), default=1.0)
        spectral_tilt = _safe_float(getattr(features, 'spectral_tilt', 0.0))

        # vibrato info (传递给 Artistry 提取器)
        vibrato_quality = _safe_float(vt.vibrato_quality) if vt else 0.0
        vibrato_rate_avg = _safe_float(vt.vibrato_rate_avg, default=5.0) if vt else 5.0

        return TechniqueFeatures(
            onset_density=onset_density,
            spectral_flux=_safe_float(vt.technique_score if vt else 0.0) / 20.0,  # 近似映射
            consonant_clarity=_safe_clamp(hnr * 2.0, 0, 100),  # HNR → 辅音清晰度
            hnr_mean=hnr,
            spectral_tilt=spectral_tilt,
            hf_energy_ratio=_safe_clamp(cpp / 5.0, 0, 1.0),  # CPP → 高频能量比
            cpp_mean=cpp,
            vibrato_quality=vibrato_quality,
            vibrato_rate_avg=vibrato_rate_avg,
        )

    # ================================================================
    # MuscleStrengthFeatures (NEW ⚠️ HEURISTIC)
    # ================================================================
    @staticmethod
    def to_muscle(features) -> 'MuscleFeatures':
        from backend.domain.assessment.muscle_scorer import MuscleFeatures

        bs = getattr(features, 'breath_stability', None)
        hnr = _safe_float(getattr(features, 'hnr', 15.0), default=15.0)

        # 从现有特征推导肌肉力量代理指标
        # max_db_level: 从 dynamic_range 推导
        dynamic_range = _safe_float(bs.dynamic_range, default=15.0) if bs else 15.0

        # low_freq_energy: 从 HPSS harmonic_ratio 推导
        hpss_ratio = _safe_float(bs._hpss_harmonic_ratio, default=0.30) if bs else 0.30

        # rms_decay: 从 long_note_decay/sustain 推导
        rms_decay = _safe_float(bs.long_note_decay, default=1.0) if bs else 1.0

        # singers_formant: 从 HNR 推导 (2.5-3.5kHz 聚类能量)
        singers_formant = _safe_clamp(hnr / 60.0, 0, 0.30)

        # formant_clustering: 从 pitch_stability_long 推导, 为 0 时回退到 long_note_support
        # (与 DDD LibrosaMuscleExtractor 一致: pitch_stability_long 可能未计算)
        pitch_stability = _safe_float(bs.pitch_stability_long) if bs else 0.0
        if pitch_stability > 0:
            formant_source = pitch_stability
        else:
            formant_source = _safe_float(bs.long_note_support_score, default=50.0) if bs else 50.0
        formant_cluster = _safe_clamp(formant_source, 0, 100)

        # overtone_richness: 从 controlled_breathiness 推导
        overtone = _safe_clamp(
            _safe_float(bs.controlled_breathiness, default=50.0) if bs else 50.0, 0, 100
        )

        return MuscleFeatures(
            max_db_level=-20.0 + dynamic_range * 0.3,
            low_freq_energy_ratio=_safe_clamp(hpss_ratio, 0, 1),
            rms_decay_rate=_safe_clamp(rms_decay, 0.1, 5.0),
            singers_formant_energy=_safe_clamp(singers_formant, 0, 0.3),
            formant_clustering_quality=formant_cluster,
            overtone_richness=overtone,
            dynamic_range_db=dynamic_range,
        )

    # ================================================================
    # ArtistryFeatures
    # ================================================================
    @staticmethod
    def to_artistry(features) -> 'ArtistryFeatures':
        from backend.domain.assessment.artistry_scorer import ArtistryFeatures

        vt = getattr(features, 'vocal_technique', None)
        bs = getattr(features, 'breath_stability', None)

        vibrato_quality = _safe_float(vt.vibrato_quality) if vt else 0.0
        vibrato_count = int(_safe_float(vt.vibrato_count)) if vt else 0
        dynamic_range = _safe_float(bs.dynamic_range, default=15.0) if bs else 15.0
        phrase_coherence = _safe_float(bs.phrase_coherence, default=50.0) if bs else 50.0
        is_artistic = bool(getattr(bs, 'is_artistic_fluctuation', False)) if bs else False
        long_note_count = int(_safe_float(bs.long_note_count)) if bs else 0

        # 从 vocal technique DTO 推导 crescendo_quality 和 pitch_cv
        crescendo_quality = _safe_float(bs.crescendo_quality, default=50.0) if bs else 50.0

        return ArtistryFeatures(
            vibrato_quality=vibrato_quality,
            vibrato_count=vibrato_count,
            dynamic_range=dynamic_range,
            crescendo_quality=crescendo_quality,
            phrase_coherence=phrase_coherence,
            is_artistic_fluctuation=is_artistic,
            long_note_count=long_note_count,
            pitch_cv=max(0.01, _safe_float(vt.vibrato_rate_avg, default=5.0)) if vt else 5.0,
        )

    # ================================================================
    # TimbreFeatures (⚠️ HEURISTIC)
    # ================================================================
    @staticmethod
    def to_timbre(features) -> 'TimbreFeatures':
        from backend.domain.assessment.timbre_adjuster import TimbreFeatures

        hnr = _safe_float(getattr(features, 'hnr', 15.0), default=15.0)
        cpp = _safe_float(getattr(features, 'cpp', 1.0), default=1.0)

        # 从音频特征推导音色代理指标
        # spectral_centroid_deviation: 从 spectral_tilt 推导
        spectral_tilt = _safe_float(getattr(features, 'spectral_tilt', 0.0))
        centroid_dev = abs(spectral_tilt) / 10.0  # 离差

        # mfcc_cluster: 从 HNR 和 CPP 综合推导
        cluster_dist = _safe_clamp(hnr / 30.0, 0, 1.0)
        cluster_purity = _safe_clamp(cpp / 6.0, 0, 1.0)

        # harmonic_richness: 从 harmonic_stability + HNR 推导
        bs = getattr(features, 'breath_stability', None)
        harmonic_stability = _safe_float(bs.harmonic_stability, default=50.0) if bs else 50.0
        harmonic_richness = _safe_clamp(harmonic_stability / 100.0 + hnr / 60.0, 0, 1)

        # nasality_index: 简化估计 (从频谱质心偏离推测)
        nasality = _safe_clamp(abs(spectral_tilt + 5.0) / 10.0, 0, 1)

        return TimbreFeatures(
            spectral_centroid_deviation=centroid_dev,
            mfcc_cluster_distance=cluster_dist,
            mfcc_cluster_purity=cluster_purity,
            harmonic_richness=harmonic_richness,
            nasality_index=nasality,
        )
