"""
Praat 声质特征提取模块 v6.2

通过 parselmouth (Praat Python API) 提取临床级声质特征:
- Jitter: 周期间频率变化 → 声带稳定性 [Baken & Orlikoff 2000]
- Shimmer: 周期间幅度变化 → 声带闭合质量 [Baken & Orlikoff 2000]
- Formants (F1-F4): 声道共振 → 共鸣质量 [Sundberg 1987]
- Praat HNR: 谐波噪声比 (不同于 de Krom 1993 的倒谱法)

文献:
- Baken & Orlikoff (2000). "Clinical Measurement of Speech and Voice."
  - Jitter 正常值: < 1.04% (Table 6-5)
  - Shimmer 正常值: < 3.81% (Table 7-3)
- Sundberg (1987). "The Science of the Singing Voice."
  - Singer's formant: 2.5-3.5 kHz 能量簇 (Ch.5)
  - Formant tuning: F1/F2 调整用于投射 (Ch.2)
- Hillenbrand et al. (1994). "Acoustic correlates of breathy vocal quality."
  - CPP 与 HNR 互补, jitter/shimmer 与感知音质相关

性能注意:
- parselmouth 的 jitter/shimmer 分析需要 PointProcess, 对长音频开销大
- Quick 模式: 降采样 (每 5 帧跳 1) → ~2s
- Pro 模式: 全部分析 → ~5s
"""
from dataclasses import dataclass, field
from typing import Optional
import numpy as np
import logging

logger = logging.getLogger(__name__)

try:
    import parselmouth
    PARSELMOUTH_AVAILABLE = True
except ImportError:
    PARSELMOUTH_AVAILABLE = False
    logger.warning("parselmouth not installed — Praat voice quality features disabled")


@dataclass
class PraatVoiceQualityResult:
    """Praat 声质特征结果 v6.2"""
    success: bool = False

    # Jitter (周期频率变化) — 正常值 < 1.04% [Baken & Orlikoff 2000]
    jitter_local: float = 0.0       # % — 连续周期的平均绝对频率差
    jitter_rap: float = 0.0         # % — 3周期窗口相对平均扰动
    jitter_ppq5: float = 0.0        # % — 5周期窗口相对平均扰动

    # Shimmer (周期幅度变化) — 正常值 < 3.81% [Baken & Orlikoff 2000]
    shimmer_local: float = 0.0      # % — 连续周期的平均绝对幅度差
    shimmer_apq3: float = 0.0       # % — 3周期窗口幅度扰动商

    # Formants (声道共振) [Sundberg 1987]
    f1_mean: float = 0.0            # Hz — 第一共振峰均值 (开口度)
    f2_mean: float = 0.0            # Hz — 第二共振峰均值 (舌位前后)
    f3_mean: float = 0.0            # Hz — 第三共振峰均值
    f4_mean: float = 0.0            # Hz — 第四共振峰均值
    f1_std: float = 0.0             # Hz — F1 标准差
    f2_std: float = 0.0             # Hz — F2 标准差

    # Singer's formant [Sundberg 1987, Ch.5]
    singers_formant_energy: float = 0.0  # 2.5-3.5kHz / 0-5kHz 能量比

    # Praat HNR (自相关法, 不同于倒谱法)
    praat_hnr: float = 0.0          # dB


