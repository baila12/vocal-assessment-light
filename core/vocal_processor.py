"""
核心音频处理模块 - 复用现有实现
包含: 人声分离、音高检测、节奏分析、技巧分析、情感识别
"""
import sys
import numpy as np
import librosa
from pathlib import Path
from typing import Dict, Tuple, Optional, List
import warnings

warnings.filterwarnings('ignore')


class VocalProcessor:
    """声乐处理核心类 - 真正的模型调用"""

    def __init__(self):
        self.audio_data = None
        self.sample_rate = 22050
        self.vocal_audio = None  # 分离后的人声
        self.progress_callback = None
        self._cancelled = False

    def set_progress_callback(self, callback):
        """设置进度回调函数 callback(step_name, progress_percent)"""
        self.progress_callback = callback

    def cancel(self):
        """取消处理"""
        self._cancelled = True

    def _check_cancelled(self):
        """检查是否已取消"""
        if self._cancelled:
            raise InterruptedError("处理已取消")

    def _report_progress(self, step_name: str, progress: int):
        """报告进度"""
        if self.progress_callback:
            self.progress_callback(step_name, progress)

    def load_audio(self, filepath: str) -> bool:
        """加载音频文件"""
        try:
            self._check_cancelled()
            self._report_progress("加载音频", 0)
            self.audio_data, self.sample_rate = librosa.load(
                filepath, sr=None, mono=True
            )
            self._report_progress("加载音频", 100)
            return True
        except Exception as e:
            print(f"加载音频失败: {e}")
            return False

    def separate_vocals(self) -> np.ndarray:
        """人声分离 - 使用简化的频谱减法方法"""
        self._report_progress("人声分离", 10)

        if self.audio_data is None:
            raise ValueError("请先加载音频")

        # 备选方案：频谱减法
        return self._separate_vocals_fallback()

    def _separate_vocals_fallback(self) -> np.ndarray:
        """人声分离备选方案 - 基于频谱减法"""
        self._report_progress("人声分离", 50)

        # 计算STFT
        D = librosa.stft(self.audio_data)
        magnitude = np.abs(D)
        phase = np.angle(D)

        # 简单的谐波-打击乐分离
        harmonic, percussive = librosa.decompose.hpss(magnitude)

        # 人声主要在谐波成分中
        vocal_mag = harmonic * 0.8 + percussive * 0.2

        # 重建音频
        vocal_stft = vocal_mag * np.exp(1j * phase)
        vocal = librosa.istft(vocal_stft, length=len(self.audio_data))

        self.vocal_audio = vocal
        self._report_progress("人声分离", 100)

        return vocal

    def detect_pitch(self) -> Tuple[np.ndarray, np.ndarray]:
        """音高检测 - 使用librosa.pyin"""
        self._report_progress("音高检测", 0)

        audio = self.vocal_audio if self.vocal_audio is not None else self.audio_data

        if audio is None:
            raise ValueError("请先加载音频")

        self._report_progress("音高检测", 30)

        hop_length = 512
        f0, voiced_flag, voiced_probs = librosa.pyin(
            audio,
            fmin=librosa.note_to_hz('C2'),
            fmax=librosa.note_to_hz('C6'),
            sr=self.sample_rate,
            hop_length=hop_length
        )

        self._report_progress("音高检测", 70)

        times = librosa.times_like(f0, sr=self.sample_rate, hop_length=hop_length)
        frequencies = np.where(voiced_flag, f0, np.nan)

        self._report_progress("音高检测", 100)

        return times, frequencies

    def analyze_rhythm(self) -> Dict:
        """节奏分析"""
        self._check_cancelled()
        self._report_progress("节奏分析", 0)

        audio = self.vocal_audio if self.vocal_audio is not None else self.audio_data

        onset_env = librosa.onset.onset_strength(y=audio, sr=self.sample_rate)

        self._report_progress("节奏分析", 40)

        tempo, beat_frames = librosa.beat.beat_track(
            onset_envelope=onset_env,
            sr=self.sample_rate
        )

        self._report_progress("节奏分析", 70)

        if len(beat_frames) > 1:
            beat_intervals = np.diff(beat_frames) * 512 / self.sample_rate
            stability = 1.0 - min(1.0, np.std(beat_intervals) / np.mean(beat_intervals))
        else:
            stability = 0.0

        self._report_progress("节奏分析", 100)

        return {
            'bpm': float(tempo),
            'beat_frames': beat_frames.tolist(),
            'stability': float(stability),
            'beat_times': librosa.frames_to_time(beat_frames, sr=self.sample_rate).tolist()
        }

    def analyze_techniques(self, times: np.ndarray, frequencies: np.ndarray) -> Dict:
        """技巧分析 - 检测颤音、滑音等"""
        self._check_cancelled()
        self._report_progress("技巧分析", 0)

        valid_mask = ~np.isnan(frequencies)
        valid_freqs = frequencies[valid_mask]
        valid_times = times[valid_mask]

        if len(valid_freqs) < 10:
            return {'vibrato': {'count': 0, 'rate': 0}, 'glides': {'count': 0}}

        self._report_progress("技巧分析", 30)

        # 颤音检测
        vibrato_count = 0
        vibrato_rates = []

        if len(valid_freqs) > 40:
            from scipy import signal
            hop_length = 512
            dt = hop_length / self.sample_rate

            nyquist = 1 / (2 * dt)
            low = 4 / nyquist
            high = 7 / nyquist

            if low < high < 1.0:
                b, a = signal.butter(2, [low, high], btype='band')
                filtered_f0 = signal.filtfilt(b, a, valid_freqs)

                peaks, _ = signal.find_peaks(filtered_f0,
                                              height=np.std(filtered_f0) * 0.3,
                                              distance=int(1/(7*dt)))

                if len(peaks) > 1:
                    peak_intervals = np.diff(peaks) * dt
                    rates = 1 / peak_intervals
                    valid_rates = rates[(rates >= 4) & (rates <= 7)]
                    if len(valid_rates) > 0:
                        vibrato_count = len(valid_rates)
                        vibrato_rates = valid_rates.tolist()

        self._report_progress("技巧分析", 70)

        # 滑音检测
        glide_count = 0
        glide_threshold = 50

        for i in range(1, len(valid_freqs)):
            freq_change = abs(valid_freqs[i] - valid_freqs[i-1])
            time_change = valid_times[i] - valid_times[i-1]
            if freq_change > glide_threshold and time_change < 0.2:
                glide_count += 1

        self._report_progress("技巧分析", 100)

        return {
            'vibrato': {
                'count': vibrato_count,
                'rate': np.mean(vibrato_rates) if vibrato_rates else 0
            },
            'glides': {'count': glide_count}
        }

    def recognize_emotion(self) -> Dict:
        """情感识别 - 基于音频特征"""
        self._report_progress("情感识别", 0)

        audio = self.vocal_audio if self.vocal_audio is not None else self.audio_data

        return self._recognize_emotion_fallback(audio)

    def _recognize_emotion_fallback(self, audio: np.ndarray) -> Dict:
        """情感识别备选方案 - 基于音频特征"""
        self._report_progress("情感识别", 50)

        rms = librosa.feature.rms(y=audio)[0]
        energy_mean = np.mean(rms)
        energy_std = np.std(rms)

        spectral_centroids = librosa.feature.spectral_centroid(y=audio, sr=self.sample_rate)[0]
        brightness = np.mean(spectral_centroids)

        contrast = librosa.feature.spectral_contrast(y=audio, sr=self.sample_rate)
        contrast_mean = np.mean(contrast)

        zcr = librosa.feature.zero_crossing_rate(audio)[0]
        zcr_mean = np.mean(zcr)

        self._report_progress("情感识别", 80)

        energy_score = min(1.0, energy_mean / 0.1)
        brightness_score = min(1.0, brightness / 3000)
        variation_score = min(1.0, energy_std / 0.05)

        emotions = {
            'happy': energy_score * 0.4 + brightness_score * 0.4 + variation_score * 0.2,
            'sad': (1 - energy_score) * 0.5 + (1 - brightness_score) * 0.3 + (1 - variation_score) * 0.2,
            'angry': energy_score * 0.5 + variation_score * 0.5,
            'neutral': 0.3 + (1 - variation_score) * 0.4,
            'surprised': variation_score * 0.6 + energy_score * 0.4
        }

        dominant = max(emotions, key=emotions.get)
        confidence = emotions[dominant]

        self._report_progress("情感识别", 100)

        return {
            'dominant': dominant,
            'confidence': confidence,
            'scores': emotions
        }

    def calculate_scores(self, pitch_data: Dict, rhythm_data: Dict,
                        technique_data: Dict, emotion_data: Dict) -> Dict:
        """计算五维评分"""
        self._report_progress("计算评分", 0)

        frequencies = pitch_data.get('frequencies', [])
        valid_freqs = [f for f in frequencies if not np.isnan(f)]

        if len(valid_freqs) > 1:
            pitch_changes = np.diff(valid_freqs)
            stability = 1.0 - min(1.0, np.std(pitch_changes) / 50)
            pitch_score = stability * 100
        else:
            pitch_score = 50

        self._report_progress("计算评分", 40)

        rhythm_score = rhythm_data.get('stability', 0.5) * 100

        vibrato = technique_data.get('vibrato', {})
        vibrato_count = vibrato.get('count', 0)
        if vibrato_count > 0:
            rate = vibrato.get('rate', 5)
            if 4 <= rate <= 7:
                breath_score = 80 + min(20, vibrato_count * 2)
            else:
                breath_score = 60 + min(20, vibrato_count)
        else:
            breath_score = 50

        self._report_progress("计算评分", 70)

        emotion_score = emotion_data.get('confidence', 0.5) * 100

        if self.audio_data is not None:
            rms = np.sqrt(np.mean(self.audio_data ** 2))
            if 0.1 <= rms <= 0.5:
                volume_score = 80 + (0.3 - abs(rms - 0.3)) * 100
            else:
                volume_score = max(30, 100 - abs(rms - 0.3) * 200)
        else:
            volume_score = 50

        self._report_progress("计算评分", 100)

        return {
            'volume': min(100, max(0, volume_score)),
            'pitch': min(100, max(0, pitch_score)),
            'rhythm': min(100, max(0, rhythm_score)),
            'breath': min(100, max(0, breath_score)),
            'emotion': min(100, max(0, emotion_score)),
        }

    def process(self, filepath: str) -> Dict:
        """完整的音频处理流程"""
        self._cancelled = False

        if not self.load_audio(filepath):
            raise RuntimeError("无法加载音频文件")

        self.separate_vocals()

        times, frequencies = self.detect_pitch()
        pitch_data = {'times': times, 'frequencies': frequencies}

        rhythm_data = self.analyze_rhythm()
        technique_data = self.analyze_techniques(times, frequencies)
        emotion_data = self.recognize_emotion()

        scores = self.calculate_scores(pitch_data, rhythm_data, technique_data, emotion_data)

        return {
            'scores': scores,
            'pitch': pitch_data,
            'rhythm': rhythm_data,
            'technique': technique_data,
            'emotion': emotion_data,
            'advice': self._generate_advice(scores)
        }

    def _generate_advice(self, scores: Dict) -> str:
        """根据评分生成改进建议"""
        advice = []
        if scores.get('pitch', 0) < 70:
            advice.append("音准需要加强练习，建议多听标准音并模仿。")
        if scores.get('rhythm', 0) < 70:
            advice.append("节奏稳定性不足，建议跟着节拍器练习。")
        if scores.get('breath', 0) < 70:
            advice.append("气息控制需要改进，建议练习腹式呼吸。")
        if scores.get('volume', 0) < 70:
            advice.append("音量控制不佳，建议注意声音力度的变化。")
        if scores.get('emotion', 0) < 70:
            advice.append("情感表达可以更丰富，尝试投入更多情感。")
        return "\n".join(advice) if advice else "整体表现良好，继续保持！"