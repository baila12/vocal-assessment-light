"""
人声质量检测器
检测音频是否包含人声、人声占比、是否为纯伴奏/噪声
使用基频检测+谐波分析，适合歌唱人声检测
"""

import numpy as np
import librosa
import logging
from typing import Dict, Any
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
    method: str                  # 检测方法


class VoiceQualityDetector:
    """
    人声质量检测器（针对歌唱优化）

    使用基频检测+谐波分析检测歌唱人声：
    - 基频检测：librosa.pyin 检测人声基频范围 (80-1000Hz)
    - 谐波分析：HPSS分离谐波成分
    - 能量分析：RMS能量分布判断是否有声

    注意：Silero VAD 是为语音检测设计的，不适合歌唱人声检测
    歌唱的声学特征与说话完全不同（持续长音、颤音、音乐伴奏干扰）
    """

    def __init__(self):
        # 不再使用Silero VAD，改用声学特征方法
        self._model_available = True  # 基于librosa，始终可用
        logger.info("[VoiceQualityDetector] Using pitch-based singing voice detection")

    def detect(self, audio_path: str, sr: int = 16000) -> VoiceQualityResult:
        """
        检测音频的人声质量

        Args:
            audio_path: 音频文件路径
            sr: 采样率

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

        return self._detect_singing_voice(y, sr)

    def _detect_singing_voice(self, y: np.ndarray, sr: int) -> VoiceQualityResult:
        """
        基于声学特征检测歌唱人声

        歌唱人声的特征：
        1. 有明显的基频轮廓（人声音高在80-1000Hz）
        2. 有谐波结构（HPSS谐波成分高）
        3. 能量分布有起伏（人声有强弱变化）

        Args:
            y: 音频波形
            sr: 采样率

        Returns:
            VoiceQualityResult
        """
        try:
            # 1. 基频检测 - 最核心的歌唱人声检测方法
            f0, voiced_flags, voiced_probs = librosa.pyin(
                y,
                fmin=librosa.note_to_hz('C2'),  # 约65Hz
                fmax=librosa.note_to_hz('C6'),  # 约1047Hz
                sr=sr
            )

            # 计算有效基频的帧数
            f0_valid = ~np.isnan(f0)
            n_frames = len(f0)

            # 基频在人声范围内的帧
            voice_frames = 0
            for i in range(n_frames):
                if f0_valid[i] and 80 < f0[i] < 1000:
                    voice_frames += 1

            voice_ratio_by_f0 = voice_frames / n_frames if n_frames > 0 else 0

            # 2. 谐波性分析
            try:
                y_harmonic, y_percussive = librosa.effects.hpss(y)
                harmonic_energy = np.sum(y_harmonic**2)
                total_energy = np.sum(y**2)
                harmonic_ratio = harmonic_energy / (total_energy + 1e-10)
            except:
                harmonic_ratio = 0.5

            # 3. 能量分析
            rms = librosa.feature.rms(y=y, hop_length=512)[0]
            rms_mean = np.mean(rms)
            rms_std = np.std(rms)

            # 4. 过零率（用于检测噪声）
            zcr = librosa.feature.zero_crossing_rate(y, hop_length=512)[0]
            zcr_mean = np.mean(zcr)

            # 综合判断
            # 检测噪声：高过零率 + 低谐波性 + 能量均匀
            is_noise = zcr_mean > 0.15 and harmonic_ratio < 0.3 and rms_std / (rms_mean + 1e-10) < 0.5

            # 检测人声：基于基频检测
            has_voice = voice_ratio_by_f0 > 0.1  # 超过10%的帧有人声基频

            # 人声占比：以基频检测为主，谐波分析为辅
            voice_ratio = voice_ratio_by_f0 * 0.8 + harmonic_ratio * 0.2
            voice_ratio = min(1.0, voice_ratio)

            # 检测纯伴奏：无人声基频 + 有能量 + 非噪声
            is_accompaniment_only = not has_voice and not is_noise and rms_mean > 0.01

            # 判断是否适合声乐分析
            is_valid = has_voice and voice_ratio_by_f0 > 0.15 and not is_noise

            # 置信度
            if is_noise:
                confidence = min(1.0, zcr_mean * 5)
            elif has_voice:
                confidence = min(1.0, voice_ratio_by_f0 + 0.3)
            else:
                confidence = 0.5

            return VoiceQualityResult(
                has_voice=has_voice,
                voice_ratio=voice_ratio,
                is_accompaniment_only=is_accompaniment_only,
                is_noise=is_noise,
                is_valid_for_analysis=is_valid,
                confidence=confidence,
                method='pitch_harmonic'
            )

        except Exception as e:
            logger.error(f"[VoiceQualityDetector] Singing voice detection failed: {e}")
            return VoiceQualityResult(
                has_voice=False,
                voice_ratio=0.0,
                is_accompaniment_only=False,
                is_noise=True,
                is_valid_for_analysis=False,
                confidence=0.0,
                method='error'
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