class PraatVoiceQualityAnalyzer:
    """
    Praat 声质分析器 v6.2

    封装 parselmouth 的临床声质特征提取.
    所有特征均有文献支撑的正常值范围.

    使用:
        analyzer = PraatVoiceQualityAnalyzer(sample_rate=22050)
        result = analyzer.analyze(audio_data, f0, voiced_flags)
    """

    # 歌唱声音的 Praat 参数范围 (比语音更宽)
    PITCH_FLOOR = 50.0   # Hz — 男低音可到 D2 (~73Hz), 留 50 余量
    PITCH_CEILING = 1200.0  # Hz — 女高音可到 D6 (~1175Hz)
    MAX_FORMANTS = 5      # 包含歌手共振峰
    FORMANT_CEILING = 5500.0  # Hz — 女性/高音的共振峰上限

    def __init__(self, sample_rate: int = 22050):
        self.sample_rate = sample_rate

    def analyze(
        self,
        audio_data: np.ndarray,
        f0: Optional[np.ndarray] = None,
        voiced_flags: Optional[np.ndarray] = None,
        quick_mode: bool = False
    ) -> PraatVoiceQualityResult:
        """
        提取 Praat 声质特征

        Args:
            audio_data: 音频数据 (float64, [-1, 1])
            f0: 基频序列 (可选, 用于验证)
            voiced_flags: 有声段标记 (可选)
            quick_mode: True 时降采样加速 (~2s vs ~5s)

        Returns:
            PraatVoiceQualityResult: 声质特征
        """
        if not PARSELMOUTH_AVAILABLE:
            return PraatVoiceQualityResult()

        if len(audio_data) < 2048:
            return PraatVoiceQualityResult()

        try:
            # 转换为 parselmouth Sound 对象
            sound = parselmouth.Sound(
                audio_data.astype(np.float64), sampling_frequency=self.sample_rate
            )

            result = PraatVoiceQualityResult()

            # 1. Pitch + PointProcess (jitter/shimmer 的输入)
            pitch = sound.to_pitch(
                time_step=0.01,  # 10ms 步长
                pitch_floor=self.PITCH_FLOOR,
                pitch_ceiling=self.PITCH_CEILING
            )

            # PointProcess: 声门脉冲标记
            pulses = parselmouth.praat.call(
                [sound, pitch], "To PointProcess (cc)"
            )

            # 2. Jitter 提取
            self._extract_jitter(pulses, sound, result)

            # 3. Shimmer 提取
            self._extract_shimmer(pulses, sound, result)

            # 4. Formants 提取
            self._extract_formants(sound, result, quick_mode)

            # 5. Praat HNR
            self._extract_praat_hnr(sound, result)

            result.success = True
            logger.debug(
                f"Praat VQ: jitter={result.jitter_local:.2f}%, "
                f"shimmer={result.shimmer_local:.2f}%, "
                f"F1={result.f1_mean:.0f}Hz, F2={result.f2_mean:.0f}Hz, "
                f"HNR={result.praat_hnr:.1f}dB"
            )

            return result

        except Exception as e:
            logger.warning(f"Praat voice quality analysis failed: {e}")
            return PraatVoiceQualityResult()

    def _extract_jitter(
        self, pulses, sound, result: PraatVoiceQualityResult
    ) -> None:
        """提取 Jitter (周期频率变化)"""
        try:
            # Jitter (local): 连续周期平均绝对频率差 / 平均周期
            result.jitter_local = parselmouth.praat.call(
                pulses, "Get jitter (local)", 0.0, 0.0, 0.0001, 0.02, 1.3
            )
            # Jitter (rap): 3周期窗口相对平均扰动
            result.jitter_rap = parselmouth.praat.call(
                pulses, "Get jitter (rap)", 0.0, 0.0, 0.0001, 0.02, 1.3
            )
            # Jitter (ppq5): 5周期窗口相对平均扰动
            result.jitter_ppq5 = parselmouth.praat.call(
                pulses, "Get jitter (ppq5)", 0.0, 0.0, 0.0001, 0.02, 1.3
            )
        except Exception as e:
            logger.debug(f"Jitter extraction failed: {e}")

    def _extract_shimmer(
        self, pulses, sound, result: PraatVoiceQualityResult
    ) -> None:
        """提取 Shimmer (周期幅度变化)"""
        try:
            # Shimmer (local): 连续周期平均绝对幅度差
            result.shimmer_local = parselmouth.praat.call(
                [sound, pulses], "Get shimmer (local)", 0.0, 0.0,
                0.0001, 0.02, 1.3, 1.6
            )
            # Shimmer (apq3): 3周期窗口幅度扰动
            result.shimmer_apq3 = parselmouth.praat.call(
                [sound, pulses], "Get shimmer (apq3)", 0.0, 0.0,
                0.0001, 0.02, 1.3, 1.6
            )
        except Exception as e:
            logger.debug(f"Shimmer extraction failed: {e}")

    def _extract_formants(
        self, sound, result: PraatVoiceQualityResult, quick_mode: bool = False
    ) -> None:
        """
        提取 Formants (F1-F4) 和 Singer's formant

        Burg 方法 (to_formant_burg):
        - 准确的共振峰估计, 对高基频的歌唱声音友好
        - max_number_of_formants=5 以捕获歌手共振峰 (2.5-3.5kHz)
        """
        try:
            time_step = 0.02 if quick_mode else 0.01  # Quick: 50Hz vs 100Hz
            formants = sound.to_formant_burg(
                time_step=time_step,
                max_number_of_formants=self.MAX_FORMANTS,
                maximum_formant=self.FORMANT_CEILING,
                window_length=0.025,
                pre_emphasis_from=50.0
            )

            # 收集各共振峰时间序列
            times = formants.xs()
            if len(times) < 3:
                return

            f1_vals, f2_vals, f3_vals, f4_vals = [], [], [], []

            for t in times:
                f1 = formants.get_value_at_time(1, t)
                f2 = formants.get_value_at_time(2, t)
                f3 = formants.get_value_at_time(3, t)
                f4 = formants.get_value_at_time(4, t)
                # 过滤无效值 (Praat 返回 0 表示未检测到)
                if f1 > 50:
                    f1_vals.append(f1)
                if f2 > 100:
                    f2_vals.append(f2)
                if f3 > 200:
                    f3_vals.append(f3)
                if f4 > 400:
                    f4_vals.append(f4)

            if f1_vals:
                result.f1_mean = float(np.mean(f1_vals))
                result.f1_std = float(np.std(f1_vals))
            if f2_vals:
                result.f2_mean = float(np.mean(f2_vals))
                result.f2_std = float(np.std(f2_vals))
            if f3_vals:
                result.f3_mean = float(np.mean(f3_vals))
            if f4_vals:
                result.f4_mean = float(np.mean(f4_vals))

            # Singer's formant: 2.5-3.5kHz / 0-5kHz 能量比
            self._extract_singers_formant(sound, result)

        except Exception as e:
            logger.debug(f"Formant extraction failed: {e}")

    def _extract_singers_formant(
        self, sound, result: PraatVoiceQualityResult
    ) -> None:
        """
        Singer's formant 检测 [Sundberg 1987, Ch.5]

        计算 2.5-3.5 kHz 能量与 0-5 kHz 总能量的比值。
        经过训练的古典歌手在此频段有明显能量峰。
        流行歌手通常较低。
        """
        try:
            # 使用 parselmouth 的 Spectrum 分析
            spectrum = sound.to_spectrum()
            # 获取频带能量 (简化方法: 使用 LTAS)
            ltas = sound.to_ltas(pitch_floor=self.PITCH_FLOOR)
            freqs = ltas.xs()
            energy = np.array([ltas.get_value_at_frequency(f) for f in freqs])

            if len(energy) < 10:
                return

            # 2.5-3.5 kHz 能量
            mask_sf = (freqs >= 2500) & (freqs <= 3500)
            sf_energy = np.sum(energy[mask_sf])

            # 0-5 kHz 总能量
            mask_total = freqs <= 5000
            total_energy = np.sum(energy[mask_total])

            if total_energy > 0:
                result.singers_formant_energy = float(sf_energy / total_energy)

        except Exception as e:
            logger.debug(f"Singer's formant extraction failed: {e}")

    def _extract_praat_hnr(
        self, sound, result: PraatVoiceQualityResult
    ) -> None:
        """
        Praat HNR (自相关法)

        不同于 de Krom (1993) 的倒谱法。
        Praat 使用自相关函数检测周期性, 计算谐波/噪声能量比。
        """
        try:
            harmonicity = parselmouth.praat.call(
                sound, "To Harmonicity (cc)", 0.01, self.PITCH_FLOOR, 0.1, 1.0
            )
            result.praat_hnr = parselmouth.praat.call(
                harmonicity, "Get mean", 0.0, 0.0
            )
        except Exception as e:
            logger.debug(f"Praat HNR extraction failed: {e}")
