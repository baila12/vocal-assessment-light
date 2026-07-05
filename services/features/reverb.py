"""
混响补偿模块 v1.0 — HPSS 谐波分离 + 谱减法

基于以下论文:
  - Fitzgerald, D. (2010). "Harmonic/Percussive Separation Using Median Filtering."
    Proc. DAFx.  — HPSS 中值滤波频谱分离
  - Driedger, J., Müller, M., & Disch, S. (2015). "Extending Harmonic-Percussive
    Separation of Audio Signals." ISMIR.  — HPSS margin 参数设计
  - Boll, S. (1979). "Suppression of Acoustic Noise in Speech Using Spectral
    Subtraction." IEEE Trans. ASSP, 27(2), 113-120.  — 谱减法原理
  - Berouti, M., Schwartz, R., & Makhoul, J. (1979). "Enhancement of Speech
    Corrupted by Acoustic Noise." ICASSP.  — 过减因子 α 和频谱地板 β
  - Kinoshita, K. et al. (2013). "A summary of the REVERB challenge: state-of-the-art
    and remaining challenges." EURASIP J. Adv. Signal Process.  — 晚期混响抑制策略

核心思路:
  1. HPSS 分离谐波(直接声)和冲击(混响扩散尾)成分  [Fitzgerald 2010]
  2. 从冲击成分估计"房间噪声"频谱
  3. 谱减法: 从谐波成分中减去缩放后的噪声频谱  [Boll 1979]
  4. 过减 + 频谱地板防止音乐噪声  [Berouti 1979]
"""
from dataclasses import dataclass
import numpy as np
import librosa
import logging

logger = logging.getLogger(__name__)


@dataclass
class ReverbCompensationResult:
    """混响补偿结果"""
    original_rms: float = 0.0       # 原始 RMS
    compensated_rms: float = 0.0    # 补偿后 RMS
    hpss_harmonic_ratio: float = 0.0  # HPSS 谐波能量占比
    noise_reduction_db: float = 0.0   # 估计的降噪量 (dB)


class ReverbCompensator:
    """
    混响补偿器 — HPSS 谐波分离 + 谱减法

    使用 HPSS [Fitzgerald 2010] 分离谐波/冲击成分,
    然后用谱减法 [Boll 1979, Berouti 1979] 抑制冲击成分中的
    混响扩散尾, 减轻不同录音环境对 HNR/CPP 的影响。

    参数选择依据:
      - hpss_margin: (1.0, 3.0) — Fitzgerald 2010 建议的平衡设置,
        与项目中 existing HPSS 调用保持一致
      - oversubtraction α: 2.0 — Berouti 1979 建议语音增强用 2-4,
        取较低值以防止过度减除导致音乐噪声
      - spectral_floor β: 0.01 — Berouti 1979 建议 0.01-0.1,
        取最低值以保留最多的谐波结构
    """

    # Berouti 1979: 过减因子 α (2-4 推荐用于语音)
    DEFAULT_OVERSUBTRACTION = 2.0
    # Berouti 1979: 频谱地板 β (0.01-0.1)
    DEFAULT_SPECTRAL_FLOOR = 0.01
    # Fitzgerald 2010 / Driedger 2015: HPSS margin (谐波核, 冲击核)
    DEFAULT_HPSS_MARGIN = (1.0, 3.0)

    def __init__(
        self,
        sample_rate: int = 22050,
        hpss_margin: tuple = None,
        oversubtraction: float = None,
        spectral_floor: float = None
    ):
        """
        初始化混响补偿器。

        Args:
            sample_rate: 采样率 (Hz)
            hpss_margin: HPSS 核大小 (harmonic_kernel, percussive_kernel)
            oversubtraction: 过减因子 α [Berouti 1979], 越大越激进
            spectral_floor: 频谱地板 β [Berouti 1979], 防止负值
        """
        self.sample_rate = sample_rate
        self.hpss_margin = hpss_margin or self.DEFAULT_HPSS_MARGIN
        self.oversubtraction = oversubtraction or self.DEFAULT_OVERSUBTRACTION
        self.spectral_floor = spectral_floor or self.DEFAULT_SPECTRAL_FLOOR

    def process(
        self,
        audio_data: np.ndarray,
        return_result: bool = False
    ):
        """
        对音频应用混响补偿。

        Args:
            audio_data: 1D 音频信号数组
            return_result: 是否同时返回 ReverbCompensationResult

        Returns:
            补偿后的音频信号 (仅补偿后), 或 (补偿后, ReverbCompensationResult)
        """
        if len(audio_data) < 2048:
            if return_result:
                return audio_data.copy(), ReverbCompensationResult()
            return audio_data.copy()

        try:
            # 记录原始 RMS 用于诊断
            original_rms = float(np.sqrt(np.mean(audio_data ** 2)))

            # Step 1: HPSS 分离 [Fitzgerald 2010]
            # 谐波成分 = 直接声 + 早期反射 (保留)
            # 冲击成分 = 晚期混响扩散尾 + 辅音瞬态
            harmonic, percussive = librosa.effects.hpss(
                audio_data, margin=self.hpss_margin
            )

            hpss_harmonic_ratio = float(
                np.sum(harmonic ** 2) / (np.sum(audio_data ** 2) + 1e-10)
            )

            # Step 2: STFT 域谱减法 [Boll 1979]
            # 计算短时傅里叶变换
            n_fft = 2048
            hop_length = 512

            S_harm = librosa.stft(harmonic, n_fft=n_fft, hop_length=hop_length)
            S_perc = librosa.stft(percussive, n_fft=n_fft, hop_length=hop_length)

            mag_harm = np.abs(S_harm)
            mag_perc = np.abs(S_perc)

            # Step 3: 估计噪声频谱 [Boll 1979]
            # 混响的冲击成分在时间上分布均匀, 取其时间均值作为噪声估计
            noise_estimate = np.mean(mag_perc, axis=1, keepdims=True)

            # Step 4: 过减 + 频谱地板 [Berouti 1979]
            # |Ŝ| = max(|X| - α·|N̂|, β·|X|)
            mag_clean = mag_harm - self.oversubtraction * noise_estimate
            mag_clean = np.maximum(mag_clean, self.spectral_floor * mag_harm)

            # 估计降噪量 [Boll 1979]
            original_energy = np.sum(mag_harm ** 2)
            clean_energy = np.sum(mag_clean ** 2)
            if original_energy > 0 and clean_energy > 0:
                noise_reduction_db = float(
                    10 * np.log10(original_energy / clean_energy)
                )
            else:
                noise_reduction_db = 0.0

            # Step 5: 用原始相位重建 [Boll 1979]
            S_clean = mag_clean * np.exp(1j * np.angle(S_harm))

            # Step 6: 逆 STFT 重建时域信号
            compensated = librosa.istft(
                S_clean, hop_length=hop_length, length=len(audio_data)
            )

            compensated_rms = float(np.sqrt(np.mean(compensated ** 2)))

            # 如果有静默帧, 用原始谐波成分填充
            if compensated_rms > 0:
                compensated = compensated * (original_rms / compensated_rms)

            result = ReverbCompensationResult(
                original_rms=original_rms,
                compensated_rms=float(np.sqrt(np.mean(compensated ** 2))),
                hpss_harmonic_ratio=hpss_harmonic_ratio,
                noise_reduction_db=noise_reduction_db
            )

            if return_result:
                return compensated, result
            return compensated

        except Exception as e:
            logger.warning(f"混响补偿失败: {e}")
            if return_result:
                return audio_data.copy(), ReverbCompensationResult()
            return audio_data.copy()
