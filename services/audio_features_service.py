"""
高级音频特征提取服务 v2.0 - 模块化重构

将特征提取拆分为独立模块：
- pitch.py: 音准分析
- rhythm.py: 节奏分析
- breath.py: 气息分析
- technique.py: 技巧检测
- acoustic.py: 声学指标

设计原则：
- 单一职责：每个模块只负责一种特征提取
- 返回 DTO：统一的数据传输对象
- 可配置：支持不同唱法的阈值调整
"""
from typing import Optional, Tuple
import numpy as np
import librosa
import logging

# 导入 DTOs
from services.features import (
    AudioFeaturesResult,
    PitchDeviationResult,
    RhythmAlignmentResult,
    BreathStabilityResult,
    VocalTechniqueResult,
)

# 导入分析器
from services.features.pitch import PitchAnalyzer
from services.features.rhythm import RhythmAnalyzer
from services.features.breath import BreathAnalyzer
from services.features.technique import TechniqueAnalyzer
from services.features.acoustic import AcousticAnalyzer

logger = logging.getLogger(__name__)


class AudioFeaturesService:
    """高级音频特征提取服务 - 协调器"""

    VOICE_FMIN = 65.0
    VOICE_FMAX = 1047.0

    def __init__(self, sample_rate: int = 22050, hop_length: int = 512):
        self.sample_rate = sample_rate
        self.hop_length = hop_length

        # 初始化各分析器
        self.pitch_analyzer = PitchAnalyzer(sample_rate, hop_length)
        self.rhythm_analyzer = RhythmAnalyzer(sample_rate, hop_length)
        self.breath_analyzer = BreathAnalyzer(sample_rate, hop_length)
        self.technique_analyzer = TechniqueAnalyzer(sample_rate, hop_length)
        self.acoustic_analyzer = AcousticAnalyzer(sample_rate, hop_length)

    def extract_all_features(
        self,
        audio_data: np.ndarray,
        f0: Optional[np.ndarray] = None,
        singing_style: str = 'pop'
    ) -> AudioFeaturesResult:
        """
        提取所有高级特征 v5.10

        新增预处理：
        - 响度归一化：减少录音条件差异
        - VAD人声分段：过滤前奏/间奏/尾奏，避免器乐段污染评分

        Args:
            audio_data: 音频数据
            f0: 基频序列（可选，未提供则自动提取）
            singing_style: 唱法类型 (pop/classical/folk/rap)

        Returns:
            AudioFeaturesResult: 综合特征提取结果
        """
        try:
            result = AudioFeaturesResult()

            # v5.10 预处理：响度归一化（保留原始音频用于节奏分析）
            audio_data_raw = audio_data.copy()
            audio_data = AcousticAnalyzer.normalize_loudness(audio_data)

            # 提取基频（如果未提供）
            if f0 is None:
                f0, voiced_flags = self._extract_f0(audio_data)
            else:
                voiced_flags = ~np.isnan(f0)

            # v5.10 预处理：VAD人声分段，过滤纯器乐段
            vocal_segments = AcousticAnalyzer.find_vocal_segments(
                f0, self.hop_length, self.sample_rate
            )
            result._vocal_segment_count = len(vocal_segments)

            if vocal_segments:
                # 提取人声段音频用于声学特征计算
                vocal_audio = AcousticAnalyzer.filter_audio_to_vocal_segments(
                    audio_data, vocal_segments, self.hop_length
                )
                # 声学指标在纯净人声段上计算，减少器乐段干扰
                hnr = self.acoustic_analyzer.calculate_hnr(vocal_audio)
                cpp = self.acoustic_analyzer.calculate_cpp(vocal_audio)

                # v5.11: 节奏分析使用原始全音频（未归一化）
                # 响度归一化会压平动态范围，导致onset检测产生大量误检
                # 使用f0=None强制走传统onset检测路径
                rhythm_result = self.rhythm_analyzer.calculate_rhythm_alignment(
                    audio_data_raw, f0=None, voiced_flags=None
                )
                # 气息分析在人声段上进行
                breath_result = self.breath_analyzer.calculate_breath_stability(
                    vocal_audio, f0=None, singing_style=singing_style, hnr=hnr
                )
            else:
                # 无有效人声段，使用全音频
                hnr = self.acoustic_analyzer.calculate_hnr(audio_data)
                cpp = self.acoustic_analyzer.calculate_cpp(audio_data)
                rhythm_result = self.rhythm_analyzer.calculate_rhythm_alignment(
                    audio_data_raw, f0=None, voiced_flags=None
                )
                breath_result = self.breath_analyzer.calculate_breath_stability(
                    audio_data, f0=f0, singing_style=singing_style, hnr=hnr
                )

            # 音准分析始终使用完整f0（需要全局音高轨迹）
            result.pitch_deviation = self.pitch_analyzer.calculate_pitch_deviation_cents(f0, voiced_flags)
            result.rhythm_alignment = rhythm_result
            result.breath_stability = breath_result
            result.vocal_technique = self.technique_analyzer.detect_vocal_techniques(f0, audio_data)

            # 声学指标
            result.hnr = hnr
            result.cpp = cpp

            # 混合音频检测
            is_mixed, confidence, low_ratio, flatness = self.acoustic_analyzer.detect_mixed_audio(audio_data)
            result.is_mixed_audio = is_mixed
            result.mixed_audio_confidence = confidence

            return result
        except Exception as e:
            logger.exception("特征提取失败")
            return AudioFeaturesResult(success=False, error_message=str(e))

    def _extract_f0(self, audio_data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        提取基频序列

        性能优化：使用yin算法替代pyin，速度提升约2倍
        """
        try:
            f0 = librosa.yin(
                audio_data,
                fmin=self.VOICE_FMIN,
                fmax=self.VOICE_FMAX,
                sr=self.sample_rate,
                hop_length=self.hop_length
            )
            voiced_flags = ~np.isnan(f0)
            return f0, voiced_flags
        except Exception as e:
            logger.warning(f"基频提取失败: {e}")
            return np.array([]), np.array([])

    # ========== 便捷方法（保持向后兼容）==========

    def calculate_pitch_deviation_cents(
        self,
        f0: np.ndarray,
        voiced_flags: np.ndarray
    ) -> PitchDeviationResult:
        """计算音分偏差（便捷方法）"""
        return self.pitch_analyzer.calculate_pitch_deviation_cents(f0, voiced_flags)

    def calculate_rhythm_alignment(
        self,
        audio_data: np.ndarray,
        f0: np.ndarray = None,
        voiced_flags: np.ndarray = None
    ) -> RhythmAlignmentResult:
        """计算节拍对齐度（便捷方法）"""
        return self.rhythm_analyzer.calculate_rhythm_alignment(audio_data, f0, voiced_flags)

    def calculate_breath_stability(
        self,
        audio_data: np.ndarray,
        f0: Optional[np.ndarray] = None,
        singing_style: str = 'pop'
    ) -> BreathStabilityResult:
        """计算气息稳定性（便捷方法）"""
        hnr = self.acoustic_analyzer.calculate_hnr(audio_data)
        return self.breath_analyzer.calculate_breath_stability(
            audio_data, f0=f0, singing_style=singing_style, hnr=hnr
        )

    def detect_vocal_techniques(
        self,
        f0: np.ndarray,
        audio_data: np.ndarray
    ) -> VocalTechniqueResult:
        """检测演唱技巧（便捷方法）"""
        return self.technique_analyzer.detect_vocal_techniques(f0, audio_data)

    def calculate_cpp(self, audio_data: np.ndarray) -> float:
        """计算CPP（便捷方法）"""
        return self.acoustic_analyzer.calculate_cpp(audio_data)

    def calculate_hnr(self, audio_data: np.ndarray) -> float:
        """计算HNR（便捷方法）"""
        return self.acoustic_analyzer.calculate_hnr(audio_data)
