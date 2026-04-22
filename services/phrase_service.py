"""
逐句评分服务

基于乐句分段进行独立评分：
- 自动分段（基于 onset 检测）
- 每段独立评分
- 分段可视化支持
- 支持多线程并行处理
"""

import numpy as np
import librosa
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


@dataclass
class PhraseScore:
    """单句评分 DTO"""
    phrase_id: int              # 句子序号
    start_time: float           # 开始时间 (秒)
    end_time: float             # 结束时间 (秒)
    duration: float             # 时长 (秒)
    volume: float               # 音量评分
    pitch: float                # 音准评分
    rhythm: float               # 节奏评分
    breath: float               # 气息评分
    emotion: float              # 情绪评分
    total: float                # 总分
    level: str                  # 等级
    advice: List[str]           # 该句改进建议
    note_range: Tuple[float, float]  # 音高范围 (Hz)


@dataclass
class PhraseResult:
    """逐句评分结果 DTO"""
    success: bool
    phrases: List[PhraseScore] = None
    total_phrases: int = 0
    avg_score: float = 0.0
    best_phrase_id: int = 0     # 最佳句子
    worst_phrase_id: int = 0    # 最差句子
    error_message: Optional[str] = None


class PhraseService:
    """
    逐句评分服务

    基于乐句分段进行独立评分分析，支持多线程优化
    """

    # 最小句子长度（秒）
    MIN_PHRASE_DURATION = 1.5
    # 最大句子长度（秒）
    MAX_PHRASE_DURATION = 15.0
    # 默认采样率
    DEFAULT_SAMPLE_RATE = 22050
    # hop length for f0
    HOP_LENGTH = 512

    def __init__(self, sample_rate: int = 22050, max_workers: int = 4):
        """
        初始化逐句评分服务

        Args:
            sample_rate: 音频采样率
            max_workers: 最大并行线程数
        """
        self.sample_rate = sample_rate
        self.max_workers = max_workers

    def analyze_phrases(
        self,
        audio_data: np.ndarray,
        f0: Optional[np.ndarray] = None,
        onset_times: Optional[List[float]] = None,
        enable_parallel: bool = True
    ) -> PhraseResult:
        """
        执行逐句分析

        Args:
            audio_data: 音频数据
            f0: 基音频率序列（已计算，避免重复计算）
            onset_times: 预计算的 onset 时间点
            enable_parallel: 是否启用并行处理

        Returns:
            PhraseResult: 逐句评分结果
        """
        try:
            if audio_data is None or len(audio_data) == 0:
                return PhraseResult(
                    success=False,
                    error_message="音频数据为空"
                )

            # 1. 检测分段点
            if onset_times is None:
                onset_times = self._detect_onset_times(audio_data)

            # 2. 生成分段
            phrases = self._generate_phrases(audio_data, onset_times)

            if not phrases:
                return PhraseResult(
                    success=False,
                    error_message="无法检测到有效的乐句分段"
                )

            # 3. 预计算分段数据（避免在循环中重复计算）
            phrase_audios = []
            phrase_f0s = []
            hop_length = self.HOP_LENGTH

            for start, end in phrases:
                start_sample = int(start * self.sample_rate)
                end_sample = int(end * self.sample_rate)
                phrase_audio = audio_data[start_sample:end_sample]
                phrase_audios.append(phrase_audio)

                # 提取对应的 f0 片段
                if f0 is not None:
                    start_frame = int(start * self.sample_rate / hop_length)
                    end_frame = int(end * self.sample_rate / hop_length)
                    phrase_f0s.append(f0[start_frame:end_frame])
                else:
                    phrase_f0s.append(None)

            # 4. 并行或串行评分
            phrase_scores = []

            if enable_parallel and len(phrases) > 2:
                # 并行处理
                phrase_scores = self._score_phrases_parallel(
                    phrase_audios, phrase_f0s, phrases
                )
            else:
                # 串行处理
                for i, (phrase_audio, phrase_f0, (start, end)) in enumerate(
                    zip(phrase_audios, phrase_f0s, phrases)
                ):
                    score = self._score_phrase(
                        phrase_audio, phrase_f0, start, end, i
                    )
                    phrase_scores.append(score)

            # 5. 计算统计信息
            if phrase_scores:
                avg_score = np.mean([p.total for p in phrase_scores])
                best_idx = int(np.argmax([p.total for p in phrase_scores]))
                worst_idx = int(np.argmin([p.total for p in phrase_scores]))
            else:
                avg_score = 0
                best_idx = 0
                worst_idx = 0

            return PhraseResult(
                success=True,
                phrases=phrase_scores,
                total_phrases=len(phrase_scores),
                avg_score=round(avg_score, 1),
                best_phrase_id=best_idx,
                worst_phrase_id=worst_idx
            )

        except Exception as e:
            logger.exception("逐句分析失败")
            return PhraseResult(
                success=False,
                error_message=str(e)
            )

    def _score_phrases_parallel(
        self,
        phrase_audios: List[np.ndarray],
        phrase_f0s: List[np.ndarray],
        phrases: List[Tuple[float, float]]
    ) -> List[PhraseScore]:
        """并行评分多个分段"""
        phrase_scores = [None] * len(phrases)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}
            for i, (audio, f0, (start, end)) in enumerate(
                zip(phrase_audios, phrase_f0s, phrases)
            ):
                future = executor.submit(
                    self._score_phrase, audio, f0, start, end, i
                )
                futures[future] = i

            for future in as_completed(futures):
                i = futures[future]
                try:
                    phrase_scores[i] = future.result()
                except Exception as e:
                    logger.warning(f"分段 {i} 评分失败: {e}")
                    # 创建默认评分
                    phrase_scores[i] = PhraseScore(
                        phrase_id=i,
                        start_time=phrases[i][0],
                        end_time=phrases[i][1],
                        duration=phrases[i][1] - phrases[i][0],
                        volume=60.0,
                        pitch=60.0,
                        rhythm=60.0,
                        breath=60.0,
                        emotion=60.0,
                        total=60.0,
                        level="中等",
                        advice=["评分计算失败"],
                        note_range=(0.0, 0.0)
                    )

        return phrase_scores

    def _detect_onset_times(self, audio_data: np.ndarray) -> List[float]:
        """
        检测 onset 时间点

        使用 librosa 的 onset 检测算法
        """
        # 使用多种方法结合
        # 1. 基于频谱通量的 onset
        onset_frames = librosa.onset.onset_detect(
            y=audio_data,
            sr=self.sample_rate,
            hop_length=512,
            backtrack=True
        )
        onset_times = librosa.frames_to_time(
            onset_frames,
            sr=self.sample_rate,
            hop_length=512
        )

        # 2. 添加静音段分割点
        rms = librosa.feature.rms(y=audio_data, hop_length=512)[0]
        rms_threshold = np.mean(rms) * 0.3
        silent_frames = np.where(rms < rms_threshold)[0]

        # 将静音段转换为时间点
        silent_times = librosa.frames_to_time(
            silent_frames,
            sr=self.sample_rate,
            hop_length=512
        )

        # 合并并排序所有分段点
        all_times = sorted(set(list(onset_times) + list(silent_times)))

        # 过滤过于接近的点
        filtered_times = []
        last_time = -self.MIN_PHRASE_DURATION

        for t in all_times:
            if t - last_time >= self.MIN_PHRASE_DURATION:
                filtered_times.append(t)
                last_time = t

        return filtered_times

    def _generate_phrases(
        self,
        audio_data: np.ndarray,
        onset_times: List[float]
    ) -> List[Tuple[float, float]]:
        """
        生成分段列表

        Returns:
            [(start, end), ...] 分段时间列表
        """
        duration = len(audio_data) / self.sample_rate
        phrases = []

        # 添加起始点
        times = [0.0] + list(onset_times) + [duration]

        for i in range(len(times) - 1):
            start = times[i]
            end = times[i + 1]

            # 过滤过短的分段
            if end - start >= self.MIN_PHRASE_DURATION:
                # 分割过长的分段
                if end - start > self.MAX_PHRASE_DURATION:
                    # 等分
                    num_splits = int((end - start) / self.MAX_PHRASE_DURATION) + 1
                    split_duration = (end - start) / num_splits
                    for j in range(num_splits):
                        sub_start = start + j * split_duration
                        sub_end = start + (j + 1) * split_duration
                        phrases.append((sub_start, sub_end))
                else:
                    phrases.append((start, end))

        return phrases

    def _score_phrase(
        self,
        phrase_audio: np.ndarray,
        phrase_f0: Optional[np.ndarray],
        start: float,
        end: float,
        phrase_id: int
    ) -> PhraseScore:
        """
        对单个分段进行评分（优化版）
        """
        duration = end - start

        # 1. 音量评分（优化公式）
        volume_score = self._score_volume(phrase_audio)

        # 2. 音准评分（使用传入的 f0，避免重复计算）
        pitch_score, note_range = self._score_pitch_fast(phrase_audio, phrase_f0)

        # 3. 节奏评分
        rhythm_score = self._score_rhythm_fast(phrase_audio)

        # 4. 气息评分
        breath_score = self._score_breath_fast(phrase_audio)

        # 5. 情绪评分（简化）
        emotion_score = self._score_emotion_fast(phrase_audio)

        # 计算总分（加权平均）
        total = (
            volume_score * 0.15 +
            pitch_score * 0.30 +
            rhythm_score * 0.20 +
            breath_score * 0.20 +
            emotion_score * 0.15
        )

        # 确定等级
        if total >= 90:
            level = "优秀"
        elif total >= 80:
            level = "良好"
        elif total >= 70:
            level = "中等"
        elif total >= 60:
            level = "及格"
        else:
            level = "需改进"

        # 生成建议
        advice = self._generate_phrase_advice(
            volume_score, pitch_score, rhythm_score, breath_score
        )

        return PhraseScore(
            phrase_id=phrase_id,
            start_time=round(start, 2),
            end_time=round(end, 2),
            duration=round(duration, 2),
            volume=round(volume_score, 1),
            pitch=round(pitch_score, 1),
            rhythm=round(rhythm_score, 1),
            breath=round(breath_score, 1),
            emotion=round(emotion_score, 1),
            total=round(total, 1),
            level=level,
            advice=advice,
            note_range=note_range
        )

    def _score_volume(self, audio: np.ndarray) -> float:
        """
        评分音量（优化版）

        使用更合理的归一化范围，使正常音量能获得合理分数
        """
        rms = librosa.feature.rms(y=audio)[0]
        mean_rms = np.mean(rms)

        # 理想 RMS 范围: 0.02 - 0.15
        # 低于 0.02 音量太小，高于 0.15 音量过大
        if mean_rms < 0.02:
            # 音量太小，线性增长
            score = mean_rms / 0.02 * 60 + 20  # 20-80分
        elif mean_rms > 0.15:
            # 音量过大，逐渐降低
            excess = (mean_rms - 0.15) / 0.15
            score = max(60, 90 - excess * 30)
        else:
            # 理想范围，映射到 70-95 分
            score = 70 + (mean_rms - 0.02) / (0.15 - 0.02) * 25

        return min(100, max(0, score))

    def _score_pitch_fast(
        self,
        audio: np.ndarray,
        f0: Optional[np.ndarray]
    ) -> Tuple[float, Tuple[float, float]]:
        """
        快速音准评分（复用已计算的 f0）

        优化评分公式，使合理波动不会过度惩罚
        """
        valid_f0 = None

        # 优先使用传入的 f0
        if f0 is not None and len(f0) > 10:
            valid_mask = (f0 > 50) & (f0 < 1000)
            valid_f0 = f0[valid_mask]

        # 如果没有有效的 f0，快速计算
        if valid_f0 is None or len(valid_f0) < 5:
            try:
                # 使用更快的 pYIN 参数
                local_f0, _, _ = librosa.pyin(
                    audio,
                    fmin=65,
                    fmax=1047,
                    sr=self.sample_rate,
                    hop_length=self.HOP_LENGTH,
                    centers=None  # 加速
                )
                valid_f0 = local_f0[~np.isnan(local_f0)]
            except Exception:
                pass

        if valid_f0 is not None and len(valid_f0) > 5:
            f0_std = np.std(valid_f0)
            f0_mean = np.mean(valid_f0)

            # 优化：相对标准差，正常人声波动 5-15%
            relative_std = f0_std / f0_mean if f0_mean > 0 else 0.5

            # 更合理的评分：5% 波动 = 90分，15% 波动 = 70分，30% 波动 = 50分
            if relative_std < 0.05:
                score = 90 + (0.05 - relative_std) / 0.05 * 10  # 90-100
            elif relative_std < 0.15:
                score = 90 - (relative_std - 0.05) / 0.10 * 20  # 70-90
            elif relative_std < 0.30:
                score = 70 - (relative_std - 0.15) / 0.15 * 20  # 50-70
            else:
                score = max(30, 50 - (relative_std - 0.30) / 0.10 * 10)

            note_range = (float(np.min(valid_f0)), float(np.max(valid_f0)))
            return score, note_range

        return 50.0, (0.0, 0.0)

    def _score_rhythm_fast(self, audio: np.ndarray) -> float:
        """
        快速节奏评分（优化版）
        """
        try:
            onset_env = librosa.onset.onset_strength(y=audio, sr=self.sample_rate)

            # 计算 onset 强度的变化（节奏感）
            onset_std = np.std(onset_env)
            onset_mean = np.mean(onset_env)

            # 使用变异系数评估节奏稳定性
            cv = onset_std / (onset_mean + 1e-6)

            # 合理范围：0.5-2.0 的变异系数表示有节奏感
            if cv < 0.5:
                score = 60 + cv / 0.5 * 20  # 60-80，太稳定
            elif cv < 1.5:
                score = 80 + (cv - 0.5) / 1.0 * 15  # 80-95，理想范围
            else:
                score = max(50, 95 - (cv - 1.5) * 10)  # 太不稳定

            return min(100, max(0, score))
        except Exception:
            return 60.0

    def _score_breath_fast(self, audio: np.ndarray) -> float:
        """
        快速气息评分（优化版）
        """
        try:
            rms = librosa.feature.rms(y=audio)[0]

            if len(rms) < 2:
                return 60.0

            # 计算 RMS 变化率
            rms_changes = np.abs(np.diff(rms))
            mean_change = np.mean(rms_changes)
            mean_rms = np.mean(rms)

            # 相对变化率
            relative_change = mean_change / (mean_rms + 1e-6)

            # 优化评分：5% 变化率 = 90分，15% = 75分，30% = 60分
            if relative_change < 0.05:
                score = 90 + (0.05 - relative_change) / 0.05 * 10  # 90-100
            elif relative_change < 0.15:
                score = 90 - (relative_change - 0.05) / 0.10 * 15  # 75-90
            elif relative_change < 0.30:
                score = 75 - (relative_change - 0.15) / 0.15 * 15  # 60-75
            else:
                score = max(40, 60 - (relative_change - 0.30) / 0.10 * 10)

            return min(100, max(0, score))
        except Exception:
            return 60.0

    def _score_emotion_fast(self, audio: np.ndarray) -> float:
        """
        快速情绪评分（简化版）
        """
        try:
            # 基于能量和频谱特征
            rms = librosa.feature.rms(y=audio)[0]
            spectral_centroid = librosa.feature.spectral_centroid(
                y=audio, sr=self.sample_rate
            )[0]

            energy_mean = np.mean(rms)
            brightness_mean = np.mean(spectral_centroid)
            energy_std = np.std(rms)

            # 能量贡献（归一化到合理范围）
            energy_score = min(100, max(50, energy_mean * 400 + 50))

            # 亮度贡献（正常范围 1000-4000 Hz）
            brightness_score = min(100, max(50, brightness_mean / 50))

            # 动态变化贡献
            variation_score = min(100, max(50, energy_std * 500 + 50))

            # 综合评分
            return (energy_score * 0.4 + brightness_score * 0.3 + variation_score * 0.3)
        except Exception:
            return 60.0

    def _generate_phrase_advice(
        self,
        volume: float,
        pitch: float,
        rhythm: float,
        breath: float
    ) -> List[str]:
        """生成该句的改进建议"""
        advice = []

        if volume < 60:
            advice.append("音量偏小，可适当加强气息支持")
        elif volume > 95:
            advice.append("音量偏大，注意控制力度")

        if pitch < 60:
            advice.append("音准有待提高，注意听标准音高")

        if rhythm < 60:
            advice.append("节奏感需加强，可配合节拍器练习")

        if breath < 60:
            advice.append("气息稳定性不足，建议腹式呼吸练习")

        if not advice:
            advice.append("该句表现良好，继续保持")

        return advice
