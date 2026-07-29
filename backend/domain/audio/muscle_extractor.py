"""
肌肉力量特征提取器 — v7.1.2 对齐版 + v7.4 五维代理增强

复用 FeatureAdapterRegistry.to_muscle() 推导逻辑, ⚠️ HEURISTIC。

v7.4: 新增 MPT/Crest Factor/SPR/F1-F2 area/Alpha Ratio 五维代理指标
"""
from __future__ import annotations
import logging
import numpy as np

from backend.domain.assessment.muscle_scorer import MuscleFeatures
from backend.domain.audio.feature_types import AcousticFeatures
from backend.domain.assessment.breath_scorer import BreathFeatures
from backend.shared.math_utils import safe_clamp as _safe_clamp

logger = logging.getLogger(__name__)


class LibrosaMuscleExtractor:
    """肌肉力量特征提取器 — Level 3 ⚠️ HEURISTIC, 与 FeatureAdapterRegistry 一致"""

    def extract(
        self,
        breath: BreathFeatures,
        acoustic: AcousticFeatures,
        y: np.ndarray | None = None,       # v7.4: 可选原始音频 (用于 MPT/Crest/SPR/F1F2/Alpha)
        sr: int = 22050,                     # v7.4: 采样率
    ) -> MuscleFeatures:
        """提取肌肉力量代理指标 — 与 FeatureAdapterRegistry.to_muscle() 相同公式。"""

        hnr = float(getattr(acoustic, 'hnr', 15.0) or 15.0)
        hpss_ratio = float(getattr(acoustic, 'hpss_harmonic_ratio', 0.30) or 0.30)
        dynamic_range = float(getattr(breath, 'dynamic_range', 15.0) or 15.0)
        # controlled_breathiness 作为 overtone_richness 的代理 (与 adapter 一致)
        controlled_breathiness = float(getattr(breath, 'controlled_breathiness', 50.0) or 50.0)
        # pitch_stability_long: 优先, 回退到 long_note_support (短音频 fallback)
        pitch_stability_long = float(getattr(breath, 'pitch_stability_long', 0.0) or 0.0)
        long_note_support = float(getattr(breath, 'long_note_support', 50.0) or 50.0)
        formant_source = pitch_stability_long if pitch_stability_long > 0 else long_note_support

        # body muscle proxies (与 adapter 一致)
        max_db = -20.0 + dynamic_range * 0.3
        low_freq_ratio = _safe_clamp(hpss_ratio, 0, 1)
        # rms_decay: 来自 BreathStabilityResult.long_note_decay (与 adapter 一致)
        long_note_decay = float(getattr(breath, 'long_note_decay', 1.0) or 1.0)
        rms_decay = _safe_clamp(long_note_decay, 0.1, 5.0)

        # facial muscle proxies (与 adapter 一致)
        singers_formant = _safe_clamp(hnr / 60.0, 0, 0.30)
        formant_cluster = _safe_clamp(formant_source, 0, 100)
        overtone = _safe_clamp(controlled_breathiness, 0, 100)

        # v7.4: 五维代理增强 (从原始音频提取)
        mpt = 0.0
        crest = 0.0
        spr = 1.0
        f1f2_area = 0.0
        alpha_ratio = -15.0

        if y is not None and len(y) > 0:
            try:
                mpt = _extract_mpt(y, sr)
                crest = _extract_crest_factor(y)
                spr = _extract_spr(y, sr)
                f1f2_area = _extract_f1f2_area_approx(y, sr)
                alpha_ratio = _extract_alpha_ratio(y, sr)
            except Exception:
                logger.debug("v7.4 proxy extraction failed, using defaults")

        return MuscleFeatures(
            max_db_level=round(max_db, 2),
            low_freq_energy_ratio=round(low_freq_ratio, 4),
            rms_decay_rate=round(rms_decay, 2),
            singers_formant_energy=round(singers_formant, 4),
            formant_clustering_quality=round(formant_cluster, 2),
            overtone_richness=round(overtone, 2),
            dynamic_range_db=round(dynamic_range, 2),
            mpt_seconds=round(mpt, 2),
            crest_factor=round(crest, 2),
            spr_ratio=round(spr, 4),
            f1f2_area=round(f1f2_area, 2),
            alpha_ratio=round(alpha_ratio, 2),
        )


# ================================================================
# v7.4: 五维代理提取函数
# ================================================================

