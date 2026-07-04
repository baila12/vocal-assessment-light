"""
多频带 HNR (谐波噪声比) 分析模块 v5.18

移植自 VoiceLab (MeasureHNRVoiceSauceNode.py) — 实现 de Krom 1993 的
倒谱域谐波/噪声分离方法。

与 VoiceLab (Yen-Liang Shue, UCLA SPAPL 2009) 的对齐:
- de Krom 1993 倒谱法: FFT → log10 → IFFT → 倒谱域分离谐波和噪声
- 4 个分析频带: 0-500, 0-1500, 0-2500, 0-3500 Hz
- HNR = 20 * (mean_harmonic - mean_noise) per band
- 多频带 CV 作为稳定性指标

参考:
  de Krom, G. (1993). "A cepstrum-based technique for determining a
  harmonics-to-noise ratio in speech signals." J Speech Hear Res.
  VoiceLab: https://github.com/Voice-Lab/VoiceLab
"""
from dataclasses import dataclass
import numpy as np
import librosa
import logging

logger = logging.getLogger(__name__)


@dataclass
class HNRMultiscaleResult:
    """多频带 HNR 分析结果"""
    hnr_short: float = 0.0    # 0-500Hz 频带 HNR (低频)
    hnr_medium: float = 0.0   # 0-1500Hz 频带 HNR (中频, 语音主要能量)
    hnr_long: float = 0.0     # 0-3500Hz 频带 HNR (全频带)
    hnr_stability: float = 0.0  # 多频带变异系数, 越低越稳定


