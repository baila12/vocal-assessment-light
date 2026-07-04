"""
Praat CPP (倒谱峰值显著性) 分析模块 v5.18

移植自 VoiceLab (MeasureCPPNode.py) — 使用 parselmouth 的 Praat 原生 CPP 计算。
VoiceLab 使用 parselmouth.praat.call 调用 Praat 的 To PowerCepstrum 和
Get peak prominence，是学术标准的 CPP 实现。

参考:
  VoiceLab: https://github.com/Voice-Lab/VoiceLab
  Boersma, P. & Weenink, D. (2025). Praat: doing phonetics by computer.
  Hillenbrand, J. et al. (1994). "Acoustic correlates of breathy vocal quality."
"""
from dataclasses import dataclass
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class CepstralResult:
    """Praat CPP 分析结果"""
    cpp_mean: float = 0.0  # CPP 值 (dB), 典型人声 5-15
    cpp_std: float = 0.0   # 未使用 (保持接口兼容)
    cpp_max: float = 0.0   # 未使用 (保持接口兼容)


class PraatCPP:
    """
    Praat CPP 分析器 — 移植自 VoiceLab MeasureCPPNode

    使用 Praat 原生 PowerCepstrum + Get peak prominence:
    1. 创建 parselmouth.Sound
    2. 可选: 提取纯有声段 (VUV TextGrid)
    3. Spectrum → To PowerCepstrum → Get peak prominence
    4. 返回 CPP 值

    与 VoiceLab 的对齐:
    - 默认不分离有声段 (性能考虑), 可通过 voiced_only 开启
    - pitch_floor/pitch_ceiling 使用人声标准范围 (60-600Hz)
    - tilt_line quefrency 范围使用标准值 (0.001-0.020s)
    """

    # 人声标准音高范围
    PITCH_FLOOR = 60.0    # Hz
    PITCH_CEILING = 600.0  # Hz

    # 倒谱倾斜线 quefrency 范围 (VoiceLab 默认值)
    TILT_LOWER = 0.001   # 1ms
    TILT_UPPER = 0.0     # 0 = 全部范围

    def __init__(self):
        """初始化 Praat CPP 分析器"""
        self._available = False
        try:
            import parselmouth
            self._parselmouth = parselmouth
            self._available = True
        except ImportError:
            logger.warning(
                "parselmouth 未安装。PraatCPP 不可用。"
                "安装: pip install praat-parselmouth"
            )

    @property
    def available(self) -> bool:
        return self._available

    def analyze(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 22050,
        voiced_only: bool = False
    ) -> CepstralResult:
        """
        使用 Praat 原生 API 计算 CPP — 对齐 VoiceLab MeasureCPPNode

        Args:
            audio_data: 1D 音频信号数组
            sample_rate: 采样率 (Hz)
            voiced_only: 是否仅分析有声段 (VoiceLab 默认开启, 此处默认关闭)

        Returns:
            CepstralResult: 包含 cpp_mean
        """
        if not self._available:
            return CepstralResult()

        if len(audio_data) == 0:
            return CepstralResult()

        try:
            call = self._parselmouth.praat.call

            signal = np.asarray(audio_data, dtype=np.float64)
            signal = signal - np.mean(signal)

            # 创建 Praat Sound
            sound = self._parselmouth.Sound(
                signal, sampling_frequency=sample_rate
            )

            # VoiceLab: 可选有声段过滤
            if voiced_only:
                sound = self._extract_voiced_segments(sound)

            # VoiceLab: Spectrum → PowerCepstrum → Get peak prominence
            spectrum = sound.to_spectrum()
            cepstrum = call(spectrum, "To PowerCepstrum")

            cpp = call(
                cepstrum,
                "Get peak prominence",
                self.PITCH_FLOOR,
                self.PITCH_CEILING,
                "Parabolic",          # interpolation
                self.TILT_LOWER,      # tilt line quefrency lower
                self.TILT_UPPER,      # tilt line quefrency upper (0=all)
                "Straight",           # line type
                "Robust",             # fit method
            )

            return CepstralResult(
                cpp_mean=float(cpp),
                cpp_std=0.0,
                cpp_max=float(cpp)
            )

        except Exception as e:
            logger.warning(f"Praat CPP 分析失败: {e}")
            return CepstralResult()

    def _extract_voiced_segments(self, sound):
        """
        提取纯有声段 — VoiceLab 的 VUV TextGrid 方法

        Args:
            sound: parselmouth.Sound 对象

        Returns:
            parselmouth.Sound: 仅包含有声段的声音
        """
        try:
            call = self._parselmouth.praat.call

            # 基频检测
            pitch = sound.to_pitch_cc(
                pitch_floor=self.PITCH_FLOOR,
                pitch_ceiling=self.PITCH_CEILING
            )

            # PointProcess → VUV TextGrid
            point_process = call(
                [sound, pitch], "To PointProcess (cc)"
            )
            textgrid = call(
                point_process, "To TextGrid (vuv)", 0.02, 0.01
            )

            # 提取有声区间
            voiced_sounds = call(
                [sound, textgrid], "Extract all intervals", 1, False
            )

            # 拼接有声段
            if isinstance(voiced_sounds, list) and len(voiced_sounds) > 0:
                return call(voiced_sounds, "Concatenate")
            return sound

        except Exception as e:
            logger.debug(f"有声段提取失败, 使用全音频: {e}")
            return sound
