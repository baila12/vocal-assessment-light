"""
声乐评估任务

异步评估音频的五个维度：音量、音准、节奏、气息、情绪
"""
from PySide6.QtCore import QRunnable
from typing import Dict
import numpy as np
import librosa
from scipy import signal
import logging

from .signals import WorkerSignals
from .cache import get_audio_cache
from .emotion_analyzer import get_emotion_analyzer

logger = logging.getLogger(__name__)


class AssessmentTask(QRunnable):
    """声乐评估任务 - 性能优化版"""

    def __init__(self, filepath: str):
        super().__init__()
        self.filepath = filepath
        self.signals = WorkerSignals()
        self._cancelled = False
        self.setAutoDelete(True)

    def cancel(self):
        """取消任务"""
        self._cancelled = True

    def _check_cancelled(self):
        """检查是否已取消"""
        if self._cancelled:
            raise InterruptedError("处理已取消")

    def run(self):
        try:
            self.signals.started.emit("开始评估...")

            # 1. 加载音频 - 使用缓存
            self.signals.progress.emit("加载音频", 5)
            cache = get_audio_cache()
            cached = cache.get(self.filepath)
            if cached is not None:
                audio_data, sample_rate = cached
                logger.debug("评估使用缓存音频")
            else:
                audio_data, sample_rate = librosa.load(self.filepath, sr=None, mono=True)
                cache.set(self.filepath, audio_data, sample_rate)
            self._check_cancelled()

            # 2. 人声分离
            self.signals.progress.emit("人声分离", 15)
            vocal_audio = self._separate_vocals_fast(audio_data, sample_rate)
            self._check_cancelled()

            # 3. 音高检测
            self.signals.progress.emit("音高检测", 35)
            times, frequencies = self._detect_pitch(vocal_audio, sample_rate)
            pitch_data = {'times': times, 'frequencies': frequencies}
            self._check_cancelled()

            # 4. 节奏分析
            self.signals.progress.emit("节奏分析", 55)
            rhythm_data = self._analyze_rhythm(vocal_audio, sample_rate)
            self._check_cancelled()

            # 5. 技巧分析
            self.signals.progress.emit("技巧分析", 70)
            technique_data = self._analyze_techniques(times, frequencies, sample_rate)
            self._check_cancelled()

            # 6. 情感识别
            self.signals.progress.emit("情感分析", 85)
            emotion_data = self._recognize_emotion(vocal_audio, sample_rate)
            self._check_cancelled()

            # 7. 计算评分
            self.signals.progress.emit("计算评分", 95)
            scores = self._calculate_scores(pitch_data, rhythm_data, technique_data, emotion_data, audio_data)

            result = {
                'scores': scores,
                'pitch': pitch_data,
                'rhythm': rhythm_data,
                'technique': technique_data,
                'emotion': emotion_data,
                'advice': self._generate_advice(scores)
            }

            self.signals.finished.emit(result)

        except InterruptedError:
            self.signals.error.emit("评估已取消")
        except Exception as e:
            logger.error(f"评估失败: {e}")
            self.signals.error.emit(str(e))

    def _separate_vocals_fast(self, audio_data: np.ndarray, sample_rate: int) -> np.ndarray:
        """快速人声分离"""
        if len(audio_data) < sample_rate * 5:
            return audio_data

        try:
            n_fft = 1024
            hop_length = 256

            D = librosa.stft(audio_data, n_fft=n_fft, hop_length=hop_length)
            magnitude = np.abs(D)
            phase = np.angle(D)

            harmonic, percussive = librosa.decompose.hpss(magnitude, kernel_size=15)
            vocal_mag = harmonic * 0.8 + percussive * 0.2
            vocal_stft = vocal_mag * np.exp(1j * phase)
            return librosa.istft(vocal_stft, hop_length=hop_length, length=len(audio_data))
        except Exception as e:
            logger.warning(f"人声分离失败，使用原始音频: {e}")
            return audio_data

    def _detect_pitch(self, audio: np.ndarray, sample_rate: int):
        """音高检测"""
        hop_length = 512
        f0, voiced_flag, _ = librosa.pyin(
            audio,
            fmin=librosa.note_to_hz('C2'),
            fmax=librosa.note_to_hz('C6'),
            sr=sample_rate,
            hop_length=hop_length
        )
        times = librosa.times_like(f0, sr=sample_rate, hop_length=hop_length)
        frequencies = np.where(voiced_flag, f0, np.nan)
        return times, frequencies

    def _analyze_rhythm(self, audio: np.ndarray, sample_rate: int) -> Dict:
        """节奏分析"""
        onset_env = librosa.onset.onset_strength(y=audio, sr=sample_rate)
        tempo, beat_frames = librosa.beat.beat_track(onset_envelope=onset_env, sr=sample_rate)

        onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sample_rate)
        onset_count = len(onset_frames)

        if len(beat_frames) > 1:
            beat_intervals = np.diff(beat_frames) * 512 / sample_rate
            stability = 1.0 - min(1.0, np.std(beat_intervals) / (np.mean(beat_intervals) + 1e-6))
        else:
            stability = 0.0

        return {
            'bpm': float(tempo),
            'beat_frames': beat_frames.tolist(),
            'stability': float(stability),
            'onset_count': onset_count,
            'beat_times': librosa.frames_to_time(beat_frames, sr=sample_rate).tolist()
        }

    def _analyze_techniques(self, times: np.ndarray, frequencies: np.ndarray, sample_rate: int) -> Dict:
        """技巧分析"""
        valid_mask = ~np.isnan(frequencies)
        valid_freqs = frequencies[valid_mask]
        valid_times = times[valid_mask]

        if len(valid_freqs) < 10:
            return {'vibrato': {'count': 0, 'rate': 0}, 'glides': {'count': 0}}

        vibrato_count = 0
        vibrato_rates = []

        if len(valid_freqs) > 40:
            try:
                hop_length = 512
                dt = hop_length / sample_rate
                nyquist = 1 / (2 * dt)
                low, high = 4 / nyquist, 7 / nyquist

                if low < high < 1.0:
                    b, a = signal.butter(2, [low, high], btype='band')
                    filtered_f0 = signal.filtfilt(b, a, valid_freqs)
                    peaks, _ = signal.find_peaks(
                        filtered_f0,
                        height=np.std(filtered_f0) * 0.3,
                        distance=int(1 / (7 * dt))
                    )

                    if len(peaks) > 1:
                        peak_intervals = np.diff(peaks) * dt
                        rates = 1 / peak_intervals
                        valid_rates = rates[(rates >= 4) & (rates <= 7)]
                        if len(valid_rates) > 0:
                            vibrato_count = len(valid_rates)
                            vibrato_rates = valid_rates.tolist()
            except Exception:
                pass

        # 滑音检测
        freq_diff = np.abs(np.diff(valid_freqs))
        time_diff = np.diff(valid_times)
        glide_threshold = 50
        time_threshold = 0.2

        glide_mask = (freq_diff > glide_threshold) & (time_diff < time_threshold)
        glide_count = np.sum(glide_mask)

        return {
            'vibrato': {'count': vibrato_count, 'rate': np.mean(vibrato_rates) if vibrato_rates else 0},
            'glides': {'count': int(glide_count)}
        }

    def _recognize_emotion(self, audio: np.ndarray, sample_rate: int) -> Dict:
        """情感识别"""
        analyzer = get_emotion_analyzer()
        return analyzer.analyze(audio, sample_rate)

    def _calculate_scores(self, pitch_data, rhythm_data, technique_data, emotion_data, audio_data) -> Dict:
        """计算五维评分"""
        # 音量评分
        rms = np.sqrt(np.mean(audio_data ** 2))
        rms_db = 20 * np.log10(rms) if rms > 0 else -80

        frame_length = 2048
        hop_length = 512
        rms_frames = librosa.feature.rms(y=audio_data, frame_length=frame_length, hop_length=hop_length)[0]

        rms_mean = np.mean(rms_frames) + 1e-10
        rms_std = np.std(rms_frames)
        dynamic_range = rms_std / rms_mean

        rms_diff = np.abs(np.diff(rms_frames))
        volume_stability = 1.0 - np.mean(rms_diff) / (rms_mean + 1e-10)
        volume_stability = max(0, min(1, volume_stability))

        if -30 <= rms_db <= -6:
            level_score = 70 + volume_stability * 10
        elif -40 <= rms_db < -30:
            level_score = 50 + (rms_db + 40) * 2 + volume_stability * 5
        elif rms_db > -6:
            level_score = max(40, 70 - (rms_db + 6) * 3)
        else:
            level_score = max(25, 30 + (rms_db + 60) * 0.5)

        dynamic_bonus = min(10, dynamic_range * 20)
        volume_score = level_score + dynamic_bonus

        # 音准评分
        frequencies = pitch_data.get('frequencies', np.array([]))
        times = pitch_data.get('times', np.array([]))

        if len(frequencies) > 0:
            valid_mask = ~np.isnan(frequencies) & (frequencies > 80) & (frequencies < 1200)
            valid_freqs = frequencies[valid_mask]
            valid_times = times[valid_mask]
        else:
            valid_freqs = np.array([])
            valid_times = np.array([])

        pitch_score = 50

        if len(valid_freqs) > 30:
            detection_rate = len(valid_freqs) / len(frequencies) if len(frequencies) > 0 else 0
            midi_notes = 12 * np.log2(valid_freqs / 440) + 69

            window_size = min(20, len(midi_notes) // 8)
            if window_size > 3:
                local_stds = []
                for i in range(0, len(midi_notes) - window_size, window_size // 2):
                    window = midi_notes[i:i + window_size]
                    local_stds.append(np.std(window))
                avg_local_std = np.mean(local_stds)
                pitch_stability = max(0, 1 - avg_local_std / 2)
            else:
                pitch_stability = 0.5

            freq_range = np.max(valid_freqs) - np.min(valid_freqs)
            range_score = min(1.0, freq_range / 300)

            pitch_score = 30 + detection_rate * 25 + pitch_stability * 30 + range_score * 10

        elif len(valid_freqs) > 10:
            detection_rate = len(valid_freqs) / len(frequencies) if len(frequencies) > 0 else 0
            pitch_score = 35 + detection_rate * 25
        else:
            pitch_score = 25

        # 节奏评分
        rhythm_stability = rhythm_data.get('stability', 0.5)
        onset_count = rhythm_data.get('onset_count', 0)
        duration = len(audio_data) / 44100
        expected_beats = duration * 100 / 60

        if expected_beats > 0 and onset_count > 0:
            beat_ratio = min(1.5, onset_count / expected_beats)
            density_score = min(1.0, beat_ratio)
        else:
            density_score = 0.3

        rhythm_score = 40 + rhythm_stability * 30 + density_score * 20

        # 气息评分
        try:
            harmonic, percussive = librosa.effects.hpss(audio_data)
            harmonic_energy = np.sum(harmonic ** 2)
            total_energy = np.sum(audio_data ** 2) + 1e-10

            hnr = harmonic_energy / (total_energy - harmonic_energy + 1e-10)
            hnr_db = 10 * np.log10(hnr + 1e-10)

            if hnr_db > 20:
                breath_quality = 75 + min(10, (hnr_db - 20) * 2)
            elif hnr_db > 10:
                breath_quality = 55 + (hnr_db - 10) * 2
            elif hnr_db > 0:
                breath_quality = 40 + hnr_db * 1.5
            else:
                breath_quality = max(25, 40 + hnr_db * 0.5)
        except Exception:
            breath_quality = 50

        rms_frames = librosa.feature.rms(y=audio_data)[0]
        rms_cv = np.std(rms_frames) / (np.mean(rms_frames) + 1e-10)
        energy_stability = max(0, 1 - rms_cv * 0.5)

        vibrato = technique_data.get('vibrato', {})
        vibrato_count = vibrato.get('count', 0)
        vibrato_bonus = min(10, vibrato_count * 2)

        breath_score = breath_quality * 0.6 + (40 + energy_stability * 25) * 0.3 + vibrato_bonus * 0.1

        # 情绪评分
        emotion_confidence = emotion_data.get('confidence', 0.5)
        emotion_scores_dict = emotion_data.get('scores', {})

        if emotion_scores_dict:
            strong_emotions = ['angry', 'happy', 'surprised']
            strong_prob = sum(emotion_scores_dict.get(e, 0) for e in strong_emotions)

            probs = [max(0.001, s) for s in emotion_scores_dict.values()]
            probs = [p / sum(probs) for p in probs]
            entropy = -sum(p * np.log(p) for p in probs if p > 0)

            diversity = min(1.0, entropy / 1.0)
            intensity = emotion_confidence * 0.5 + strong_prob * 0.5

            emotion_score = 35 + intensity * 35 + diversity * 20
        else:
            mfccs = librosa.feature.mfcc(y=audio_data, sr=44100, n_mfcc=13)
            mfcc_var = np.mean(np.var(mfccs, axis=1))
            emotion_score = 40 + min(30, mfcc_var * 100)

        return {
            'volume': round(max(25, min(85, volume_score)), 1),
            'pitch': round(max(25, min(85, pitch_score)), 1),
            'rhythm': round(max(30, min(85, rhythm_score)), 1),
            'breath': round(max(25, min(85, breath_score)), 1),
            'emotion': round(max(30, min(85, emotion_score)), 1),
        }

    def _generate_advice(self, scores: Dict) -> str:
        """生成练习建议"""
        LEVEL_EXCELLENT = 90.0
        LEVEL_GOOD = 80.0
        LEVEL_NORMAL = 70.0
        LEVEL_FAIR = 60.0

        def get_level(score: float) -> tuple:
            if score >= LEVEL_EXCELLENT:
                return "优秀", "★★★", "#27AE60"
            elif score >= LEVEL_GOOD:
                return "良好", "★★", "#3498DB"
            elif score >= LEVEL_NORMAL:
                return "普通", "★", "#F39C12"
            elif score >= LEVEL_FAIR:
                return "一般", "☆", "#E67E22"
            else:
                return "待改进", "", "#E74C3C"

        def get_pitch_advice(score: float) -> tuple:
            if score >= LEVEL_EXCELLENT:
                return ("音准精准，音高控制达到专业水准", "挑战高难度曲目，尝试转音、装饰音等技巧")
            elif score >= LEVEL_GOOD:
                return ("音准表现出色，音高控制稳定", "尝试更复杂的音阶练习（如八度跳跃）")
            elif score >= LEVEL_NORMAL:
                return ("音准基本准确，偶尔有小幅偏差", "每天跟唱音阶10分钟，注意音准稳定性")
            elif score >= LEVEL_FAIR:
                return ("音准需要加强，存在明显音高偏差", "从基础音阶do-re-mi开始，使用调音器跟唱")
            else:
                return ("音准问题较大，音高识别需要从基础开始", "建议先进行听音训练")

        def get_rhythm_advice(score: float) -> tuple:
            if score >= LEVEL_EXCELLENT:
                return ("节奏感出色，拍子精准稳定", "挑战复杂节奏型")
            elif score >= LEVEL_GOOD:
                return ("节奏感很好，拍子稳定", "尝试更复杂的切分节奏")
            elif score >= LEVEL_NORMAL:
                return ("节奏基本稳定，偶尔有抢拍或拖拍", "使用节拍器APP练习")
            elif score >= LEVEL_FAIR:
                return ("节奏感需要加强，拍子不够稳定", "每天用节拍器练习")
            else:
                return ("节奏问题明显，缺乏基本的节奏感", "从拍手打拍子开始练习")

        def get_breath_advice(score: float) -> tuple:
            if score >= LEVEL_EXCELLENT:
                return ("气息控制精湛，呼吸平稳有力", "挑战高难度气息技巧")
            elif score >= LEVEL_GOOD:
                return ("气息控制优秀，呼吸平稳", "尝试长音挑战")
            elif score >= LEVEL_NORMAL:
                return ("气息基本稳定，偶有不够用", "每天练习腹式呼吸5分钟")
            elif score >= LEVEL_FAIR:
                return ("气息控制需要改进", "系统学习腹式呼吸")
            else:
                return ("气息问题明显，缺乏基本的呼吸支撑", "从腹式呼吸开始")

        def get_volume_advice(score: float) -> tuple:
            if score >= LEVEL_EXCELLENT:
                return ("音量控制精湛", "挑战更细腻的动态控制")
            elif score >= LEVEL_GOOD:
                return ("音量控制出色", "练习更多动态对比")
            elif score >= LEVEL_NORMAL:
                return ("音量控制尚可", "练习同一音高的渐强渐弱")
            elif score >= LEVEL_FAIR:
                return ("音量控制欠佳", "练习叹气发声法")
            else:
                return ("音量控制问题明显", "从基础发声练习开始")

        def get_emotion_advice(score: float) -> tuple:
            if score >= LEVEL_EXCELLENT:
                return ("情感表达丰富动人", "挑战不同风格曲目")
            elif score >= LEVEL_GOOD:
                return ("情感表达丰富", "尝试更多风格的歌曲")
            elif score >= LEVEL_NORMAL:
                return ("有基本的情感表达", "深入理解歌词含义")
            elif score >= LEVEL_FAIR:
                return ("情感表达较平淡", "先朗诵歌词体会情感")
            else:
                return ("情感表达欠缺", "多听优秀演唱")

        dimensions = [
            ("pitch", "音准", get_pitch_advice),
            ("rhythm", "节奏", get_rhythm_advice),
            ("breath", "气息", get_breath_advice),
            ("volume", "音量", get_volume_advice),
            ("emotion", "情感", get_emotion_advice),
        ]

        score_list = [(key, name, scores.get(key, 0)) for key, name, _ in dimensions]
        sorted_scores = sorted(score_list, key=lambda x: x[2], reverse=True)
        strongest = sorted_scores[0]
        weakest = sorted_scores[-1]

        advice_sections = []
        for key, name, advice_func in dimensions:
            score = scores.get(key, 0)
            level, emoji, color = get_level(score)
            suggestion, practice = advice_func(score)

            marker = ""
            if key == strongest[0] and score >= LEVEL_GOOD:
                marker = "【强项】"
            elif key == weakest[0] and score < LEVEL_NORMAL:
                marker = "【优先改进】"

            section = f"【{name} {score:.1f}分 - {level} {emoji}】{marker}\n建议：{suggestion}\n练习：{practice}"
            advice_sections.append(section)

        avg_score = sum(scores.get(k, 0) for k, _, _ in dimensions) / len(dimensions)

        if avg_score >= LEVEL_GOOD:
            summary = f"\n整体评价：表现良好！平均分 {avg_score:.1f}\n继续加强优势项目，重点改进弱项。"
        elif avg_score >= LEVEL_NORMAL:
            summary = f"\n整体评价：表现普通。平均分 {avg_score:.1f}\n建议重点改进【{weakest[1]}】方面。"
        else:
            summary = f"\n整体评价：需要加强。平均分 {avg_score:.1f}\n建议从基础开始系统学习。"

        general_tips = (
            "\n通用练习建议：\n"
            "• 练习前进行5-10分钟热身\n"
            "• 选择适合自己音域的歌曲\n"
            "• 录音回放是发现问题最有效的方法\n"
            "• 建议每次练习时间：30-45分钟"
        )

        return "\n\n".join(advice_sections) + summary + general_tips
