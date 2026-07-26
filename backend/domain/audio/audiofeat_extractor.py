"""
Audiofeat 增强特征提取器 — v7.2.0

利用 audiofeat 1.1.1 提取 20+ 声学特征, 增强:
- 气息维度: CPPS, GNE, HNR_praat (替换 librosa HNR/CPP)
- 技术维度: Jitter, Shimmer, Closed Quotient
- 肌肉维度: Soft Phonation Index, Vocal Fry Index
- 音色维度: Spectral Roughness, Sharpness, Harmonic Richness

设计原则:
- 零副作用: 纯函数, 无 I/O
- 宽松回退: 异常时返回默认值, 不崩溃
- 不可变输出: AudiofeatFeatures frozen dataclass
- Flag 门控: enable_audiofeat 控制是否启用
"""
from __future__ import annotations
from dataclasses import dataclass
import logging
import numpy as np

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AudiofeatFeatures:
    """Audiofeat 增强特征 — 不可变数据类 (v7.2.0)

    所有字段均有合理默认值。音频极短或静音时使用默认值,
    不抛异常。
    """

    # ---- Voice Quality (气息 + 技术) ----
    cpp_mean: float = 0.0              # CPPS 均值 (dB), 越高越清晰
    cpp_std: float = 0.0               # CPPS 标准差
    hnr_mean: float = 0.0              # HNR_praat 均值 (dB), 越高越干净
    gne_mean: float = 0.0              # GNE 均值 (0-1), 越高声门激励越规律
    gne_max: float = 0.0               # GNE 最大值

    # ---- Perturbation (技术) ----
    jitter_local: float = 0.0          # 局部 Jitter (%), 越低越稳定
    jitter_ppq5: float = 0.0           # PPQ5 Jitter (%)
    shimmer_db: float = 0.0            # 局部 Shimmer (dB), 越低越稳定

    # ---- Glottal Flow (技术) ----
    closed_quotient: float = 0.0       # 声门闭合商 (0-1), 需要 F0 period

    # ---- Phonation Mode (肌肉) ----
    soft_phonation_mean: float = 0.0   # 软发声指数均值
    vocal_fry_ratio: float = 0.0       # 气泡音占比

    # ---- Spectral (音色 + 肌肉) ----
    spectral_centroid_mean: float = 0.0     # 频谱质心 (Hz), 越高越亮
    spectral_flatness_mean: float = 0.0     # 频谱平坦度 (0-1)
    spectral_crest: float = 0.0             # 频谱峰值因子
    spectral_entropy: float = 0.0           # 频谱熵
    spectral_roughness: float = 0.0         # 频谱粗糙度
    harmonic_richness: float = 0.0          # 谐波丰富度
    inharmonicity: float = 0.0              # 不和谐度
    hammarberg_index: float = 0.0           # Hammarberg 指数 (低频/高频能量比)
    spectral_slope: float = 0.0             # 频谱斜率

    # ---- Nasality (音色) ----
    nasality: float = 0.0              # 鼻音指数

    # ---- Energy (肌肉) ----
    rms_energy: float = 0.0            # RMS 能量