def _extract_mpt(y: np.ndarray, sr: int,
                 silence_threshold_db: float = -40.0,
                 min_duration_s: float = 0.5) -> float:
    """提取最长发声时间 (Maximum Phonation Time)

    文献: 身体肌肉文献 §2.1
    - <5s: 差 (呼吸肌耐力不足)
    - 5-10s: 一般
    - 10-15s: 良好
    - >15s: 优秀

    方法: 检测连续高于阈值的 RMS 段，取最长段持续时间。
    """
    import librosa
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512).flatten()
    rms_db = 20 * np.log10(rms + 1e-10)

    active = rms_db > silence_threshold_db
    if not np.any(active):
        return 0.0

    edges = np.diff(np.concatenate([[False], active, [False]]).astype(int))
    starts = np.where(edges == 1)[0]
    ends = np.where(edges == -1)[0]
    durations = (ends - starts) * 512 / sr

    valid = durations >= min_duration_s
    if not np.any(valid):
        return 0.0

    return float(np.max(durations[valid]))


def _extract_crest_factor(y: np.ndarray) -> float:
    """提取峰值因子 (Crest Factor = peak / RMS)

    典型人声 10-14 dB, >14 = 强投射, <8 = 弱
    """
    rms = np.sqrt(np.mean(y ** 2))
    if rms < 1e-10:
        return 0.0
    peak = np.max(np.abs(y))
    return float(20 * np.log10(peak / rms))


def _extract_spr(y: np.ndarray, sr: int) -> float:
    """提取歌唱功率比 (SPR = 2-4kHz / 0-2kHz)

    训练歌手 SPR > 1.0, 反映歌手共振峰能量
    """
    import librosa
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)

    low_band = np.sum(S[(freqs >= 0) & (freqs < 2000), :])
    high_band = np.sum(S[(freqs >= 2000) & (freqs < 4000), :])

    if low_band < 1e-10:
        return 1.0
    return float(high_band / low_band)


def _extract_f1f2_area_approx(y: np.ndarray, sr: int) -> float:
    """近似 F1-F2 元音空间面积

    使用频谱峰检测估计 F1 (200-1000Hz) 和 F2 (800-2500Hz)
    的分布范围，计算近似元音空间面积。

    文献: MRI R²=0.96 验证
    """
    import librosa
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)

    f1_mask = (freqs >= 200) & (freqs <= 1000)
    f2_mask = (freqs >= 800) & (freqs <= 2500)

    if not np.any(f1_mask) or not np.any(f2_mask):
        return 0.0

    # 逐帧找峰值，收集 F1/F2 散点
    f1_peaks = []
    f2_peaks = []
    for i in range(S.shape[1]):
        col = S[:, i]
        # F1 peak
        f1_slice = col[f1_mask]
        if len(f1_slice) > 0 and np.max(f1_slice) > 0:
            f1_idx = np.argmax(f1_slice)
            f1_hz = freqs[f1_mask][f1_idx]
            f1_peaks.append(f1_hz)
        # F2 peak
        f2_slice = col[f2_mask]
        if len(f2_slice) > 0 and np.max(f2_slice) > 0:
            f2_idx = np.argmax(f2_slice)
            f2_hz = freqs[f2_mask][f2_idx]
            f2_peaks.append(f2_hz)

    if len(f1_peaks) < 3 or len(f2_peaks) < 3:
        return 0.0

    # F1 范围 × F2 范围 ≈ 元音空间面积
    f1_range = np.percentile(f1_peaks, 90) - np.percentile(f1_peaks, 10)
    f2_range = np.percentile(f2_peaks, 90) - np.percentile(f2_peaks, 10)
    return float(max(0.0, f1_range * f2_range))


def _extract_alpha_ratio(y: np.ndarray, sr: int) -> float:
    """提取 Alpha Ratio (0-1kHz / 1-5kHz 能量比, dB)

    反映发声努力程度和声门源频谱平衡。
    -10~-30dB, 流行 vs 歌剧差异大
    """
    import librosa
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)

    low_energy = np.sum(S[(freqs >= 0) & (freqs < 1000), :])
    high_energy = np.sum(S[(freqs >= 1000) & (freqs < 5000), :])

    if low_energy < 1e-10 or high_energy < 1e-10:
        return -15.0
    return float(20 * np.log10(low_energy / high_energy))
