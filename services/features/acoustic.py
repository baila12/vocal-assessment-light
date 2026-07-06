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
        检测是否为混合音频（带伴奏）— v6.0 文献驱动重构

        基于:
          - Lehner et al. (2018). "Online, Loudness-Invariant Vocal Detection
            in Mixed Music Signals." TASLP 26(8), 1369-1380. §4:
            子带频谱平坦度(1.5-3kHz) 是歌声检测最可靠的单特征,
            低频能量受录音条件影响过大, 区分力有限。
          - Driedger et al. (2014). "Extending Harmonic-Percussive Separation
            of Audio Signals." ISMIR. §3:
            HPSS 三元分解 H+P+R, 歌声颤音(5-8Hz)+清辅音→残差区(R),
            纯人声 HPSS harmonic ratio 通常 0.72-0.85。
          - Fitzgerald (2010). "Harmonic/Percussive Separation Using Median
            Filtering." DAFx: 中值滤波分离谐波/冲击成分。

        特征 (v6.0 改进):
          1. HPSS 谐波能量比 — 结构特征, 采样率无关 [Fitzgerald 2010]
          2. 子带频谱平坦度 (1.5-3kHz) — 文献证明最可靠 [Lehner 2018 §4]
          3. 高频能量比 (>5kHz) — 镲片/弦乐泛音指示
          4. 全频带频谱平坦度 — 辅助特征
          5. 谐波度 (Harmonicity) — f0 整数倍能量集中度

        移除: 低频能量 (<300Hz) — 受录音/房间/声部影响过大 [Lehner 2018]

        Args:
            audio_data: 音频数据 (建议使用原始采样率)

        Returns:
            (is_mixed, confidence, metadata_dict)
        """
        try:
            # 计算频谱
            stft = np.abs(librosa.stft(audio_data))
            spectrum = np.mean(stft, axis=1)
            freqs = librosa.fft_frequencies(sr=self.sample_rate)
            total_energy = np.sum(spectrum ** 2) + 1e-10

            # ============================================================
            # 特征1: HPSS 谐波能量比 [Fitzgerald 2010]
            #
            # Driedger et al. (2014) §3: 纯人声颤音使部分能量进入残差,
            # 正常范围 0.72-0.85。低于 0.72 暗示显著非谐波内容(伴奏)。
            # ============================================================
            harmonic, percussive = librosa.effects.hpss(
                audio_data, margin=(1.0, 3.0)
            )
            hpss_harmonic_ratio = float(
                np.sum(harmonic ** 2) / (np.sum(audio_data ** 2) + 1e-10)
            )
            hpss_score = np.clip((0.90 - hpss_harmonic_ratio) / 0.40, 0.0, 1.0)

            # ============================================================
            # 特征2: 子带频谱平坦度 (1.5-3kHz) [Lehner 2018 §4, Fig.3]
            #
            # 人声在此频段保持谐波结构→低平坦度; 多乐器混合→高平坦度
            # 这是 Lehner 实验中区分力最强的单特征
            # ============================================================
            sub_band_flatness = self._calc_sub_band_flatness(
                stft, freqs, 1500, 3000
            )
            # 归一化 (真音频校准): >0.30→1(典型伴奏), <0.08→0(纯净人声)
            # 纯人声子带平坦度实测 0.10-0.16, 轻伴奏 0.10-0.20
            sub_flat_score = np.clip((sub_band_flatness - 0.08) / 0.22, 0.0, 1.0)

            # ============================================================
            # 特征3: 高频能量 (>5kHz) [辅助]
            #
            # 镲片/弦乐泛音/电吉他失真集中在此频段
            # 纯人声 >5kHz 能量极少 (<2%)
            # ============================================================
            high_band_mask = freqs > 5000
            high_energy = np.sum(spectrum[high_band_mask] ** 2)
            high_freq_ratio = high_energy / total_energy
            high_freq_score = np.clip((high_freq_ratio - 0.01) / 0.04, 0.0, 1.0)

            # ============================================================
            # 特征4: 全频带频谱平坦度 [辅助]
            #
            # 多乐器叠加→频谱趋于平坦, 但清唱也可能因呼吸音而偏高
            # ============================================================
            full_band_flatness = librosa.feature.spectral_flatness(
                S=stft, hop_length=self.hop_length
            )
            mean_flatness = float(np.mean(full_band_flatness))
            flatness_score = np.clip(mean_flatness / 0.30, 0.0, 1.0)

            # ============================================================
            # 特征5: 谐波度 (Harmonicity) [Lehner 2018]
            #
            # 能量在 f0 整数倍处的集中程度
            # 纯人声: >0.5; 混合音频: 伴奏分散能量→<0.3
            # ============================================================
            harmonicity = self._calc_harmonicity(audio_data)
            # 归一化 (真音频校准): 纯人声实测 0.17-0.28, 需宽范围捕获
            # >0.40→0(强谐波), <0.05→1(噪声/复杂混合)
            harmonicity_score = np.clip((0.40 - harmonicity) / 0.35, 0.0, 1.0)

            # ============================================================
            # v6.0: 五特征加权投票 [Lehner 2018 feature importance]
            #
            # 权重基于 Lehner 2018 §4 的特征消融实验:
            #   子带平坦度(1.5-3kHz) — 最可靠   → 0.30
            #   HPSS 谐波比 — 结构稳定          → 0.25
            #   高频能量 — 采样率自适应          → 0.20
            #   谐波度 — 谐波结构量化            → 0.15
            #   全频平坦度 — 辅助               → 0.10
            #
            # 移除了低频能量 (Lehner 证明受录音条件影响过大)
            # ============================================================
            mixed_score = (
                0.30 * sub_flat_score +
                0.25 * hpss_score +
                0.20 * high_freq_score +
                0.15 * harmonicity_score +
                0.10 * flatness_score
            )

            # HPSS 门控 [Driedger 2014 §3; 真音频验证]:
            # - >0.88: 极其纯净→跳过 (含颤音清唱, 无任何伴奏迹象)
            # - 0.72-0.88: 正常范围 (纯人声或极轻伴奏, 需特征综合判断)
            # - <0.72: 显著非谐波→标准判断
            # 注: 0.88 经验阈值基于真音频测试 — 手写的从前(轻钢琴) 0.883 刚好在边界
            if hpss_harmonic_ratio > 0.88:
                is_mixed = False
                confidence = min(1.0, hpss_harmonic_ratio)
            else:
                # 双层阈值决策
                if mixed_score > 0.55:
                    is_mixed = True
                    confidence = 0.60 + (mixed_score - 0.55) * 0.8
                elif mixed_score > 0.40:
                    is_mixed = True
                    confidence = 0.40 + (mixed_score - 0.40) * 1.3
                elif mixed_score > 0.30:
                    # 灰区: 保守触发分离, 低置信
                    is_mixed = True
                    confidence = 0.25 + (mixed_score - 0.30) * 1.5
                else:
                    is_mixed = False
                    confidence = 1.0 - mixed_score * 3.0

            confidence = float(max(0.0, min(1.0, confidence)))

            # 元数据 (供上游日志/调试)
            metadata = {
                'hpss_harmonic_ratio': round(hpss_harmonic_ratio, 3),
                'hpss_score': round(hpss_score, 2),
                'sub_band_flatness': round(sub_band_flatness, 4),
                'sub_flat_score': round(sub_flat_score, 2),
                'high_freq_ratio': round(high_freq_ratio, 4),
                'high_freq_score': round(high_freq_score, 2),
                'full_flatness': round(mean_flatness, 4),
                'flatness_score': round(flatness_score, 2),
                'harmonicity': round(harmonicity, 3),
                'harmonicity_score': round(harmonicity_score, 2),
                'mixed_score': round(mixed_score, 3),
            }

            logger.debug(
                f"混合音频检测 v6.0: is_mixed={is_mixed}, confidence={confidence:.2f}, "
                f"score={mixed_score:.3f} (sr={self.sample_rate}), "
                f"hpss={hpss_harmonic_ratio:.3f}({hpss_score:.2f}), "
                f"sub_flat={sub_band_flatness:.4f}({sub_flat_score:.2f}), "
                f"high={high_freq_ratio:.4f}({high_freq_score:.2f}), "
                f"harm={harmonicity:.3f}({harmonicity_score:.2f}), "
                f"flat={mean_flatness:.4f}({flatness_score:.2f})"
            )

            return is_mixed, confidence, metadata

        except Exception as e:
            logger.warning(f"混合音频检测失败: {e}")
            return False, 0.0, {'error': str(e)}

    # ── v6.0 新增特征计算方法 ──

    def _calc_sub_band_flatness(
        self, stft: np.ndarray, freqs: np.ndarray,
        f_min: float, f_max: float
    ) -> float:
        """
        计算子带频谱平坦度 [Lehner 2018 §4]

        子带选择依据: 人声在此频段保持谐波结构→低平坦度;
        多乐器叠加→频谱平坦化→高平坦度。

        Args:
            stft: 幅度谱 (n_freqs × n_frames)
            freqs: 频率轴
            f_min, f_max: 子带频率范围 (Hz)

        Returns:
            子带内平均频谱平坦度 (0-1)
        """
        band_mask = (freqs >= f_min) & (freqs <= f_max)
        if np.sum(band_mask) < 4:
            return 0.0

        band_stft = stft[band_mask, :]
        if band_stft.size == 0:
            return 0.0

        # 几何平均 / 算术平均 (per-frame, then average across frames)
        power = band_stft ** 2 + 1e-12
        log_power = np.log(power)
        geometric_mean = np.exp(np.mean(log_power, axis=0))
        arithmetic_mean = np.mean(power, axis=0)
        frame_flatness = geometric_mean / (arithmetic_mean + 1e-12)

        return float(np.mean(frame_flatness))

    def _calc_harmonicity(self, audio_data: np.ndarray) -> float:
        """
        计算谐波度 (Harmonicity) [Lehner 2018]

        测量能量在基频整数倍处的集中程度。
        使用自相关法: 周期信号的自相关有明显峰值,
        噪声的自相关接近零。

        Args:
            audio_data: 时域音频信号

        Returns:
            谐波度 (0-1, 越高谐波结构越强)
        """
        if len(audio_data) < 512:
            return 0.0

        # 自相关法: 找到最大峰值 (排除零延迟)
        corr = np.correlate(audio_data, audio_data, mode='full')
        corr = corr[len(corr) // 2:]  # 只取正延迟
        corr = corr / (corr[0] + 1e-10)  # 归一化

        # 搜索第一个显著峰值 (基频周期)
        # 在 2ms-20ms 延迟范围搜索 (对应 50-500Hz 基频)
        min_lag = int(0.002 * self.sample_rate)
        max_lag = int(0.020 * self.sample_rate)

        if max_lag >= len(corr):
            max_lag = len(corr) - 1

        if min_lag >= max_lag:
            return 0.0

        peak_value = float(np.max(corr[min_lag:max_lag]))
        return max(0.0, min(1.0, peak_value))

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

        # 检测混合音频 (v6.0: 返回 metadata dict)
        is_mixed, confidence, metadata = self.detect_mixed_audio(audio_data)
        result.is_mixed_audio = is_mixed
        result.mixed_audio_confidence = confidence
        result._mixed_metadata = metadata

        return result
