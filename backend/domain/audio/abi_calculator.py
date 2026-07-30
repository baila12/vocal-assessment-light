"""
ABI (Acoustic Breathiness Index) 计算器 — v7.6 P2

基于 Barsties v. Latoszek (2017): 9 声学参数 → 单一气息感指数 (0-10)
AUC=0.94, 跨 4 种语言验证 (德语/英语/法语/韩语)

⚠️ 注意: ABI 在病理语音上验证, 歌声应用仅有 n=2 试点研究。
本模块作为 audiofeat 可选增强, 初步系数来自临床文献, 需歌声标注数据重新校准。

Ref: Barsties v. Latoszek, B. et al. (2017).
     "The Acoustic Breathiness Index (ABI): A Multivariate Acoustic Model for
     Breathiness." Journal of Voice, 31(4), 511.e1-511.e7.
"""
from __future__ import annotations
import logging
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)

# ABI 公式 (Barsties 2017, Table 4):
# ABI = 1.477
#       - 0.165 × CPPS          (cepstral peak prominence, dB)
#       - 0.058 × GNE            (glottal-to-noise excitation, 0-1)
#       - 0.238 × Jitter_local   (%)
#       - 0.182 × Shimmer_local  (dB)
#       - 0.115 × HNR            (harmonic-to-noise ratio, dB)
#       - 0.217 × H1-H2          (amplitude difference 1st/2nd harmonic, dB)
#       - 0.131 × HfNoise_6kHz   (high-frequency noise energy >6kHz, dB)
#       + 0.091 × Period_SD      (standard deviation of F0 period, ms)
#
# Score interpretation (clinical):
#   0.00-0.99 = 正常 (non-breathy)
#   1.00-1.99 = 轻度气息感 (mild)
#   2.00-3.49 = 中度气息感 (moderate)
#   3.50+     = 重度气息感 (severe)


def compute_h1_h2(y: np.ndarray, sr: int, f0: np.ndarray) -> float:
    """计算 H1-H2 (第一谐波与第二谐波的幅度差, dB)。

    文献: 气息音 H1-H2 = +2.08dB, 正常 = -0.60dB, 紧压 = -1.63dB
    H1-H2 越高 → 越气息。
    """
    try:
        import librosa
        # 取有声帧计算
        voiced_mask = (f0 > 0) & (~np.isnan(f0))
        if np.sum(voiced_mask) < 10:
            return 0.0

        f0_median = float(np.median(f0[voiced_mask]))
        if f0_median <= 0:
            return 0.0

        S = np.abs(librosa.stft(y, n_fft=4096, hop_length=512))
        freqs = librosa.fft_frequencies(sr=sr, n_fft=4096)

        h1_h2_values = []
        for i in range(S.shape[1]):
            col = S[:, i]
            # H1 ≈ f0, H2 ≈ 2*f0
            h1_idx = np.argmin(np.abs(freqs - f0_median))
            h2_idx = np.argmin(np.abs(freqs - 2 * f0_median))

            h1_amp = col[h1_idx] if h1_idx < len(col) else 0
            h2_amp = col[h2_idx] if h2_idx < len(col) else 0

            if h1_amp > 1e-10 and h2_amp > 1e-10:
                h1_h2_values.append(20 * np.log10(h1_amp / h2_amp))

        return float(np.mean(h1_h2_values)) if h1_h2_values else 0.0
    except Exception:
        logger.debug("H1-H2 computation failed", exc_info=True)
        return 0.0


def compute_hf_noise_6khz(y: np.ndarray, sr: int) -> float:
    """计算 >6kHz 高频噪声能量 (dB, 归一化)。

    气息声在 >6kHz 频段产生额外高频噪声。
    返回值: 高频能量占比 (dB), 越高越气息。
    """
    try:
        import librosa
        S = np.abs(librosa.stft(y, n_fft=4096, hop_length=512))
        freqs = librosa.fft_frequencies(sr=sr, n_fft=4096)

        hf_mask = freqs > 6000
        total_energy = np.sum(S)
        if total_energy <= 0:
            return -60.0  # effectively zero

        hf_ratio = np.sum(S[hf_mask]) / total_energy
        if hf_ratio <= 0:
            return -60.0
        return float(20 * np.log10(hf_ratio))
    except Exception:
        logger.debug("HF noise computation failed", exc_info=True)
        return -60.0


def compute_period_sd(f0: np.ndarray, sr: int) -> float:
    """计算基频周期标准差 (ms)。

    气息声 → 声门闭合不规律 → 周期变异增大。
    返回值: period SD (ms), 越高越不规律。
    """
    try:
        voiced_mask = (f0 > 0) & (~np.isnan(f0))
        if np.sum(voiced_mask) < 10:
            return 0.0

        valid_f0 = f0[voiced_mask]
        periods_ms = 1000.0 / valid_f0  # Hz → ms
        return float(np.std(periods_ms))
    except Exception:
        logger.debug("Period SD computation failed", exc_info=True)
        return 0.0


