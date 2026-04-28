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
        提取所有高级特征

        Args:
            audio_data: 音频数据
            f0: 基频序列（可选，未提供则自动提取）
            singing_style: 唱法类型 (pop/classical/folk/rap)

        Returns:
            AudioFeaturesResult: 综合特征提取结果
        """
        try:
            result = AudioFeaturesResult()

            # 提取基频（如果未提供）
            if f0 is None:
                f0, voiced_flags = self._extract_f0(audio_data)
            else:
                voiced_flags = ~np.isnan(f0)

            # 计算声学指标（用于气息分析）
            hnr = self.acoustic_analyzer.calculate_hnr(audio_data)

            # 并行调用各分析器
            result.pitch_deviation = self.pitch_analyzer.calculate_pitch_deviation_cents(f0, voiced_flags)
            result.rhythm_alignment = self.rhythm_analyzer.calculate_rhythm_alignment(
                audio_data, f0=f0, voiced_flags=voiced_flags
            )
            result.breath_stability = self.breath_analyzer.calculate_breath_stability(
                audio_data, f0=f0, singing_style=singing_style, hnr=hnr
            )
            result.vocal_technique = self.technique_analyzer.detect_vocal_techniques(f0, audio_data)

            # 声学指标
            result.hnr = hnr
            result.cpp = self.acoustic_analyzer.calculate_cpp(audio_data)

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
