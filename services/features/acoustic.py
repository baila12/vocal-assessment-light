"""
声学指标计算模块

包含：
1. HNR (谐波噪声比) - 反映声带闭合程度
2. CPP (倒谱峰值显著性) - 反映声带闭合质量
3. 混合音频检测 - 检测是否带有伴奏，调整HNR评估策略
"""
from dataclasses import dataclass
import numpy as np
import librosa
import logging

logger = logging.getLogger(__name__)


@dataclass
class AcousticResult:
    """声学分析结果"""
    hnr: float = 0.0
    cpp: float = 0.0
    is_mixed_audio: bool = False
    mixed_audio_confidence: float = 0.0
    low_freq_ratio: float = 0.0
    spectral_flatness: float = 0.0


class AcousticAnalyzer:
    """声学指标分析器"""

    def __init__(self, sample_rate: int = 22050, hop_length: int = 512):
        self.sample_rate = sample_rate
        self.hop_length = hop_length

    def calculate_hnr(self, audio_data: np.ndarray) -> float:
        """
        计算谐波噪声比 (Harmonics-to-Noise Ratio)

        HNR 反映声带闭合程度，值越高声带闭合越好

        Args:
            audio_data: 音频数据

        Returns:
            float: HNR值 (dB)
        """
        try:
            harmonic, percussive = librosa.effects.hpss(audio_data, margin=(1.0, 3.0))
            harmonic_energy = np.sum(harmonic ** 2)
            residual_energy = np.sum((audio_data - harmonic) ** 2) + 1e-10

            if harmonic_energy > 0 and residual_energy > 0:
                hnr = 10 * np.log10(harmonic_energy / residual_energy)
                return float(max(0, min(40, hnr)))
            return 0.0

        except Exception as e:
            logger.warning(f"HNR 计算失败: {e}")
            return 0.0

    def calculate_cpp(self, audio_data: np.ndarray) -> float:
        """
        计算倒谱峰值显著性 (Cepstral Peak Prominence)

        CPP 反映声带闭合质量，值越高声带闭合越好

        Args:
            audio_data: 音频数据

        Returns:
            float: CPP值
        """
        try:
            frame_length = 2048
            frames = librosa.util.frame(
                audio_data, frame_length=frame_length, hop_length=self.hop_length
            )

            cpp_values = []
            min_quefrency = int(0.002 * self.sample_rate)
            max_quefrency = int(0.02 * self.sample_rate)

            for frame in frames.T:
                if np.max(np.abs(frame)) < 1e-6:
                    continue

                spectrum = np.abs(np.fft.rfft(frame))
                log_spectrum = np.log(spectrum + 1e-10)
                cepstrum = np.fft.ifft(log_spectrum).real

                if max_quefrency < len(cepstrum):
                    search_range = cepstrum[min_quefrency:max_quefrency]
                    if len(search_range) > 0:
                        peak = np.max(search_range)
                        baseline = np.mean(search_range)
                        cpp_values.append(peak - baseline)

            return float(np.mean(cpp_values)) if cpp_values else 0.0

        except Exception as e:
            logger.warning(f"CPP 计算失败: {e}")
            return 0.0

    def detect_mixed_audio(self, audio_data: np.ndarray) -> tuple:
        """
        检测是否为混合音频（带伴奏）

        混合音频特征：
        1. 低频能量占比高（伴奏通常有低频乐器）
        2. 频谱平坦度高（多乐器叠加）
        3. 立体声相关性（如果有）

        Args:
            audio_data: 音频数据

        Returns:
            (is_mixed, confidence, low_freq_ratio, spectral_flatness)
        """
        try:
            # 计算频谱
            stft = np.abs(librosa.stft(audio_data))
            spectrum = np.mean(stft, axis=1)

            # 1. 低频能量占比（人声主要在 300-3000Hz，伴奏有更多低频）
            freqs = librosa.fft_frequencies(sr=self.sample_rate)
            voice_band_mask = (freqs >= 300) & (freqs <= 3000)
            low_freq_mask = freqs < 300

            voice_energy = np.sum(spectrum[voice_band_mask] ** 2)
            low_energy = np.sum(spectrum[low_freq_mask] ** 2)
            total_energy = np.sum(spectrum ** 2) + 1e-10

            low_freq_ratio = low_energy / total_energy
            voice_ratio = voice_energy / total_energy

            # 2. 频谱平坦度（混合音频频谱更平坦）
            spectral_flatness = librosa.feature.spectral_flatness(
                S=stft, hop_length=self.hop_length
            )
            mean_flatness = np.mean(spectral_flatness)

            # 3. 判断逻辑
            # 纯人声：低频占比 < 0.3，频谱平坦度 < 0.3
            # 混合音频：低频占比 > 0.4 或 频谱平坦度 > 0.4

            is_mixed = False
            confidence = 0.0

            if low_freq_ratio > 0.5:
                # 高低频能量，很可能是混合音频
                is_mixed = True
                confidence = 0.7 + (low_freq_ratio - 0.5) * 0.6
            elif low_freq_ratio > 0.35:
                # 中等低频能量，结合频谱平坦度判断
                if mean_flatness > 0.35:
                    is_mixed = True
                    confidence = 0.5 + (mean_flatness - 0.35)
                else:
                    # 可能是低音域歌手
                    confidence = 0.3
            else:
                # 低频能量低，可能是纯人声
                is_mixed = False
                confidence = 1.0 - low_freq_ratio

            confidence = max(0.0, min(1.0, confidence))

            logger.debug(
                f"混合音频检测: is_mixed={is_mixed}, confidence={confidence:.2f}, "
                f"low_freq_ratio={low_freq_ratio:.2f}, flatness={mean_flatness:.2f}"
            )

            return is_mixed, confidence, low_freq_ratio, float(mean_flatness)

        except Exception as e:
            logger.warning(f"混合音频检测失败: {e}")
            return False, 0.0, 0.0, 0.0

    @staticmethod
    def normalize_loudness(audio_data: np.ndarray, target_rms: float = 0.05) -> np.ndarray:
        """
        响度归一化 v5.10

        使用RMS归一化减少录音条件差异（麦克风距离/增益/房间声学）。
        目标RMS值 0.05 对应约 -23 LUFS 的典型语音/歌唱水平。

        注意：只做增益调整，不改变动态范围。

        Args:
            audio_data: 音频数据
            target_rms: 目标RMS值（默认0.05，经验值）

        Returns:
            归一化后的音频数据
        """
        rms = np.sqrt(np.mean(audio_data ** 2))
        if rms > 1e-10:
            gain = target_rms / rms
            # 限制增益范围避免过度放大噪声或压缩强信号
            gain = np.clip(gain, 0.1, 10.0)
            return audio_data * gain
        return audio_data

    @staticmethod
    def find_vocal_segments(
        f0: np.ndarray,
        hop_length: int = 512,
        sample_rate: int = 22050,
        min_segment_sec: float = 0.5,
        max_gap_sec: float = 1.0
    ) -> list:
        """
        VAD 人声分段 v5.10

        使用基频检测标记有声段，过滤掉前奏/间奏/尾奏(纯器乐段)。
        只保留包含人声基频的连续段，避免纯器乐段被当作"没有音高的演唱"。

        Args:
            f0: 基频序列
            hop_length: 帧移
            sample_rate: 采样率
            min_segment_sec: 最小声段时长(秒)，短于此的视为噪声
            max_gap_sec: 最大间隔(秒)，小于此的间断会被合并

        Returns:
            [(start_frame, end_frame), ...] 人声段列表
        """
        voiced = ~np.isnan(f0) & (f0 > 65) & (f0 < 1047)

        min_frames = int(min_segment_sec * sample_rate / hop_length)
        max_gap_frames = int(max_gap_sec * sample_rate / hop_length)

        segments = []
        start = None
        gap_start = None

        for i, is_voiced in enumerate(voiced):
            if is_voiced:
                if start is None:
                    start = i
                gap_start = None
            else:
                if start is not None:
                    if gap_start is None:
                        gap_start = i
                    if (i - gap_start) >= max_gap_frames:
                        segment_len = gap_start - start
                        if segment_len >= min_frames:
                            segments.append((start, gap_start))
                        start = None
                        gap_start = None

        # 末尾段
        if start is not None:
            segment_len = len(voiced) - start
            if segment_len >= min_frames:
                segments.append((start, len(voiced)))

        return segments

    @staticmethod
    def filter_audio_to_vocal_segments(
        audio_data: np.ndarray,
        vocal_segments: list,
        hop_length: int = 512
    ) -> np.ndarray:
        """
        提取音频中的人声段，拼接为连续数组 v5.10

        用于从包含前奏/间奏的混合音频中只提取人声部分进行特征计算。

        Args:
            audio_data: 完整音频数据
            vocal_segments: 人声段列表 [(start_frame, end_frame), ...]
            hop_length: 帧移

        Returns:
            人声段拼接后的音频数据（若无有效段则返回原音频）
        """
        if not vocal_segments:
            return audio_data

        vocal_parts = []
        for start_frame, end_frame in vocal_segments:
            start_sample = start_frame * hop_length
            end_sample = min(end_frame * hop_length, len(audio_data))
            if end_sample > start_sample:
                vocal_parts.append(audio_data[start_sample:end_sample])

        if not vocal_parts:
            return audio_data

        return np.concatenate(vocal_parts)

    def analyze(self, audio_data: np.ndarray) -> AcousticResult:
        """
        综合声学分析

        Args:
            audio_data: 音频数据

        Returns:
            AcousticResult: 包含HNR、CPP和混合音频检测结果
        """
        result = AcousticResult()

        # 计算HNR和CPP
        result.hnr = self.calculate_hnr(audio_data)
        result.cpp = self.calculate_cpp(audio_data)

        # 检测混合音频
        is_mixed, confidence, low_ratio, flatness = self.detect_mixed_audio(audio_data)
        result.is_mixed_audio = is_mixed
        result.mixed_audio_confidence = confidence
        result.low_freq_ratio = low_ratio
        result.spectral_flatness = flatness

        return result