class MultiScaleHNR:
    """
    多频带 HNR 分析器 — de Krom 1993 倒谱分离法

    使用倒谱域谐波/噪声分离:
    1. 提取基频周期段 (5 个周期)
    2. Hamming 窗 → FFT → log10 → IFFT → 实倒谱
    3. 在倒谱中定位谐波峰值 (N0 的整数倍)
    4. 置零谐波区域 → 重建噪声倒谱 → FFT → 噪声频谱
    5. HNR[k] = 20 * (mean(harmonic[0:k]) - mean(noise[0:k]))
    6. 4 频带: 500, 1500, 2500, 3500 Hz
    """

    # 分析频带 (Hz) — 对齐 VoiceLab
    FREQ_BANDS = [500, 1500, 2500, 3500]

    # 基频周期数
    N_PERIODS = 5

    def __init__(self, sample_rate: int = 22050):
        """
        初始化 HNR 分析器

        Args:
            sample_rate: 音频采样率 (Hz)
        """
        self.sample_rate = sample_rate

    def analyze(
        self,
        audio_data: np.ndarray,
        f0: np.ndarray = None,
        frame_shift_ms: float = 1.0
    ) -> HNRMultiscaleResult:
        """
        执行多频带 HNR 分析 — de Krom 1993 方法

        Args:
            audio_data: 1D 音频信号
            f0: 基频序列 (可选, 未提供则用 librosa.yin 提取)
            frame_shift_ms: 帧移 (ms), VoiceLab 默认 1ms

        Returns:
            HNRMultiscaleResult: hnr_short(0-500Hz), hnr_medium(0-1500Hz),
                                 hnr_long(0-3500Hz), hnr_stability(CV)
        """
        if len(audio_data) == 0:
            return HNRMultiscaleResult()

        try:
            signal = np.asarray(audio_data, dtype=np.float64)

            # 提取基频 (如果未提供)
            if f0 is None:
                f0 = librosa.yin(
                    signal,
                    fmin=65.0,
                    fmax=600.0,
                    sr=self.sample_rate,
                    hop_length=int(self.sample_rate * frame_shift_ms / 1000)
                )

            if len(f0) == 0 or np.all(np.isnan(f0)):
                return HNRMultiscaleResult()

            # 对每个有声帧计算 HNR
            sampleshift = self.sample_rate / (1000.0 / frame_shift_ms)
            n_periods = self.N_PERIODS

            all_hnrs = []  # [[hnr_500, hnr_1500, hnr_2500, hnr_3500], ...]

            for k in range(len(f0)):
                f0_curr = f0[k]
                if np.isnan(f0_curr) or f0_curr <= 0:
                    continue

                # 信号采样位置
                ks = int(np.round(k * sampleshift))
                if ks <= 0 or ks >= len(signal):
                    continue

                # 周期长度 (samples)
                N0_curr = self.sample_rate / f0_curr

                # 提取 5 个周期长度的信号段
                ystart = int(round(ks - n_periods / 2 * N0_curr))
                yend = int(round(ks + n_periods / 2 * N0_curr)) - 1

                if ystart < 0 or yend >= len(signal):
                    continue

                # 确保偶数长度 (FFT 友好)
                if (yend - ystart + 1) % 2 == 1:
                    yend -= 1
                if yend <= ystart:
                    continue

                yseg = signal[ystart:yend + 1]

                # de Krom 1993 HNR 计算
                hnr_bands = self._de_krom_hnr(yseg, f0_curr)
                if hnr_bands is not None:
                    all_hnrs.append(hnr_bands)

            if not all_hnrs:
                return HNRMultiscaleResult()

            # 各频带取中位数 (抗野值)
            hnrs = np.array(all_hnrs)
            median_hnrs = np.median(hnrs, axis=0)  # [4]

            hnr_500, hnr_1500, hnr_2500, hnr_3500 = median_hnrs

            # 稳定性: 4 频带 CV
            mean_hnr = np.mean(median_hnrs)
            if mean_hnr != 0:
                stability = float(np.std(median_hnrs) / abs(mean_hnr))
            else:
                stability = 1.0

            return HNRMultiscaleResult(
                hnr_short=float(hnr_500),
                hnr_medium=float(hnr_1500),
                hnr_long=float(hnr_3500),
                hnr_stability=float(stability)
            )

        except Exception as e:
            logger.warning(f"HNR 分析失败: {e}")
            return HNRMultiscaleResult()

    def _de_krom_hnr(self, yseg: np.ndarray, f0: float):
        """
        de Krom 1993 倒谱域谐波/噪声分离法 — 对齐 VoiceLab getHNR()

        Args:
            yseg: 信号段 (~5 周期长度)
            f0: 基频 (Hz)

        Returns:
            list: [hnr_500, hnr_1500, hnr_2500, hnr_3500] or None
        """
        try:
            n_bins = len(yseg)
            if n_bins < 4:
                return None

            # 基频对应的采样点数
            N0 = round(self.sample_rate / f0)

            # Step 1: 倒谱计算
            aY, ay = self._compute_cepstrum(yseg, n_bins)

            # Step 2: 谐波置零
            ay_noise = self._remove_harmonics_from_cepstrum(ay, N0, n_bins)

            # Step 3: 对称化噪声倒谱 (镜像)
            ay_noise = self._mirror_cepstrum(ay_noise, n_bins)

            # Step 4: 重建噪声频谱
            Nap = np.real(np.fft.fft(ay_noise))
            N_spec = Nap.copy()

            # Step 5: 谐波频谱 = 总频谱 - 噪声频谱
            Ha = aY - Nap

            # Step 6: 阶梯校正
            N_spec = self._apply_step_correction(Ha, N_spec, f0, n_bins)

            # Step 7: 谐波频谱
            H_spec = aY - N_spec

            # Step 8: 计算各频带 HNR
            return self._compute_band_hnrs(H_spec, N_spec, n_bins)

        except Exception as e:
            logger.debug(f"de Krom HNR 计算失败: {e}")
            return None

    def _compute_cepstrum(self, yseg: np.ndarray, n_bins: int):
        """计算倒谱: Hamming窗 → FFT → log10 → IFFT → 实倒谱"""
        windowed = yseg * np.hamming(n_bins)
        fft_y = np.fft.fft(windowed, n_bins)
        aY = np.log10(np.abs(fft_y) + 1e-12)
        ay = np.fft.ifft(aY).real
        return aY, ay

    def _find_harmonic_boundary(self, ay: np.ndarray, peak_idx: int):
        """
        从倒谱谐波峰向外扩展，找到谐波分量的左右边界。

        从峰值向两侧移动，直到振幅不再递减（到达谷底）。
        返回包含整个谐波"山峰"的区间 [l_idx, r_idx]。
        """
        n_bins = len(ay)
        abs_ay = np.abs(ay)

        # 左边界: 从峰值向左走，直到下一个点比当前点大（进入谷底上升）
        l_idx = peak_idx
        while l_idx > 1 and abs_ay[l_idx - 1] < abs_ay[l_idx]:
            l_idx -= 1

        # 右边界: 从峰值向右走，直到下一个点比当前点大（进入谷底上升）
        r_idx = peak_idx
        while r_idx < n_bins - 2 and abs_ay[r_idx + 1] < abs_ay[r_idx]:
            r_idx += 1

        return l_idx, r_idx

    def _remove_harmonics_from_cepstrum(
        self, ay: np.ndarray, N0: int, n_bins: int
    ) -> np.ndarray:
        """在倒谱中定位并置零所有谐波峰区域"""
        N0_delta = round(N0 * 0.1)
        max_harmonic = int(np.floor(n_bins / 2 / N0))
        ay_noise = ay.copy()

        for h in range(1, max_harmonic + 1):
            center = h * N0
            lo = max(0, int(center - N0_delta))
            hi = min(n_bins, int(center + N0_delta))
            if hi <= lo:
                continue

            # 在搜索窗口中找到实际峰值
            region = np.abs(ay[lo:hi])
            peak_rel = np.argmax(region)
            peak_idx = lo + peak_rel

            # 从峰值向外扩展到谷底
            l_idx, r_idx = self._find_harmonic_boundary(ay, peak_idx)

            # 置零整个谐波区域
            ay_noise[l_idx:r_idx + 1] = 0

        return ay_noise

    def _mirror_cepstrum(self, ay_noise: np.ndarray, n_bins: int) -> np.ndarray:
        """
        镜像对称化倒谱，使噪声倒谱满足实数信号的对称性。

        对于实数信号，倒谱满足 c[N-k] = c[k] (k=1..N-1)。
        半边索引从 mid-2 开始镜像（排除 DC 分量 c[0] 和 c[mid-1]）。
        """
        mid = n_bins // 2 + 1
        # 源起始为 mid-2: c[1]..c[mid-2] 镜像到 c[mid]..c[N-1]
        # c[N-k] = c[k] → 目标 c[mid] 应对应源 c[mid-2]
        src_len = n_bins - mid
        if src_len > 0:
            ay_noise[mid:] = ay_noise[mid - 2:mid - 2 - src_len:-1]
        return ay_noise

    def _apply_step_correction(
        self, Ha: np.ndarray, N_spec: np.ndarray, f0: float, n_bins: int
    ) -> np.ndarray:
        """阶梯校正: 在谐波峰之间填充噪声谷"""
        Hdelta = f0 / self.sample_rate * n_bins
        corrected = N_spec.copy()

        for f_idx in range(int(Hdelta), int(n_bins // 2), int(Hdelta)):
            fstart = int(np.ceil(f_idx - Hdelta))
            fend = int(min(f_idx, n_bins // 2))
            if fend > fstart:
                valley = abs(min(Ha[fstart:fend]))
                corrected[fstart:fend] = corrected[fstart:fend] - valley

        return corrected

    def _compute_band_hnrs(
        self, H_spec: np.ndarray, N_spec: np.ndarray, n_bins: int
    ) -> list:
        """计算各频带 HNR: 20 * (mean_harmonic - mean_noise)"""
        hnrs = []
        for freq in self.FREQ_BANDS:
            band_bins = int(freq / self.sample_rate * n_bins)
            band_bins = min(band_bins, n_bins // 2)
            if band_bins > 1:
                h_energy = np.mean(H_spec[1:band_bins])
                n_energy = np.mean(N_spec[1:band_bins])
                hnr = 20.0 * (h_energy - n_energy)
                hnr = float(np.clip(hnr, -20.0, 60.0))
                hnrs.append(hnr)
            else:
                hnrs.append(0.0)
        return hnrs