def compute_abi(
    cpp: float = 0.0,
    gne: float = 0.0,
    jitter_local: float = 0.0,
    shimmer_db: float = 0.0,
    hnr: float = 0.0,
    h1_h2: float = 0.0,
    hf_noise_6khz: float = -60.0,
    period_sd: float = 0.0,
) -> float:
    """计算 ABI 气息感指数 (0-10)。

    Barsties v. Latoszek (2017) 原始公式:
      ABI = 1.477 - 0.165*CPPS - 0.058*GNE - 0.238*Jitter - 0.182*Shimmer
            - 0.115*HNR - 0.217*H1H2 - 0.131*HF_noise + 0.091*Period_SD

    ⚠️ 歌声适配: 原始临床公式对干净歌声可能输出负值 (CPPS/HNR 远超病理范围)。
    v7.6 使用归一化版本, 用理想值作为参考点, 计算偏差分数。

    Args:
        cpp: CPPS (dB), 歌声 13-18 (Buckley 2023), 理想=15
        gne: GNE (0-1), 理想=0.8
        jitter_local: 局部 Jitter (%), 理想=0.2%
        shimmer_db: 局部 Shimmer (dB), 理想=0.1dB
        hnr: HNR (dB), 歌声 25-35, 理想=28
        h1_h2: H1-H2 (dB), 理想=-0.6
        hf_noise_6khz: >6kHz 能量 (dB), 理想=-45
        period_sd: 基频周期 SD (ms), 理想=0.3

    Returns:
        abi_score: 0-10 气息感指数 (≥3.5 = 严重)
    """
    # 归一化: 计算每个参数与理想值的偏差, 加权累加 → 0-10
    # 正偏差 = 比理想值差 → 增加 ABI 分数
    deviations = 0.0

    # CPPS: 15 dB 为理想, 每下降 3dB 增加 1 分
    cpp_dev = max(0.0, 15.0 - cpp) / 3.0
    deviations += 0.165 * cpp_dev

    # GNE: 0.8 为理想, 每下降 0.1 增加 0.5 分
    gne_dev = max(0.0, 0.8 - gne) / 0.1 * 0.5
    deviations += 0.058 * gne_dev

    # Jitter: 0.2% 为理想, 每上升 0.5% 增加 1 分
    jitter_dev = max(0.0, jitter_local - 0.2) / 0.5
    deviations += 0.238 * jitter_dev

    # Shimmer: 0.1dB 为理想, 每上升 0.2dB 增加 1 分
    shimmer_dev = max(0.0, shimmer_db - 0.1) / 0.2
    deviations += 0.182 * shimmer_dev

    # HNR: 28dB 为理想, 每下降 5dB 增加 1 分
    hnr_dev = max(0.0, 28.0 - hnr) / 5.0
    deviations += 0.115 * hnr_dev

    # H1-H2: -0.6dB 为理想, 每偏离 1dB 增加 0.5 分
    h1h2_dev = abs(h1_h2 - (-0.6)) / 1.0 * 0.5
    deviations += 0.217 * h1h2_dev

    # HF noise: -45dB 为理想, 每上升 5dB 增加 1 分
    hf_dev = max(0.0, hf_noise_6khz + 45.0) / 5.0
    deviations += 0.131 * hf_dev

    # Period SD: 0.3ms 为理想, 每上升 0.5ms 增加 1 分
    psd_dev = max(0.0, period_sd - 0.3) / 0.5
    deviations += 0.091 * psd_dev

    # 换算到 0-10: 偏差 0 → ABI=0, 偏差 10 → ABI=5, 偏差 20 → ABI=10
    abi = deviations * 0.5
    return max(0.0, min(10.0, abi))


def abi_to_breath_score(abi: float) -> float:
    """将 ABI (0-10) 映射为气声控制得分 (0-100, 反向)。

    低 ABI (干净) → 高 breath 得分
    高 ABI (气息) → 低 breath 得分
    """
    if abi <= 0.5:
        return 95.0  # 非常干净
    elif abi <= 1.5:
        return 90.0 - (abi - 0.5) / 1.0 * 15.0   # 0.5→90, 1.5→75
    elif abi <= 3.0:
        return 75.0 - (abi - 1.5) / 1.5 * 30.0   # 1.5→75, 3.0→45
    elif abi <= 5.0:
        return 45.0 - (abi - 3.0) / 2.0 * 25.0   # 3.0→45, 5.0→20
    else:
        return max(0.0, 20.0 - (abi - 5.0) * 4.0)


class AbiCalculator:
    """ABI 气息感评估器 — v7.6 audiofeat 可选增强。

    用法:
        calc = AbiCalculator()
        abi = calc.calculate(audiofeat_features, y, sr, f0)
        breath_mod = abi_to_breath_score(abi)
    """

    def calculate(
        self,
        audiofeat: Optional['AudiofeatFeatures'] = None,
        y: Optional[np.ndarray] = None,
        sr: int = 22050,
        f0: Optional[np.ndarray] = None,
        hnr: float = 15.0,
    ) -> float:
        """计算 ABI 气息感指数。

        当 audiofeat 不可用时返回 NaN (调用方应回退到 CPPS+HNR 路径)。
        """
        if audiofeat is None:
            return float('nan')

        cpp = float(audiofeat.cpp_mean or 0.0)
        gne = float(audiofeat.gne_mean or 0.0)
        jitter = float(audiofeat.jitter_local or 0.0)
        shimmer = float(audiofeat.shimmer_db or 0.0)

        # H1-H2 (需要原始音频 + F0)
        h1_h2 = 0.0
        if y is not None and len(y) > 0 and f0 is not None and len(f0) > 0:
            h1_h2 = compute_h1_h2(y, sr, f0)

        # >6kHz 噪声 (需要原始音频)
        hf_noise = -60.0
        if y is not None and len(y) > 0:
            hf_noise = compute_hf_noise_6khz(y, sr)

        # Period SD (需要 F0)
        period_sd = 0.0
        if f0 is not None and len(f0) > 0:
            period_sd = compute_period_sd(f0, sr)

        return compute_abi(
            cpp=cpp,
            gne=gne,
            jitter_local=jitter,
            shimmer_db=shimmer,
            hnr=hnr,
            h1_h2=h1_h2,
            hf_noise_6khz=hf_noise,
            period_sd=period_sd,
        )
