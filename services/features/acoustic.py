"""
声学指标计算模块

包含：
1. HNR (谐波噪声比) - 反映声带闭合程度
2. CPP (倒谱峰值显著性) - 反映声带闭合质量
"""
import numpy as np
import librosa
import logging

logger = logging.getLogger(__name__)


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
