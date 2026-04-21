"""
逐句评分服务

基于乐句分段进行独立评分：
- 自动分段（基于 onset 检测）
- 每段独立评分
- 分段可视化支持
"""

import numpy as np
import librosa
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
import logging

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

    基于乐句分段进行独立评分分析
    """

    # 最小句子长度（秒）
    MIN_PHRASE_DURATION = 1.5
    # 最大句子长度（秒）
    MAX_PHRASE_DURATION = 15.0

    def __init__(self, sample_rate: int = 22050):
        """
        初始化逐句评分服务

        Args:
            sample_rate: 音频采样率
        """
        self.sample_rate = sample_rate

    def analyze_phrases(
        self,
        audio_data: np.ndarray,
        f0: Optional[np.ndarray] = None,
        onset_times: Optional[List[float]] = None
    ) -> PhraseResult:
        """
        执行逐句分析

        Args:
            audio_data: 音频数据
            f0: 基音频率序列
            onset_times: 预计算的 onset 时间点

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

            # 3. 对每段进行评分
            phrase_scores = []
            for i, (start, end) in enumerate(phrases):
                score = self._score_phrase(
                    audio_data, start, end, f0, i
                )
                phrase_scores.append(score)

            # 4. 计算统计信息
            if phrase_scores:
                avg_score = np.mean([p.total for p in phrase_scores])
                best_idx = np.argmax([p.total for p in phrase_scores])
                worst_idx = np.argmin([p.total for p in phrase_scores])
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
        audio_data: np.ndarray,
        start: float,
        end: float,
        f0: Optional[np.ndarray],
        phrase_id: int
    ) -> PhraseScore:
        """
        对单个分段进行评分
        """
        # 提取分段音频
        start_sample = int(start * self.sample_rate)
        end_sample = int(end * self.sample_rate)
        phrase_audio = audio_data[start_sample:end_sample]

        duration = end - start

        # 1. 音量评分
        volume_score = self._score_volume(phrase_audio)

        # 2. 音准评分
        pitch_score, note_range = self._score_pitch(phrase_audio, f0, start, end)

        # 3. 节奏评分
        rhythm_score = self._score_rhythm(phrase_audio)

        # 4. 气息评分
        breath_score = self._score_breath(phrase_audio)

        # 5. 情绪评分（简化）
        emotion_score = self._score_emotion(phrase_audio)

        # 计算总分
        total = (volume_score + pitch_score + rhythm_score + breath_score + emotion_score) / 5

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
        """评分音量"""
        rms = librosa.feature.rms(y=audio)[0]
        mean_rms = np.mean(rms)

        # 归一化 (假设理想 RMS 在 0.05-0.2)
        score = min(100, max(0, mean_rms * 500))
        return score

    def _score_pitch(
        self,
        audio: np.ndarray,
        f0: Optional[np.ndarray],
        start: float,
        end: float
    ) -> Tuple[float, Tuple[float, float]]:
        """评分音准"""
        # 提取该段的 f0
        if f0 is not None:
            hop_length = 512
            start_frame = int(start * self.sample_rate / hop_length)
            end_frame = int(end * self.sample_rate / hop_length)

            segment_f0 = f0[start_frame:end_frame]
            valid_f0 = segment_f0[(segment_f0 > 50) & (segment_f0 < 1000)]

            if len(valid_f0) > 10:
                # 音准稳定性
                f0_std = np.std(valid_f0)
                f0_mean = np.mean(valid_f0)

                # 标准差越小，分数越高
                stability_score = max(0, 100 - f0_std / f0_mean * 200)

                note_range = (float(np.min(valid_f0)), float(np.max(valid_f0)))
                return stability_score, note_range

        # 备用方案：重新计算
        try:
            local_f0, _, _ = librosa.pyin(
                audio,
                fmin=65,
                fmax=1047,
                sr=self.sample_rate
            )
            valid_f0 = local_f0[~np.isnan(local_f0)]

            if len(valid_f0) > 5:
                f0_std = np.std(valid_f0)
                f0_mean = np.mean(valid_f0)
                score = max(0, 100 - f0_std / f0_mean * 200)
                note_range = (float(np.min(valid_f0)), float(np.max(valid_f0)))
                return score, note_range
        except Exception:
            pass

        return 50.0, (0.0, 0.0)

    def _score_rhythm(self, audio: np.ndarray) -> float:
        """评分节奏"""
        try:
            tempo, _ = librosa.beat.beat_track(y=audio, sr=self.sample_rate)
            onset_env = librosa.onset.onset_strength(y=audio, sr=self.sample_rate)

            # 计算 onset 强度的变化
            onset_std = np.std(onset_env)

            # 标准差在合理范围内为好
            score = min(100, onset_std * 100)
            return score
        except Exception:
            return 50.0

    def _score_breath(self, audio: np.ndarray) -> float:
        """评分气息"""
        try:
            # 使用 RMS 变化评估气息稳定性
            rms = librosa.feature.rms(y=audio)[0]
            rms_changes = np.abs(np.diff(rms))
            mean_change = np.mean(rms_changes)

            # 变化越小，气息越稳
            stability = max(0, 100 - mean_change * 500)
            return stability
        except Exception:
            return 50.0

    def _score_emotion(self, audio: np.ndarray) -> float:
        """评分情绪（简化版）"""
        try:
            # 基于能量和频谱特征
            rms = librosa.feature.rms(y=audio)[0]
            spectral_centroid = librosa.feature.spectral_centroid(y=audio, sr=self.sample_rate)[0]

            energy_score = min(100, np.mean(rms) * 300)
            brightness_score = min(100, np.mean(spectral_centroid) / 100)

            return (energy_score + brightness_score) / 2
        except Exception:
            return 50.0

    def _generate_phrase_advice(
        self,
        volume: float,
        pitch: float,
        rhythm: float,
        breath: float
    ) -> List[str]:
        """生成该句的改进建议"""
        advice = []

        if volume < 70:
            advice.append("音量偏小，可适当加强气息支持")
        elif volume > 95:
            advice.append("音量偏大，注意控制力度")

        if pitch < 70:
            advice.append("音准有待提高，注意听标准音高")

        if rhythm < 70:
            advice.append("节奏感需加强，可配合节拍器练习")

        if breath < 70:
            advice.append("气息稳定性不足，建议腹式呼吸练习")

        if not advice:
            advice.append("该句表现良好，继续保持")

        return advice
