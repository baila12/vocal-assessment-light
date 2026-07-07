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
from typing import Optional
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

# v5.18 新算法 (Feature Flag 控制)
from services.feature_flags import FeatureFlags
from services.features.hnr import MultiScaleHNR
from services.features.cpp import PraatCPP
from services.features.voicing import VoicingDetector

# v5.20 混响补偿 (HPSS+谱减法 → HNR/CPP修正)
from services.features.reverb import ReverbCompensator

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

        # v5.18 新算法 (Feature Flag 控制, 默认不启用)
        self.multiscale_hnr = MultiScaleHNR(sample_rate)
        self.praat_cpp = PraatCPP()
        self.voicing_detector = VoicingDetector(sample_rate, hop_length)

        # v5.20 混响补偿器 (Feature Flag 控制, 默认不启用)
        self.reverb_compensator = ReverbCompensator(sample_rate=sample_rate)

    def extract_all_features(
        self,
        audio_data: np.ndarray,
        f0: Optional[np.ndarray] = None,
        singing_style: str = 'pop',
        is_separated: bool = False,
        feature_flags: Optional[FeatureFlags] = None
    ) -> AudioFeaturesResult:
        """
        提取所有高级特征 v5.18

        Args:
            audio_data: 音频数据
            f0: 基频序列（可选，未提供则自动提取）
            singing_style: 唱法类型 (pop/classical/folk/rap)
            is_separated: 是否为Demucs分离后的纯净人声 (用于CV映射修正)
            feature_flags: FeatureFlags 功能开关 (v5.18)

        Returns:
            AudioFeaturesResult: 综合特征提取结果
        """
        try:
            result = AudioFeaturesResult()

            # v5.10 预处理：响度归一化（保留原始音频用于节奏分析）
            audio_data_raw = audio_data.copy()
            audio_data = AcousticAnalyzer.normalize_loudness(audio_data)

            # v6.2: 预计算 HPSS 分离 (避免 acoustic/breath 三处重复调用)
            # librosa.effects.hpss 是 O(N log N), 缓存可节省 ~1.5s/次
            try:
                hpss_harmonic, hpss_percussive = librosa.effects.hpss(
                    audio_data, margin=(1.0, 3.0)
                )
            except Exception:
                hpss_harmonic, hpss_percussive = None, None
            result._hpss_harmonic = hpss_harmonic
            result._hpss_percussive = hpss_percussive

            # 提取基频（如果未提供）
            if f0 is None:
                f0, voiced_flags = self._extract_f0(audio_data, feature_flags)
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

                # v5.20: 混响补偿 — HPSS+谱减法抑制混响扩散尾 [Fitzgerald 2010, Boll 1979]
                # 补偿后音频仅用于 HNR/CPP 计算, 不影响音准/节奏/气息等其他特征
                acoustic_audio = vocal_audio
                if (
                    feature_flags is not None
                    and feature_flags.enable_reverb_compensation
                    and len(vocal_audio) >= 2048
                ):
                    compensated, reverb_result = self.reverb_compensator.process(
                        vocal_audio, return_result=True
                    )
                    acoustic_audio = compensated
                    logger.info(
                        f"混响补偿: noise_reduction={reverb_result.noise_reduction_db:.1f}dB, "
                        f"HPSS harmonic_ratio={reverb_result.hpss_harmonic_ratio:.2f}"
                    )
                    result._reverb_compensation = reverb_result

                # 声学指标在纯净人声段上计算，减少器乐段干扰
                hnr = self.acoustic_analyzer.calculate_hnr(acoustic_audio)
                cpp = self.acoustic_analyzer.calculate_cpp(acoustic_audio)

                # v5.13: 节奏分析使用原始音频(未归一化)
                # f0路径暂不启用(需校准验证后恢复), 先修CV映射
                # is_clean_vocal标记用于专业模式纯净人声的CV映射修正
                rhythm_result = self.rhythm_analyzer.calculate_rhythm_alignment(
                    audio_data_raw,
                    f0=None, voiced_flags=None,  # f0路径留到校准后启用
                    is_clean_vocal=is_separated
                )
                # 气息分析在人声段上进行
                breath_result = self.breath_analyzer.calculate_breath_stability(
                    vocal_audio, f0=f0, singing_style=singing_style, hnr=hnr
                )
            else:
                # 无有效人声段，使用全音频

                # v5.20: 混响补偿 (与有声段路径一致)
                acoustic_audio = audio_data
                if (
                    feature_flags is not None
                    and feature_flags.enable_reverb_compensation
                    and len(audio_data) >= 2048
                ):
                    compensated, reverb_result = self.reverb_compensator.process(
                        audio_data, return_result=True
                    )
                    acoustic_audio = compensated
                    logger.info(
                        f"混响补偿(全音频): noise_reduction={reverb_result.noise_reduction_db:.1f}dB"
                    )
                    result._reverb_compensation = reverb_result

                hnr = self.acoustic_analyzer.calculate_hnr(acoustic_audio)
                cpp = self.acoustic_analyzer.calculate_cpp(acoustic_audio)
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

            # v5.18: Feature Flag 控制的新算法替换
            if feature_flags is not None:
                if feature_flags.enable_multiscale_hnr:
                    self._apply_multiscale_hnr(
                        result, vocal_audio if vocal_segments else audio_data, f0
                    )
                if feature_flags.enable_praat_cpp:
                    self._apply_praat_cpp(
                        result, vocal_audio if vocal_segments else audio_data
                    )
                if feature_flags.enable_voicing_detection:
                    self._apply_voicing_detection(result, f0, voiced_flags)

            # 混合音频检测 (v6.0: 返回 metadata dict)
            is_mixed, confidence, metadata = self.acoustic_analyzer.detect_mixed_audio(audio_data)
            result.is_mixed_audio = is_mixed
            result.mixed_audio_confidence = confidence
            result._mixed_metadata = metadata

            return result
        except Exception as e:
            logger.exception("特征提取失败")
            return AudioFeaturesResult(success=False, error_message=str(e))

    # ── v5.18 Feature Flag 私有方法 ──

    def _apply_multiscale_hnr(
        self, result: AudioFeaturesResult, audio: np.ndarray, f0: np.ndarray
    ) -> None:
        """多频带 HNR: de Krom 1993 倒谱法 (对齐 VoiceLab)"""
        ms_hnr_result = self.multiscale_hnr.analyze(audio, f0=f0)
        result.hnr = ms_hnr_result.hnr_medium
        logger.debug(
            f"MultiScaleHNR: hnr={result.hnr:.1f}dB "
            f"({ms_hnr_result.hnr_short}/{ms_hnr_result.hnr_medium}/"
            f"{ms_hnr_result.hnr_long}, "
            f"stability={ms_hnr_result.hnr_stability:.3f})"
        )

    def _apply_praat_cpp(
        self, result: AudioFeaturesResult, audio: np.ndarray
    ) -> None:
        """Praat CPP: VoiceLab parselmouth 方法"""
        cpp_result = self.praat_cpp.analyze(audio, sample_rate=self.sample_rate)
        # VoiceLab CPP 范围 ~5-40 dB; 现有 pipeline CPP 范围 ~0-5
        # 归一化因子 /6.0: 将 24dB (优质人声) 映射到 4.0 (优秀档位)
        result.cpp = cpp_result.cpp_mean / 6.0
        logger.debug(
            f"PraatCPP: raw={cpp_result.cpp_mean:.1f} "
            f"normalized={result.cpp:.2f}"
        )

    def _apply_voicing_detection(
        self, result: AudioFeaturesResult,
        f0: np.ndarray, voiced_flags: np.ndarray
    ) -> None:
        """Voicing Detection: PYIN 决策质量评估"""
        vd_result = self.voicing_detector.evaluate(f0, voiced_flags)
        result._voicing_detection = vd_result
        logger.info(
            f"VoicingDetector: confidence={vd_result.detection_confidence:.2f} "
            f"voicing_ratio={vd_result.voicing_ratio:.2f}"
        )

    # ── f0 提取 ──

    def _extract_f0(
        self, audio_data: np.ndarray, feature_flags: Optional[FeatureFlags] = None
    ) -> tuple:
        """
        提取基频序列 v5.18

        使用 librosa.yin 算法。当 feature_flags.enable_torchcrepe_fallback=True
        且 PYIN detection_rate < 0.5 时，自动切换到 TorchCREPE。

        性能优化：yin 算法比 pyin 快约 2 倍。
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

            # v5.18: TorchCREPE fallback when PYIN confidence is low
            if feature_flags is not None and feature_flags.enable_torchcrepe_fallback:
                detection_rate = np.mean(voiced_flags) if len(voiced_flags) > 0 else 0.0
                if detection_rate < 0.5 and len(audio_data) > 0:
                    logger.info(
                        f"PYIN detection_rate={detection_rate:.2f} < 0.5, "
                        f"falling back to TorchCREPE"
                    )
                    f0_crepe = self._extract_f0_crepe(audio_data)
                    if f0_crepe is not None and len(f0_crepe) > 0:
                        f0 = f0_crepe
                        voiced_flags = ~np.isnan(f0)
                        logger.info(
                            f"TorchCREPE fallback: {len(f0)} frames, "
                            f"detection_rate={np.mean(voiced_flags):.2f}"
                        )

            return f0, voiced_flags

        except Exception as e:
            logger.warning(f"基频提取失败: {e}")
            return np.array([]), np.array([])

    def _extract_f0_crepe(self, audio_data: np.ndarray) -> Optional[np.ndarray]:
        """
        使用 TorchCREPE 提取基频 v5.18

        CREPE 是基于深度学习的单音基频检测器，对噪声和低质量音频更鲁棒。
        权重约 5MB，使用 model='full' (最大容量, 最高精度)。

        Args:
            audio_data: 音频数据

        Returns:
            f0: 基频序列 (Hz), NaN = unvoiced; 失败返回 None
        """
        try:
            import torch
            import torchcrepe

            # 转换到 torch tensor
            audio_tensor = torch.from_numpy(
                audio_data.astype(np.float32)
            ).unsqueeze(0)  # [1, samples]

            # CREPE 基频检测
            f0, confidence = torchcrepe.predict(
                audio_tensor,
                sample_rate=self.sample_rate,
                hop_length=self.hop_length,
                fmin=self.VOICE_FMIN,
                fmax=self.VOICE_FMAX,
                model='full',
                batch_size=1024,
                device='cpu',
                return_confidence=True
            )

            # 转换回 numpy: confidence < 0.5 → NaN (unvoiced)
            f0_np = f0.squeeze().detach().cpu().numpy()
            conf_np = confidence.squeeze().detach().cpu().numpy()

            # 低置信度帧标记为 unvoiced
            f0_np[conf_np < 0.5] = np.nan

            # 调整长度以匹配 PYIN 输出
            expected_len = 1 + (len(audio_data) - self.hop_length) // self.hop_length
            if len(f0_np) < expected_len:
                # 补零 (NaN)
                padded = np.full(expected_len, np.nan)
                padded[:len(f0_np)] = f0_np
                f0_np = padded
            elif len(f0_np) > expected_len:
                f0_np = f0_np[:expected_len]

            return f0_np

        except ImportError:
            logger.warning("torchcrepe 未安装，无法使用 CREPE fallback")
            return None
        except Exception as e:
            logger.warning(f"TorchCREPE 提取失败: {e}")
            return None

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
