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
from .types import AcousticResult
from .types import AcousticResult

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

    def detect_mixed_audio(self, audio_data: np.ndarray) -> tuple:
        """
        检测是否为混合音频（带伴奏）— v5.20 多特征融合版

        采样率自适应: 归一化参数基于 Nyquist 频率调整, 在 16kHz-48kHz
        范围内均有效。v5.20 从原文件直接加载检测片段 (audio_service.py),
        避免 16kHz 降采样导致的频谱特征退化。

        特征:
          1. HPSS 谐波能量比 — 采样率无关, 纯人声 >0.75
          2. 低频能量比 — 伴奏(贝斯/鼓)有更多 <300Hz 能量
          3. 高频能量比 — 伴奏(镲片/泛音)有更多 >5kHz 能量
          4. 频谱平坦度 — 多乐器叠加使频谱趋于平坦

        参考文献:
          - Fitzgerald (2010). "Harmonic/Percussive Separation."
            DAFx. — HPSS 理论基础
          - McFee et al. (2015). "librosa: Audio and Music Signal
            Analysis in Python." SciPy. — 使用的库和特征
          - v5.17 实证: 轻钢琴伴奏男声在旧 0.35 阈值下被漏判

        Args:
            audio_data: 音频数据 (建议使用原始采样率)

        Returns:
            (is_mixed, confidence, low_freq_ratio, spectral_flatness)
        """
        try:
            # 计算频谱
            stft = np.abs(librosa.stft(audio_data))
            spectrum = np.mean(stft, axis=1)
            freqs = librosa.fft_frequencies(sr=self.sample_rate)
            total_energy = np.sum(spectrum ** 2) + 1e-10

            # ============================================================
            # 特征1: HPSS 谐波能量比 (主特征, 16kHz下最可靠)
            #
            # 原理 [Fitzgerald 2010]: HPSS 用中值滤波将音频分为
            #   - 谐波成分 (水平方向连续) = 人声 + 乐器持续音
            #   - 冲击成分 (垂直方向连续) = 辅音 + 乐器瞬态 + 混响
            # 纯人声: 谐波比 > 0.75 (大部分能量在谐波成分)
            # 混合音频: 谐波比降低 (伴奏能量部分被分到冲击成分)
            # ============================================================
            harmonic, percussive = librosa.effects.hpss(
                audio_data, margin=(1.0, 3.0)
            )
            hpss_harmonic_ratio = float(
                np.sum(harmonic ** 2) / (np.sum(audio_data ** 2) + 1e-10)
            )
            # 归一化: 0.90以上→0, 0.50以下→1
            hpss_score = np.clip((0.90 - hpss_harmonic_ratio) / 0.40, 0.0, 1.0)

            # ============================================================
            # 特征2: 高频能量占比 (>5kHz)
            #
            # 纯人声在 >5kHz 能量极少 (<2%), 伴奏乐器(镲片/弦乐泛音)
            # 在此频段有明显能量
            # ============================================================
            high_band_mask = freqs > 5000
            high_energy = np.sum(spectrum[high_band_mask] ** 2)
            high_freq_ratio = high_energy / total_energy
            # 归一化: >5%→1 (强烈有伴奏), <1%→0 (纯人声)
            high_freq_score = np.clip((high_freq_ratio - 0.01) / 0.04, 0.0, 1.0)

            # ============================================================
            # 特征3: 频谱平坦度
            # ============================================================
            spectral_flatness = librosa.feature.spectral_flatness(
                S=stft, hop_length=self.hop_length
            )
            mean_flatness = float(np.mean(spectral_flatness))
            flatness_score = np.clip(mean_flatness / 0.30, 0.0, 1.0)

            # ============================================================
            # 特征4: 低频能量比
            #
            # 归一化采样率自适应: Nyquist 越高, 300Hz 以下占比越低。
            # 在 44.1kHz 下人声典型 5-20%, 伴奏 >25%
            # 在 16kHz 下人声典型 20-50%, 区分力有限
            # ============================================================
            low_freq_mask = freqs < 300
            low_energy = np.sum(spectrum[low_freq_mask] ** 2)
            low_freq_ratio = low_energy / total_energy
            # 采样率自适应归一化
            nyquist = self.sample_rate / 2
            low_freq_norm = 0.12 + (300.0 / nyquist) * 3.0
            low_freq_score = np.clip(low_freq_ratio / low_freq_norm, 0.0, 1.0)

            # ============================================================
            # v5.20: 四特征加权投票 (采样率自适应)
            #
            # HPSS 谐波比 — 最可靠, 采样率无关
            # 高频能量 — 有效但需采样率自适应 >5kHz 占比
            # 低频能量 — 在 44.1kHz 下有效, 16kHz 下自动降权
            # 频谱平坦度 — 辅助
            # ============================================================
            mixed_score = (
                0.40 * hpss_score +
                0.25 * high_freq_score +
                0.20 * low_freq_score +
                0.15 * flatness_score
            )

            # 决策
            if mixed_score > 0.45:
                is_mixed = True
                confidence = 0.65 + (mixed_score - 0.45) * 0.7
            elif mixed_score > 0.28:
                is_mixed = True
                confidence = 0.45 + (mixed_score - 0.28) * 1.0
            elif mixed_score > 0.18:
                # 灰区: 保守处理, 触发分离
                is_mixed = True
                confidence = 0.25 + (mixed_score - 0.18) * 2.0
            else:
                is_mixed = False
                confidence = 1.0 - mixed_score * 4.0

            confidence = float(max(0.0, min(1.0, confidence)))

            logger.debug(
                f"混合音频检测 v5.20: is_mixed={is_mixed}, confidence={confidence:.2f}, "
                f"mixed_score={mixed_score:.3f} (sr={self.sample_rate}), "
                f"hpss={hpss_harmonic_ratio:.3f}({hpss_score:.2f}), "
                f"high={high_freq_ratio:.4f}({high_freq_score:.2f}), "
                f"low={low_freq_ratio:.3f}({low_freq_score:.2f}), "
                f"flat={mean_flatness:.4f}({flatness_score:.2f})"
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
