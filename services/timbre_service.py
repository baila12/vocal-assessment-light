"""
音色分析服务

专业音色特征分析，包括：
- 明亮度 (Brightness): 频谱质心
- 温暖度 (Warmth): 低频能量占比
- 鼻音占比 (Nasality): 特定频段能量
- 气声占比 (Breathiness): 高频噪声能量
- 颤音检测 (Vibrato): 音高周期性变化
- HNR (Harmonics-to-Noise Ratio): 声带闭合度
"""

import numpy as np
import librosa
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict
import logging

logger = logging.getLogger(__name__)


@dataclass
class TimbreResult:
    """音色分析结果 DTO"""
    success: bool
    brightness: float = 0.0       # 明亮度 0-1
    warmth: float = 0.0           # 温暖度 0-1
    nasality: float = 0.0         # 鼻音占比 0-1
    breathiness: float = 0.0      # 气声占比 0-1
    hnr: float = 0.0              # 谐波噪声比 dB
    vibrato_rate: float = 0.0     # 颤音频率 Hz
    vibrato_extent: float = 0.0   # 颤音幅度 半音
    vibrato_count: int = 0        # 颤音次数
    timbre_style: str = ""        # 整体音色风格标签
    error_message: Optional[str] = None


class TimbreService:
    """
    音色分析服务

    基于声学特征进行专业音色分析
    """

    # 频率阈值
    LOW_FREQ = 500       # 低频阈值
    MID_FREQ = 2000      # 中频阈值
    HIGH_FREQ = 4000     # 高频阈值
    NASAL_LOW = 1000     # 鼻音频段下限
    NASAL_HIGH = 3000    # 鼻音频段上限
    BREATH_FREQ = 5000   # 气声频率下限

    def __init__(self, sample_rate: int = 22050):
        """
        初始化音色分析服务

        Args:
            sample_rate: 音频采样率
        """
        self.sample_rate = sample_rate

    def analyze(
        self,
        audio_data: np.ndarray,
        f0: Optional[np.ndarray] = None
    ) -> TimbreResult:
        """
        执行完整音色分析

        Args:
            audio_data: 音频数据
            f0: 基音频率序列 (可选，用于颤音检测)

        Returns:
            TimbreResult: 音色分析结果
        """
        try:
            # 确保数据有效
            if audio_data is None or len(audio_data) == 0:
                return TimbreResult(
                    success=False,
                    error_message="音频数据为空"
                )

            # 1. 明亮度分析
            brightness = self._analyze_brightness(audio_data)

            # 2. 温暖度分析
            warmth = self._analyze_warmth(audio_data)

            # 3. 鼻音分析
            nasality = self._analyze_nasality(audio_data)

            # 4. 气声分析
            breathiness = self._analyze_breathiness(audio_data)

            # 5. HNR 分析
            hnr = self._analyze_hnr(audio_data)

            # 6. 颤音检测
            vibrato_rate, vibrato_extent, vibrato_count = self._detect_vibrato(f0)

            # 7. 生成音色风格标签
            timbre_style = self._generate_style_label(
                brightness, warmth, nasality, breathiness, hnr
            )

            return TimbreResult(
                success=True,
                brightness=brightness,
                warmth=warmth,
                nasality=nasality,
                breathiness=breathiness,
                hnr=hnr,
                vibrato_rate=vibrato_rate,
                vibrato_extent=vibrato_extent,
                vibrato_count=vibrato_count,
                timbre_style=timbre_style
            )

        except Exception as e:
            logger.exception("音色分析失败")
            return TimbreResult(
                success=False,
                error_message=str(e)
            )

    def _analyze_brightness(self, audio_data: np.ndarray) -> float:
        """
        分析明亮度

        明亮度与频谱质心正相关
        质心越高，声音越明亮
        """
        # 计算频谱质心
        spectral_centroids = librosa.feature.spectral_centroid(
            y=audio_data,
            sr=self.sample_rate,
            n_fft=2048,
            hop_length=512
        )[0]

        # 平均质心
        mean_centroid = np.mean(spectral_centroids)

        # 归一化到 0-1 (假设人声主要在 500Hz - 5000Hz)
        min_centroid = 500
        max_centroid = 5000

        brightness = (mean_centroid - min_centroid) / (max_centroid - min_centroid)
        brightness = np.clip(brightness, 0, 1)

        return round(float(brightness), 3)

    def _analyze_warmth(self, audio_data: np.ndarray) -> float:
        """
        分析温暖度

        温暖度与低频能量占比正相关
        低频能量越多，声音越温暖厚实
        """
        # 计算短时傅里叶变换
        stft = np.abs(librosa.stft(audio_data, n_fft=2048, hop_length=512))

        # 频率 bins
        freqs = librosa.fft_frequencies(sr=self.sample_rate, n_fft=2048)

        # 低频索引
        low_freq_idx = freqs < self.LOW_FREQ

        # 计算能量
        total_energy = np.sum(stft ** 2)
        low_freq_energy = np.sum(stft[low_freq_idx, :] ** 2)

        if total_energy > 0:
            warmth = low_freq_energy / total_energy
        else:
            warmth = 0

        # 归一化 (人声低频占比通常在 0.1-0.4)
        warmth = np.clip(warmth * 3, 0, 1)

        return round(float(warmth), 3)

    def _analyze_nasality(self, audio_data: np.ndarray) -> float:
        """
        分析鼻音占比

        鼻音主要集中在 1000-3000Hz 频段
        该频段能量占比越高，鼻音越重
        """
        # 计算短时傅里叶变换
        stft = np.abs(librosa.stft(audio_data, n_fft=2048, hop_length=512))

        # 频率 bins
        freqs = librosa.fft_frequencies(sr=self.sample_rate, n_fft=2048)

        # 鼻音频段索引
        nasal_idx = (freqs >= self.NASAL_LOW) & (freqs <= self.NASAL_HIGH)

        # 计算能量
        total_energy = np.sum(stft ** 2)
        nasal_energy = np.sum(stft[nasal_idx, :] ** 2)

        if total_energy > 0:
            nasality = nasal_energy / total_energy
        else:
            nasality = 0

        # 归一化 (正常鼻音占比约 0.15-0.35)
        # 超过 0.3 认为有明显鼻音
        nasality = np.clip((nasality - 0.15) / 0.2, 0, 1)

        return round(float(nasality), 3)

    def _analyze_breathiness(self, audio_data: np.ndarray) -> float:
        """
        分析气声占比

        气声主要表现为高频噪声能量
        5000Hz 以上能量占比越高，气声越重
        """
        # 计算短时傅里叶变换
        stft = np.abs(librosa.stft(audio_data, n_fft=2048, hop_length=512))

        # 频率 bins
        freqs = librosa.fft_frequencies(sr=self.sample_rate, n_fft=2048)

        # 高频索引
        high_freq_idx = freqs >= self.BREATH_FREQ

        # 计算能量
        total_energy = np.sum(stft ** 2)
        high_freq_energy = np.sum(stft[high_freq_idx, :] ** 2)

        if total_energy > 0:
            breathiness = high_freq_energy / total_energy
        else:
            breathiness = 0

        # 归一化 (正常气声占比约 0.01-0.1)
        breathiness = np.clip(breathiness * 10, 0, 1)

        return round(float(breathiness), 3)

    def _analyze_hnr(self, audio_data: np.ndarray) -> float:
        """
        分析谐波噪声比 (HNR)

        HNR 反映声带闭合程度
        HNR 越高，声带闭合越好，声音越清晰
        """
        try:
            # 使用 librosa 的方法估算 HNR
            # 分帧
            frames = librosa.util.frame(audio_data, frame_length=2048, hop_length=512)

            hnr_values = []

            for frame in frames.T:
                # 自相关方法计算 HNR
                autocorr = np.correlate(frame, frame, mode='full')
                autocorr = autocorr[len(autocorr) // 2:]

                if len(autocorr) > 0 and autocorr[0] > 0:
                    # 找基音周期的自相关峰值
                    # 简化：使用前 1/4 的峰值
                    search_range = len(autocorr) // 4
                    if search_range > 1:
                        peak_idx = np.argmax(autocorr[1:search_range]) + 1
                        r0 = autocorr[0]
                        r1 = autocorr[peak_idx] if peak_idx < len(autocorr) else 0

                        if r1 > 0:
                            # HNR = 10 * log10(r0 / (r0 - r1))
                            hnr = 10 * np.log10(max(r0 / (r0 - r1 + 1e-10), 1))
                            hnr_values.append(hnr)

            if hnr_values:
                mean_hnr = np.mean(hnr_values)
                # 限制在合理范围
                mean_hnr = np.clip(mean_hnr, 0, 40)
            else:
                mean_hnr = 0

            return round(float(mean_hnr), 2)

        except Exception as e:
            logger.warning(f"HNR 计算失败: {e}")
            return 0.0

    def _detect_vibrato(
        self,
        f0: Optional[np.ndarray]
    ) -> Tuple[float, float, int]:
        """
        检测颤音

        颤音特征：
        - 频率：5-8 Hz
        - 幅度：0.5-2 个半音

        Args:
            f0: 基音频率序列

        Returns:
            (颤音频率, 颤音幅度, 颤音次数)
        """
        if f0 is None or len(f0) < 100:
            return 0.0, 0.0, 0

        try:
            # 过滤无效值
            valid_mask = (f0 > 50) & (f0 < 1000)
            f0_valid = f0[valid_mask]

            if len(f0_valid) < 50:
                return 0.0, 0.0, 0

            # 转换为半音
            f0_semitones = 12 * np.log2(f0_valid / 440.0)

            # 去趋势
            f0_detrended = f0_semitones - np.convolve(
                f0_semitones,
                np.ones(20) / 20,
                mode='same'
            )

            # FFT 分析周期性
            fft_result = np.fft.fft(f0_detrended)
            freqs = np.fft.fftfreq(len(f0_detrended), d=512 / self.sample_rate)

            # 寻找 5-8 Hz 范围的峰值
            vibrato_mask = (freqs >= 4) & (freqs <= 9)
            vibrato_power = np.abs(fft_result) ** 2

            if np.sum(vibrato_mask) > 0:
                vibrato_power_range = vibrato_power.copy()
                vibrato_power_range[~vibrato_mask] = 0

                max_idx = np.argmax(vibrato_power_range)
                vibrato_rate = abs(freqs[max_idx])

                # 计算颤音幅度
                vibrato_extent = np.std(f0_detrended) * 2

                # 检测颤音段数量
                vibrato_count = self._count_vibrato_segments(f0_detrended, vibrato_rate)

                return round(vibrato_rate, 2), round(vibrato_extent, 2), vibrato_count

            return 0.0, 0.0, 0

        except Exception as e:
            logger.warning(f"颤音检测失败: {e}")
            return 0.0, 0.0, 0

    def _count_vibrato_segments(
        self,
        f0_detrended: np.ndarray,
        vibrato_rate: float
    ) -> int:
        """
        计算颤音段数量

        基于周期性和幅度阈值
        """
        if vibrato_rate < 4:
            return 0

        # 颤音周期（帧数）
        frames_per_cycle = self.sample_rate / (512 * vibrato_rate)

        # 计算滑动窗口的能量
        window_size = int(frames_per_cycle * 2)
        if window_size < 4:
            window_size = 4

        energy = np.convolve(
            f0_detrended ** 2,
            np.ones(window_size) / window_size,
            mode='same'
        )

        # 阈值
        threshold = np.mean(energy) * 1.5

        # 计算超过阈值的连续段
        above_threshold = energy > threshold

        count = 0
        in_segment = False

        for val in above_threshold:
            if val and not in_segment:
                count += 1
                in_segment = True
            elif not val:
                in_segment = False

        return count

    def _generate_style_label(
        self,
        brightness: float,
        warmth: float,
        nasality: float,
        breathiness: float,
        hnr: float
    ) -> str:
        """
        生成音色风格标签

        基于各维度特征的综合判断
        """
        styles = []

        # 明亮度判断
        if brightness > 0.7:
            styles.append("明亮")
        elif brightness < 0.3:
            styles.append("柔和")

        # 温暖度判断
        if warmth > 0.6:
            styles.append("厚实")
        elif warmth < 0.3:
            styles.append("单薄")

        # 鼻音判断
        if nasality > 0.6:
            styles.append("鼻音重")

        # 气声判断
        if breathiness > 0.5:
            styles.append("气声")
        elif breathiness < 0.1:
            styles.append("清晰")

        # HNR 判断 (声带闭合)
        if hnr > 25:
            styles.append("声带闭合良好")
        elif hnr < 15:
            styles.append("声带闭合不足")

        # 组合标签
        if len(styles) == 0:
            return "中性音色"
        elif len(styles) <= 2:
            return "、".join(styles)
        else:
            return "、".join(styles[:2]) + f"等{len(styles)}个特征"