class AudiofeatExtractor:
    """
    Audiofeat 增强特征提取器 — v7.2.0

    使用 audiofeat 1.1.1 提取 20+ 声学特征。
    输入: PyTorch tensor (波形)
    输出: AudiofeatFeatures frozen dataclass

    实现为 Protocol AudioFeatureExtractor 的实现。
    """

    def __init__(self):
        self._available = False
        try:
            import audiofeat
            self._audiofeat = audiofeat
            self._available = True
        except ImportError:
            logger.warning("audiofeat not installed — AudiofeatExtractor disabled")

    @property
    def available(self) -> bool:
        return self._available

    # ================================================================
    # 公共 API
    # ================================================================

    def extract(self, waveform, sample_rate: int) -> AudiofeatFeatures:
        """
        从波形提取所有 audiofeat 特征。

        Args:
            waveform: PyTorch tensor (1D float32) 或 numpy array
            sample_rate: 采样率 (Hz)

        Returns:
            AudiofeatFeatures frozen dataclass
        """
        if not self._available:
            return AudiofeatFeatures()

        # 转换为 torch tensor (float32)
        if isinstance(waveform, np.ndarray):
            import torch
            waveform = torch.from_numpy(waveform.astype(np.float32))
        else:
            waveform = waveform.float()

        # 边缘情况: 空或极短
        if waveform.numel() == 0 or waveform.numel() < sample_rate * 0.02:
            return AudiofeatFeatures()

        try:
            return self._extract_impl(waveform, sample_rate)
        except Exception:
            logger.exception("AudiofeatExtractor.extract() failed")
            return AudiofeatFeatures()

    def _extract_impl(self, y, sr: int) -> AudiofeatFeatures:
        """实际提取逻辑 (y: torch.Tensor, float32)"""
        af = self._audiofeat

        # ---- Voice Quality ----
        cpp = self._safe_1d(af.voice.cepstral_peak_prominence, y, sr)
        hnr = self._safe_scalar(af.voice.hnr_praat, y, sr)
        gne = self._safe_1d(af.voice.glottal_to_noise_excitation, y)

        # ---- Perturbation ----
        jitter = self._clamp_jitter(self._safe_scalar(af.voice.jitter_local, y))
        jitter_ppq5 = self._clamp_jitter(self._safe_scalar(af.voice.jitter_ppq5, y))
        shimmer = self._safe_scalar(af.voice.shimmer_local_db, y)

        # ---- Phonation ----
        soft_phon = self._safe_1d(af.voice.soft_phonation_index, y, sr)
        vocal_fry = self._safe_scalar(af.voice.vocal_fry_index, y)

        # ---- Spectral ----
        centroid = self._safe_1d(af.spectral.spectral_centroid, y, sr)
        flatness = self._safe_1d(af.spectral.spectral_flatness, y, sr)
        crest = self._safe_scalar(af.spectral.spectral_crest_factor, y, sr)
        entropy = self._safe_scalar(af.spectral.spectral_entropy, y, sr)
        roughness = self._safe_scalar(af.spectral.spectral_roughness, y, sr)
        harm_rich = self._safe_scalar(af.spectral.harmonic_richness_factor, y)
        inharm = self._safe_scalar(af.spectral.inharmonicity_index, y, sr)
        hammarberg = self._safe_scalar(af.voice.hammarberg_index, y, sr)
        slope = self._safe_scalar(af.spectral.spectral_slope, y, sr)
        tonality = self._safe_scalar(af.spectral.spectral_tonality, y, sr)

        # ---- Nasality ----
        nasality = self._safe_scalar(af.voice.nasality_index, y, fs=sr)

        # ---- Energy ----
        rms_val = self._safe_scalar(af.rms, y, 2048, 512)

        # ---- Closed Quotient (需要 F0) ----
        cq = self._compute_closed_quotient(y, sr)

        return AudiofeatFeatures(
            cpp_mean=float(np.nanmean(cpp)) if len(cpp) > 0 else 0.0,
            cpp_std=float(np.nanstd(cpp)) if len(cpp) > 0 else 0.0,
            hnr_mean=float(hnr),
            gne_mean=float(np.nanmean(gne)) if len(gne) > 0 else 0.0,
            gne_max=float(np.nanmax(gne)) if len(gne) > 0 else 0.0,
            jitter_local=float(jitter) if not np.isnan(jitter) else 0.0,
            jitter_ppq5=float(jitter_ppq5) if not np.isnan(jitter_ppq5) else 0.0,
            shimmer_db=float(shimmer) if not np.isnan(shimmer) else 0.0,
            closed_quotient=float(cq) if not np.isnan(cq) else 0.0,
            soft_phonation_mean=float(np.nanmean(soft_phon)) if len(soft_phon) > 0 else 0.0,
            vocal_fry_ratio=float(vocal_fry) if not np.isnan(vocal_fry) else 0.0,
            spectral_centroid_mean=float(np.nanmean(centroid)) if len(centroid) > 0 else 0.0,
            spectral_flatness_mean=float(np.nanmean(flatness)) if len(flatness) > 0 else 0.0,
            spectral_crest=float(crest),
            spectral_entropy=float(entropy),
            spectral_roughness=float(roughness),
            harmonic_richness=float(harm_rich) if not np.isnan(harm_rich) else 0.0,
            inharmonicity=float(inharm),
            hammarberg_index=float(hammarberg) if not np.isnan(hammarberg) else 0.0,
            spectral_slope=float(slope),
            nasality=float(nasality) if not np.isnan(nasality) else 0.0,
            rms_energy=float(rms_val),
        )

    # ================================================================
    # Helpers
    # ================================================================

    @staticmethod
    def _safe_scalar(fn, *args, **kwargs) -> float:
        """安全调用 audiofeat 函数, 返回标量 (NaN/Inf → 0.0)"""
        try:
            result = fn(*args, **kwargs)
            if hasattr(result, 'numel'):
                if result.numel() == 0:
                    return 0.0
                if result.numel() == 1:
                    val = float(result.item())
                else:
                    val = float(result.float().mean().item())
            else:
                val = float(result)
            if np.isnan(val) or np.isinf(val):
                return 0.0
            return val
        except Exception:
            return 0.0

    @staticmethod
    def _safe_1d(fn, *args, **kwargs):
        """安全调用 audiofeat 函数, 返回 1D numpy array (无 NaN/Inf)"""
        try:
            result = fn(*args, **kwargs)
            if hasattr(result, 'numpy'):
                result = result.numpy()
            arr = np.asarray(result, dtype=np.float64).ravel()
            arr = arr[~np.isnan(arr)]
            arr = arr[~np.isinf(arr)]
            return arr
        except Exception:
            return np.array([], dtype=np.float64)

    @staticmethod
    def _clamp_jitter(val: float) -> float:
        """Jitter 值域检查 — audiofeat 对合成信号可能返回异常大值"""
        if np.isnan(val) or np.isinf(val):
            return 0.0
        # 正常 jitter 范围: 0-5% (病理 > 5%)
        if val > 10.0:
            return 0.0
        return float(val)

    @staticmethod
    def _compute_closed_quotient(y, sr: int) -> float:
        """计算声门闭合商 (近似, 基于 F0 估算)"""
        try:
            from audiofeat.f0 import fundamental_frequency_pyin
            f0 = fundamental_frequency_pyin(y, sr)
            if f0 is None or f0.numel() == 0:
                return 0.0
            f0_median = float(f0[f0 > 0].median()) if (f0 > 0).any() else 0.0
            if f0_median < 50:
                return 0.0
            period = int(sr / f0_median)
            from audiofeat.voice import closed_quotient
            cq = closed_quotient(y, period)
            return float(cq) if not np.isnan(float(cq)) else 0.0
        except Exception:
            return 0.0
