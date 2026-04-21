"""
人声质量检测服务

检测上传的音频是否包含有效人声，避免对非人声音频给出不合理的高分
"""

import numpy as np
import librosa
from dataclasses import dataclass
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


@dataclass
class VoiceQualityResult:
    """人声质量检测结果 DTO"""
    is_voice: bool                  # 是否为人声
    voice_ratio: float              # 人声占比 (0-1)
    quality_score: float            # 人声质量分数 (0-100)
    silence_ratio: float            # 静音占比 (0-1)
    noise_ratio: float              # 噪声占比 (0-1)
    harmonic_ratio: float           # 谐波占比 (0-1)
    pitch_consistency: float        # 音高一致性 (0-1)
    warnings: list                  # 警告信息列表
    suggestions: list               # 改进建议


class VoiceQualityService:
    """
    人声质量检测服务

    通过多个维度判断音频是否为有效人声：
    - 谐波结构分析
    - 基频范围检测
    - 能量分布特征
    - 频谱特征分析
    """

    # 人声基频范围 (Hz)
    VOICE_FMIN = 80      # 男声最低
    VOICE_FMAX = 1000    # 女声最高

    # 最小有效音频时长 (秒)
    MIN_DURATION = 2.0

    # 人声检测阈值
    MIN_VOICE_RATIO = 0.3       # 最小人声占比
    MIN_HARMONIC_RATIO = 0.4    # 最小谐波占比
    MAX_SILENCE_RATIO = 0.6     # 最大静音占比

    def __init__(self, sample_rate: int = 22050):
        self.sample_rate = sample_rate

    def analyze(self, audio_data: np.ndarray) -> VoiceQualityResult:
        """
        分析音频的人声质量

        Args:
            audio_data: 音频数据

        Returns:
            VoiceQualityResult: 检测结果
        """
        warnings = []
        suggestions = []

        duration = len(audio_data) / self.sample_rate

        # 1. 时长检查
        if duration < self.MIN_DURATION:
            warnings.append(f"音频时长过短 ({duration:.1f}秒)，建议至少 {self.MIN_DURATION}秒")
            suggestions.append("录制更长时间的音频以获得准确评估")

        # 2. 静音检测
        silence_ratio = self._detect_silence(audio_data)

        # 3. 基频分析
        f0, voiced_flags, pitch_consistency = self._analyze_pitch(audio_data)
        voice_ratio = np.mean(voiced_flags) if len(voiced_flags) > 0 else 0

        # 4. 谐波分析
        harmonic_ratio = self._analyze_harmonics(audio_data)

        # 5. 噪声分析
        noise_ratio = self._analyze_noise(audio_data)

        # 6. 频谱特征分析（区分合成音和人声）
        spectral_features = self._analyze_spectral_features(audio_data)

        # 综合判断是否为人声
        is_voice = self._determine_voice_presence(
            voice_ratio=voice_ratio,
            harmonic_ratio=harmonic_ratio,
            silence_ratio=silence_ratio,
            pitch_consistency=pitch_consistency,
            spectral_features=spectral_features
        )

        # 计算质量分数
        quality_score = self._calculate_quality_score(
            voice_ratio=voice_ratio,
            harmonic_ratio=harmonic_ratio,
            silence_ratio=silence_ratio,
            pitch_consistency=pitch_consistency,
            noise_ratio=noise_ratio
        )

        # 生成警告和建议
        if not is_voice:
            if voice_ratio < self.MIN_VOICE_RATIO:
                warnings.append("未检测到明显的人声信号")
                suggestions.append("请确保麦克风正常工作并录制清晰的人声")
            if harmonic_ratio < self.MIN_HARMONIC_RATIO:
                warnings.append("音频缺乏人声特有的谐波结构")
                suggestions.append("这可能不是人声录音，或录音质量过差")

        if silence_ratio > self.MAX_SILENCE_RATIO:
            warnings.append(f"静音占比过高 ({silence_ratio*100:.0f}%)")
            suggestions.append("请减少录音中的空白段落")

        if pitch_consistency < 0.3:
            warnings.append("音高检测不稳定")
            suggestions.append("可能是伴奏音乐或噪音，而非清晰人声")

        # 检测是否为合成音（如正弦波测试音）
        if spectral_features.get('is_synthetic', False):
            warnings.append("检测到合成音频特征，非真实人声")
            suggestions.append("请使用真实人声录音进行评估")
            is_voice = False

        return VoiceQualityResult(
            is_voice=is_voice,
            voice_ratio=voice_ratio,
            quality_score=quality_score,
            silence_ratio=silence_ratio,
            noise_ratio=noise_ratio,
            harmonic_ratio=harmonic_ratio,
            pitch_consistency=pitch_consistency,
            warnings=warnings,
            suggestions=suggestions
        )

    def _detect_silence(self, audio_data: np.ndarray) -> float:
        """检测静音占比"""
        rms = librosa.feature.rms(y=audio_data)[0]
        silence_threshold = np.max(rms) * 0.05  # 5% of max as silence threshold
        silent_frames = np.sum(rms < silence_threshold)
        return silent_frames / len(rms) if len(rms) > 0 else 1.0

    def _analyze_pitch(self, audio_data: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float]:
        """分析基频，返回 f0、有声帧标记、音高一致性"""
        try:
            f0, voiced_flags, voiced_probs = librosa.pyin(
                audio_data,
                fmin=self.VOICE_FMIN,
                fmax=self.VOICE_FMAX,
                sr=self.sample_rate
            )

            # 有效音高值
            valid_f0 = f0[~np.isnan(f0)]

            if len(valid_f0) > 10:
                # 计算音高一致性（基于音高变化的标准差）
                f0_normalized = valid_f0 / np.mean(valid_f0)
                pitch_std = np.std(f0_normalized)
                # 音高一致性：变化越小越一致，但完全不变也不是好的人声
                pitch_consistency = max(0, 1 - pitch_std * 2)
                pitch_consistency = min(1, pitch_consistency)
            else:
                pitch_consistency = 0.1

            return f0, voiced_flags, pitch_consistency

        except Exception as e:
            logger.warning(f"Pitch analysis failed: {e}")
            return np.array([]), np.array([]), 0.0

    def _analyze_harmonics(self, audio_data: np.ndarray) -> float:
        """分析谐波占比"""
        try:
            harmonic, percussive = librosa.effects.hpss(audio_data)

            harmonic_energy = np.sum(harmonic ** 2)
            total_energy = np.sum(audio_data ** 2) + 1e-10

            return harmonic_energy / total_energy

        except Exception as e:
            logger.warning(f"Harmonic analysis failed: {e}")
            return 0.0

    def _analyze_noise(self, audio_data: np.ndarray) -> float:
        """分析噪声占比"""
        try:
            # 使用频谱平坦度检测噪声
            spectral_flatness = librosa.feature.spectral_flatness(y=audio_data)[0]
            # 高平坦度意味着更接近噪声
            return np.mean(spectral_flatness)

        except Exception as e:
            logger.warning(f"Noise analysis failed: {e}")
            return 0.5

    def _analyze_spectral_features(self, audio_data: np.ndarray) -> dict:
        """分析频谱特征，检测是否为合成音"""
        try:
            # 计算频谱质心
            spectral_centroid = librosa.feature.spectral_centroid(
                y=audio_data, sr=self.sample_rate
            )[0]

            # 计算频谱带宽
            spectral_bandwidth = librosa.feature.spectral_bandwidth(
                y=audio_data, sr=self.sample_rate
            )[0]

            # 合成音特征：频谱特征非常稳定（变化极小）
            centroid_std = np.std(spectral_centroid) / (np.mean(spectral_centroid) + 1e-10)
            bandwidth_std = np.std(spectral_bandwidth) / (np.mean(spectral_bandwidth) + 1e-10)

            # 方法1：频谱变化极小
            is_synthetic_method1 = centroid_std < 0.01 and bandwidth_std < 0.05

            # 方法2：检测FFT频谱是否集中在少数频率（合成音特征）
            fft = np.abs(np.fft.rfft(audio_data))
            fft_normalized = fft / (np.max(fft) + 1e-10)
            # 统计显著频率成分数量（能量 > 最大能量的10%）
            significant_components = np.sum(fft_normalized > 0.1)
            # 合成音通常只有少数几个显著频率成分
            is_synthetic_method2 = significant_components < 5

            # 方法3：检测频谱熵（合成音熵值低）
            fft_prob = fft / (np.sum(fft) + 1e-10)
            spectral_entropy = -np.sum(fft_prob * np.log2(fft_prob + 1e-10))
            # 合成音熵值通常 < 5
            is_synthetic_method3 = spectral_entropy < 5

            # 综合判断：任一方法判定为合成音即认为是合成音
            is_synthetic = is_synthetic_method1 or is_synthetic_method2 or is_synthetic_method3

            return {
                'centroid_mean': np.mean(spectral_centroid),
                'centroid_std': centroid_std,
                'bandwidth_mean': np.mean(spectral_bandwidth),
                'bandwidth_std': bandwidth_std,
                'significant_components': significant_components,
                'spectral_entropy': spectral_entropy,
                'is_synthetic': is_synthetic
            }

        except Exception as e:
            logger.warning(f"Spectral analysis failed: {e}")
            return {'is_synthetic': False}

    def _determine_voice_presence(
        self,
        voice_ratio: float,
        harmonic_ratio: float,
        silence_ratio: float,
        pitch_consistency: float,
        spectral_features: dict
    ) -> bool:
        """综合判断是否为有效人声"""
        # 如果是合成音，直接返回 False
        if spectral_features.get('is_synthetic', False):
            return False

        # 静音太多，不是有效人声
        if silence_ratio > self.MAX_SILENCE_RATIO:
            return False

        # 人声占比太低
        if voice_ratio < self.MIN_VOICE_RATIO:
            return False

        # 谐波占比太低
        if harmonic_ratio < self.MIN_HARMONIC_RATIO:
            return False

        return True

    def _calculate_quality_score(
        self,
        voice_ratio: float,
        harmonic_ratio: float,
        silence_ratio: float,
        pitch_consistency: float,
        noise_ratio: float
    ) -> float:
        """计算人声质量分数 (0-100)"""
        # 各维度权重
        weights = {
            'voice_ratio': 0.3,
            'harmonic_ratio': 0.25,
            'silence_penalty': 0.2,
            'pitch_consistency': 0.15,
            'noise_penalty': 0.1
        }

        # 人声占比得分
        voice_score = voice_ratio * 100

        # 谐波得分
        harmonic_score = harmonic_ratio * 100

        # 静音惩罚
        silence_penalty = (1 - silence_ratio) * 100

        # 音高一致性得分
        pitch_score = pitch_consistency * 100

        # 噪声惩罚
        noise_penalty = (1 - noise_ratio) * 100

        # 加权平均
        quality_score = (
            voice_score * weights['voice_ratio'] +
            harmonic_score * weights['harmonic_ratio'] +
            silence_penalty * weights['silence_penalty'] +
            pitch_score * weights['pitch_consistency'] +
            noise_penalty * weights['noise_penalty']
        )

        return max(0, min(100, quality_score))
