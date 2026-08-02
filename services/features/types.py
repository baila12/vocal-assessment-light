"""
音频特征数据传输对象 (DTOs)

DEPRECATED since v7.6. Scheduled for removal in v7.9.
All production code migrated to DDD domain types (backend/domain/audio/).
Zero active import references in non-deprecated code as of v7.8.

从 __init__.py 分离，消除与子模块的循环导入
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import warnings

warnings.warn(
    "services.features.types is deprecated since v7.6 (will be removed in v7.9). "
    "Use backend.domain.audio domain types instead.",
    DeprecationWarning,
    stacklevel=2,
)


@dataclass
class PitchDeviationResult:
    """音分偏差分析结果 v5.14: 新增多指标体系 (移植自 pitch-benchmark)"""
    mae_cents: float = 0.0
    max_cents: float = 0.0
    consecutive_off_notes: int = 0
    pitch_breaks: int = 0
    pitch_wobble: float = 0.0
    detection_rate: float = 0.0
    valid_frame_count: int = 0
    rpa: float = 0.0
    rca: float = 0.0
    gross_error_rate: float = 0.0
    octave_error_rate: float = 0.0
    relative_smoothness: float = 0.0
    continuity_breaks: float = 0.0


@dataclass
class RhythmAlignmentResult:
    """节拍对齐分析结果"""
    avg_deviation_ratio: float = 0.0
    max_deviation_ratio: float = 0.0
    off_beat_segments: int = 0
    beats_per_second: float = 0.0
    onset_count: int = 0
    irregularity: float = 0.0


@dataclass
class BreathStabilityResult:
    """气息稳定性分析结果 - v4.1 专业气息评估"""
    rms_fluctuation: float = 0.0
    long_note_decay: float = 0.0
    breath_breaks: int = 0
    dynamic_range: float = 0.0
    sustain_quality: float = 0.0
    long_note_support_score: float = 0.0
    long_note_count: int = 0
    long_note_avg_quality: float = 0.0
    harmonic_stability: float = 0.0
    pitch_stability_long: float = 0.0
    dynamic_control_score: float = 0.0
    soft_singing_quality: float = 0.0
    crescendo_quality: float = 0.0
    soft_segment_count: int = 0
    breath_design_score: float = 0.0
    clean_breath_count: int = 0
    phrase_coherence: float = 0.0
    breath_technique_score: float = 0.0
    controlled_breathiness: float = 0.0
    uncontrolled_leak: float = 0.0
    is_artistic_fluctuation: bool = False
    professional_breath_score: float = 0.0
    _hpss_harmonic_ratio: float = 0.0  # v6.2 perf: cached HPSS ratio


@dataclass
class VocalTechniqueResult:
    """演唱技巧检测结果"""
    vibrato_count: int = 0
    vibrato_rate_avg: float = 0.0
    vibrato_extent_avg: float = 0.0
    vibrato_quality: float = 0.0
    slide_count: int = 0
    falsetto_segments: int = 0
    staccato_count: int = 0       # v6.2: 断音检测数
    legato_quality: float = 0.0   # v6.2: 连音质量 0-100
    technique_score: float = 0.0


@dataclass
class AudioFeaturesResult:
    """音频特征提取综合结果"""
    success: bool = True
    pitch_deviation: PitchDeviationResult = field(default_factory=PitchDeviationResult)
    rhythm_alignment: RhythmAlignmentResult = field(default_factory=RhythmAlignmentResult)
    breath_stability: BreathStabilityResult = field(default_factory=BreathStabilityResult)
    vocal_technique: VocalTechniqueResult = field(default_factory=VocalTechniqueResult)
    hnr: float = 0.0
    cpp: float = 0.0
    is_mixed_audio: bool = False
    mixed_audio_confidence: float = 0.0
    _vocal_segment_count: int = 0
    _voicing_detection: Optional['VoicingDetectionResult'] = None  # v5.18
    _mixed_metadata: Optional[dict] = None  # v6.0: mixed audio detection metadata
    _reverb_compensation: Optional[object] = None  # v5.20: ReverbCompensationResult
    _hpss_harmonic: Optional[object] = None  # v6.2: cached HPSS harmonic component
    _hpss_percussive: Optional[object] = None  # v6.2: cached HPSS percussive component
    _hpss_harmonic_ratio: float = 0.0  # v6.2: cached harmonic_ratio for breath technique
    spectral_tilt: float = -10.0  # v6.2: LTAS slope dB/oct [Sundberg 1987]
    _praat_voice_quality: Optional[object] = None  # v6.2: PraatVoiceQualityResult
    error_message: Optional[str] = None


@dataclass
class AcousticResult:
    """声学分析结果"""
    hnr: float = 0.0
    cpp: float = 0.0
    is_mixed_audio: bool = False
    mixed_audio_confidence: float = 0.0
    _mixed_metadata: Optional[dict] = None  # v6.0: mixed audio detection metadata
    # v6.0: low_freq_ratio and spectral_flatness removed (replaced by multi-feature metadata)