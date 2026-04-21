"""
人声质量检测器 (使用Silero VAD)
检测音频是否包含人声、人声占比、是否为纯伴奏/噪声
支持ONNX模型推理，模型不可用时降级到启发式算法
"""

import numpy as np
import librosa
import logging
import os
from typing import Dict, Any, Tuple, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class VoiceQualityResult:
    """人声质量检测结果"""
    has_voice: bool              # 是否包含人声
    voice_ratio: float           # 人声占比 (0-1)
    is_accompaniment_only: bool  # 是否为纯伴奏
    is_noise: bool               # 是否为噪声
    is_valid_for_analysis: bool  # 是否适合进行声乐分析
    confidence: float            # 检测置信度 (0-1)
    method: str                  # 检测方法 (dl/heuristic)


class VoiceQualityDetector:
    """
    人声质量检测器

    使用Silero VAD模型检测语音活动：
    - 模型大小: ~2.2MB
    - 推理速度: 实时
    - 准确率: >95%

    模型不可用时自动降级到启发式算法
    """

    # Silero VAD模型路径
    SILERO_MODEL_PATH = 'models/voice_quality/silero_vad.onnx'

    def __init__(self):
        self._session = None
        self._model_available = False

        # 尝试加载Silero VAD模型
        if os.path.exists(self.SILERO_MODEL_PATH):
            try:
                import onnxruntime as ort
                self._session = ort.InferenceSession(
                    self.SILERO_MODEL_PATH,
                    providers=['CPUExecutionProvider']
                )
                self._model_available = True
                logger.info(f"[VoiceQualityDetector] Silero VAD loaded from {self.SILERO_MODEL_PATH}")
            except Exception as e:
                logger.warning(f"[VoiceQualityDetector] Failed to load Silero VAD: {e}")

        if not self._model_available:
            logger.info("[VoiceQualityDetector] Using heuristic fallback")

    def detect(self, audio_path: str, sr: int = 16000) -> VoiceQualityResult:
        """
        检测音频的人声质量

        Args:
            audio_path: 音频文件路径
            sr: 采样率 (默认16kHz，Silero VAD要求)

        Returns:
            VoiceQualityResult: 检测结果
        """
        # 加载音频
        try:
            y, sr = librosa.load(audio_path, sr=sr, mono=True)
        except Exception as e:
            logger.error(f"[VoiceQualityDetector] Failed to load audio: {e}")
            return VoiceQualityResult(
                has_voice=False,
                voice_ratio=0.0,
                is_accompaniment_only=False,
                is_noise=True,
                is_valid_for_analysis=False,
                confidence=1.0,
                method='error'
            )

        # 尝试使用Silero VAD
        if self._model_available:
            return self._detect_silero(y, sr)
        else:
            return self._detect_heuristic(y, sr)

    def _detect_silero(self, y: np.ndarray, sr: int) -> VoiceQualityResult:
        """
        使用Silero VAD检测语音活动

        Args:
            y: 音频波形
            sr: 采样率

        Returns:
            VoiceQualityResult
        """
        try:
            # Silero VAD参数
            window_size_samples = 512  # 32ms @ 16kHz
            threshold = 0.5

            # 获取模型输入信息
            input_names = [inp.name for inp in self._session.get_inputs()]

            # 初始化状态 - Silero VAD使用 'state' 输入 (形状: [2, 1, 128])
            state = np.zeros((2, 1, 128), dtype=np.float32)

            # 分帧处理
            speech_frames = []
            total_frames = 0

            for i in range(0, len(y) - window_size_samples, window_size_samples):
                chunk = y[i:i + window_size_samples].astype(np.float32)
                total_frames += 1

                # 运行VAD推理
                ort_inputs = {
                    'input': chunk[np.newaxis, :],  # [1, 512] - rank 2
                    'state': state,
                    'sr': np.array(sr, dtype=np.int64)
                }

                out, state = self._session.run(
                    ['output', 'stateN'],
                    ort_inputs
                )

                speech_prob = out[0][0]
                speech_frames.append(speech_prob > threshold)

            # 计算语音占比
            speech_count = sum(speech_frames)
            voice_ratio = speech_count / total_frames if total_frames > 0 else 0

            # 判断结果
            has_voice = voice_ratio > 0.1  # 至少10%是语音
            is_noise = voice_ratio < 0.05 and np.std(y) < 0.01  # 几乎无语音且能量低
            is_accompaniment_only = not has_voice and not is_noise

            # 判断是否适合声乐分析
            is_valid = has_voice and voice_ratio > 0.2

            return VoiceQualityResult(
                has_voice=has_voice,
                voice_ratio=voice_ratio,
                is_accompaniment_only=is_accompaniment_only,
                is_noise=is_noise,
                is_valid_for_analysis=is_valid,
                confidence=max(voice_ratio, 1 - voice_ratio),
                method='silero_vad'
            )

        except Exception as e:
            logger.error(f"[VoiceQualityDetector] Silero VAD failed: {e}")
            return self._detect_heuristic(y, sr)

    def _detect_heuristic(self, y: np.ndarray, sr: int) -> VoiceQualityResult:
        """
        启发式检测算法（降级方案）

        基于以下特征判断：
        1. RMS能量分布 - 人声通常有明显的能量起伏
        2. 频谱质心 - 人声通常在200-2000Hz
        3. 过零率 - 人声通常有中等过零率
        4. 谐波性 - 人声有明显谐波结构

        Args:
            y: 音频波形
            sr: 采样率

        Returns:
            VoiceQualityResult
        """
        # 1. 计算RMS能量
        rms = librosa.feature.rms(y=y, hop_length=512)[0]
        rms_mean = np.mean(rms)
        rms_std = np.std(rms)

        # 2. 计算频谱质心
        cent = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=512)[0]
        cent_mean = np.mean(cent)

        # 3. 计算过零率
        zcr = librosa.feature.zero_crossing_rate(y, hop_length=512)[0]
        zcr_mean = np.mean(zcr)

        # 4. 计算谐波性 (使用HPSS分离)
        try:
            y_harmonic, y_percussive = librosa.effects.hpss(y)
            harmonic_ratio = np.sum(y_harmonic ** 2) / (np.sum(y ** 2) + 1e-10)
        except:
            harmonic_ratio = 0.5

        # 判断逻辑

        # 检测噪声：高过零率 + 低谐波性 + 能量均匀
        is_noise = zcr_mean > 0.15 and harmonic_ratio < 0.3 and rms_std / (rms_mean + 1e-10) < 0.5

        # 检测人声：
        # - 频谱质心在人声范围 (200-2000Hz)
        # - 有明显谐波结构
        # - RMS有起伏（人声有强弱变化）
        has_voice_features = (
            200 < cent_mean < 2000 and
            harmonic_ratio > 0.4 and
            rms_std / (rms_mean + 1e-10) > 0.3
        )

        # 估算人声占比
        if has_voice_features:
            # 基于谐波性估算
            voice_ratio = min(1.0, harmonic_ratio * 1.5)
        else:
            voice_ratio = 0.0

        has_voice = has_voice_features and voice_ratio > 0.2

        # 检测纯伴奏
        is_accompaniment_only = not has_voice and not is_noise and rms_mean > 0.01

        # 判断是否适合分析
        is_valid = has_voice and voice_ratio > 0.3 and not is_noise

        # 置信度估算
        if is_noise:
            confidence = min(1.0, zcr_mean * 5)
        elif has_voice:
            confidence = min(1.0, harmonic_ratio + 0.3)
        else:
            confidence = 0.5

        return VoiceQualityResult(
            has_voice=has_voice,
            voice_ratio=voice_ratio,
            is_accompaniment_only=is_accompaniment_only,
            is_noise=is_noise,
            is_valid_for_analysis=is_valid,
            confidence=confidence,
            method='heuristic'
        )

    def get_analysis_recommendation(self, result: VoiceQualityResult) -> str:
        """
        根据检测结果给出分析建议

        Args:
            result: 检测结果

        Returns:
            建议文本
        """
        if result.is_valid_for_analysis:
            return "Audio is suitable for vocal analysis"

        if result.is_noise:
            return "Noise or invalid audio detected, please use a different file"

        if result.is_accompaniment_only:
            return "Accompaniment-only audio detected, no vocals found"

        if not result.has_voice:
            return "No clear vocals detected, analysis may be inaccurate"

        if result.voice_ratio < 0.3:
            return "Low vocal ratio, results may be inaccurate"

        return "Audio quality issues detected, consider using a clearer recording"
