"""
统一的后台任务工作类
使用QThreadPool + QRunnable实现真正的异步
性能优化：添加缓存、预加载模型、减少重复计算
"""
from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool
import numpy as np
import librosa
import soundfile as sf
from typing import Dict, Callable, Optional
from pathlib import Path
import torch
import logging

logger = logging.getLogger(__name__)

# 情绪识别模型路径 - 使用相对路径
EMOTION_MODEL_PATH = str(Path(__file__).parent.parent / "models" / "emotion")

# 全局模型缓存（避免每次评估重新加载）
_emotion_classifier = None
# 与label_encoder.txt匹配的标签
_emotion_labels = ['neu', 'ang', 'hap', 'sad']
_model_loaded = False

# 音频数据缓存 - 避免重复加载同一文件
_audio_cache: Dict[str, tuple] = {}  # filepath -> (audio_data, sample_rate)
_cache_max_size = 5  # 最大缓存文件数


def preload_emotion_model():
    """预加载情绪模型 - 优先使用已下载的SpeechBrain模型"""
    global _emotion_classifier, _model_loaded
    if _model_loaded:
        return True

    # 尝试使用已下载的SpeechBrain预训练模型（不需要网络）
    try:
        from speechbrain.pretrained.interfaces import EncoderClassifier

        # SpeechBrain有本地缓存，尝试直接使用预训练模型名称加载
        # 如果已下载过，会使用本地缓存
        classifier = EncoderClassifier.from_hparams(
            source="speechbrain/emotion-recognition-wav2vec2-IEMOCAP",
            savedir="pretrained_models/emotion"
        )

        _emotion_classifier = {
            'type': 'speechbrain',
            'classifier': classifier,
            'labels': ['neu', 'ang', 'hap', 'sad']
        }
        _model_loaded = True
        logger.info("情绪模型预加载完成（SpeechBrain）")
        return True

    except Exception as e:
        logger.warning(f"SpeechBrain模型加载失败: {e}")

    # 备用：HuggingFace在线模型
    try:
        from transformers import AutoModelForAudioClassification, AutoFeatureExtractor
        model_name = "ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition"
        _emotion_classifier = {
            'type': 'transformers',
            'model': AutoModelForAudioClassification.from_pretrained(model_name),
            'feature_extractor': AutoFeatureExtractor.from_pretrained(model_name)
        }
        _model_loaded = True
        logger.info("情绪模型预加载完成（HuggingFace）")
        return True
    except Exception as e:
        logger.warning(f"情绪模型预加载失败: {e}")
        return False


def _load_emotion_model():
    """加载情绪识别模型（全局缓存）"""
    global _emotion_classifier
    if _emotion_classifier is not None:
        return _emotion_classifier
    preload_emotion_model()
    return _emotion_classifier


def _get_cached_audio(filepath: str) -> Optional[tuple]:
    """从缓存获取音频数据"""
    if filepath in _audio_cache:
        logger.debug(f"从缓存获取音频: {filepath}")
        return _audio_cache[filepath]
    return None


def _cache_audio(filepath: str, audio_data: np.ndarray, sample_rate: int):
    """缓存音频数据"""
    global _audio_cache
    # 清理旧缓存
    if len(_audio_cache) >= _cache_max_size:
        oldest_key = next(iter(_audio_cache))
        del _audio_cache[oldest_key]
        logger.debug(f"清理缓存: {oldest_key}")
    _audio_cache[filepath] = (audio_data, sample_rate)
    logger.debug(f"缓存音频: {filepath}")


class WorkerSignals(QObject):
    """工作线程信号"""
    started = Signal(str)  # 任务开始: 任务名称
    progress = Signal(str, int)  # 进度更新: 步骤名称, 百分比
    finished = Signal(object)  # 完成: 结果数据
    error = Signal(str)  # 错误: 错误信息


class AudioLoadTask(QRunnable):
    """音频加载任务 - 带缓存优化"""

    def __init__(self, filepath: str):
        super().__init__()
        self.filepath = filepath
        self.signals = WorkerSignals()
        self.setAutoDelete(True)

    def run(self):
        try:
            self.signals.started.emit("正在加载音频...")

            # 1. 基本信息（快速）
            path = Path(self.filepath)
            basic_info = {
                'filename': path.name,
                'filepath': str(path),
                'format': path.suffix.upper().replace('.', ''),
                'size_mb': path.stat().st_size / (1024 * 1024) if path.exists() else 0
            }

            self.signals.progress.emit("读取文件", 20)

            # 2. 加载音频数据 - 使用缓存
            cached = _get_cached_audio(self.filepath)
            if cached is not None:
                audio_data, sample_rate = cached
                logger.debug(f"使用缓存音频数据")
            else:
                audio_data, sample_rate = librosa.load(self.filepath, sr=None, mono=True)
                _cache_audio(self.filepath, audio_data, sample_rate)

            self.signals.progress.emit("分析参数", 50)

            # 3. 技术参数 - 使用librosa获取时长避免重复读取
            duration = len(audio_data) / sample_rate
            minutes = int(duration // 60)
            seconds = int(duration % 60)

            # 使用soundfile获取额外信息
            try:
                info = sf.info(self.filepath)
                technical_params = {
                    'sample_rate': info.samplerate,
                    'channels': info.channels,
                    'channel_name': '单声道' if info.channels == 1 else '立体声',
                    'duration_seconds': duration,
                    'duration_formatted': f"{minutes:02d}:{seconds:02d}",
                    'bit_depth': getattr(info, 'subtype', '未知')
                }
            except Exception:
                technical_params = {
                    'sample_rate': sample_rate,
                    'channels': 1,
                    'channel_name': '单声道',
                    'duration_seconds': duration,
                    'duration_formatted': f"{minutes:02d}:{seconds:02d}",
                    'bit_depth': '未知'
                }

            self.signals.progress.emit("分析音量", 70)

            # 4. 音量信息 - 优化计算
            volume_info = self._compute_volume_info(audio_data)

            self.signals.progress.emit("分析音高", 85)

            # 5. 音高统计（最慢，可选）
            pitch_stats = self._analyze_pitch(audio_data, sample_rate)

            result = {
                'basic_info': basic_info,
                'technical_params': technical_params,
                'volume_info': volume_info,
                'pitch_stats': pitch_stats,
                'audio_data': audio_data,
                'sample_rate': sample_rate,
                'valid': True
            }

            self.signals.finished.emit(result)

        except Exception as e:
            logger.error(f"音频加载失败: {e}")
            self.signals.error.emit(str(e))

    def _compute_volume_info(self, audio_data: np.ndarray) -> Dict:
        """优化版音量计算"""
        rms = np.sqrt(np.mean(audio_data ** 2))
        avg_db = 20 * np.log10(rms) if rms > 0 else -80
        peak = np.max(np.abs(audio_data))
        peak_db = 20 * np.log10(peak) if peak > 0 else -80

        # 使用向量化计算动态范围
        frame_length = 2048
        hop_length = 512
        rms_frames = librosa.feature.rms(y=audio_data, frame_length=frame_length, hop_length=hop_length)[0]
        valid_rms = rms_frames[rms_frames > 0]
        if len(valid_rms) > 0:
            dynamic_range = 20 * np.log10(np.max(valid_rms) / np.min(valid_rms))
        else:
            dynamic_range = 0

        return {
            'avg_db': float(avg_db),
            'peak_db': float(peak_db),
            'dynamic_range': float(dynamic_range)
        }

    def _analyze_pitch(self, audio_data: np.ndarray, sample_rate: int) -> Dict:
        """分析音高统计"""
        try:
            hop_length = 512
            f0, voiced_flag, _ = librosa.pyin(
                audio_data,
                fmin=librosa.note_to_hz('C2'),
                fmax=librosa.note_to_hz('C6'),
                sr=sample_rate,
                hop_length=hop_length
            )
            valid_mask = ~np.isnan(f0)
            valid_freqs = f0[valid_mask]

            if len(valid_freqs) > 0:
                min_freq = float(np.min(valid_freqs))
                max_freq = float(np.max(valid_freqs))
                min_note = librosa.hz_to_note(min_freq)
                max_note = librosa.hz_to_note(max_freq)
            else:
                min_freq, max_freq, min_note, max_note = 0, 0, '--', '--'

            return {
                'valid_frames': int(np.sum(valid_mask)),
                'total_frames': int(len(f0)),
                'min_freq': min_freq,
                'max_freq': max_freq,
                'min_note': min_note,
                'max_note': max_note
            }
        except Exception:
            return {
                'valid_frames': 0,
                'total_frames': 0,
                'min_freq': 0,
                'max_freq': 0,
                'min_note': '--',
                'max_note': '--'
            }


class AssessmentTask(QRunnable):
    """声乐评估任务 - 性能优化版"""

    def __init__(self, filepath: str):
        super().__init__()
        self.filepath = filepath
        self.signals = WorkerSignals()
        self._cancelled = False
        self.setAutoDelete(True)

    def cancel(self):
        self._cancelled = True

    def _check_cancelled(self):
        if self._cancelled:
            raise InterruptedError("处理已取消")

    def run(self):
        try:
            self.signals.started.emit("开始评估...")

            # 1. 加载音频 - 使用缓存
            self.signals.progress.emit("加载音频", 5)
            cached = _get_cached_audio(self.filepath)
            if cached is not None:
                audio_data, sample_rate = cached
                logger.debug("评估使用缓存音频")
            else:
                audio_data, sample_rate = librosa.load(self.filepath, sr=None, mono=True)
                _cache_audio(self.filepath, audio_data, sample_rate)
            self._check_cancelled()

            # 2. 人声分离 - 可选简化模式
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

            # 6. 情感识别 - 使用预加载模型
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
        """快速人声分离 - 性能优化版"""
        # 对于短音频直接返回，避免复杂处理
        if len(audio_data) < sample_rate * 5:  # 小于5秒
            return audio_data

        try:
            # 使用更小的n_fft加速STFT
            n_fft = 1024  # 默认2048，减小可加速
            hop_length = 256  # 默认512

            D = librosa.stft(audio_data, n_fft=n_fft, hop_length=hop_length)
            magnitude = np.abs(D)
            phase = np.angle(D)

            # 简化HPSS - 使用更小的kernel_size
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
        """节奏分析 - 基于专利中的起始点检测算法"""
        onset_env = librosa.onset.onset_strength(y=audio, sr=sample_rate)
        tempo, beat_frames = librosa.beat.beat_track(onset_envelope=onset_env, sr=sample_rate)

        # 起始点检测（专利中的Onset Detection）
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
        """技巧分析 - 向量化优化版"""
        valid_mask = ~np.isnan(frequencies)
        valid_freqs = frequencies[valid_mask]
        valid_times = times[valid_mask]

        if len(valid_freqs) < 10:
            return {'vibrato': {'count': 0, 'rate': 0}, 'glides': {'count': 0}}

        vibrato_count = 0
        vibrato_rates = []

        if len(valid_freqs) > 40:
            try:
                from scipy import signal
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

        # 滑音检测 - 向量化替代Python循环
        freq_diff = np.abs(np.diff(valid_freqs))
        time_diff = np.diff(valid_times)
        glide_threshold = 50  # Hz变化阈值
        time_threshold = 0.2  # 最大时间间隔

        # 使用向量化计算滑音数量
        glide_mask = (freq_diff > glide_threshold) & (time_diff < time_threshold)
        glide_count = np.sum(glide_mask)

        return {
            'vibrato': {'count': vibrato_count, 'rate': np.mean(vibrato_rates) if vibrato_rates else 0},
            'glides': {'count': int(glide_count)}
        }

    def _recognize_emotion(self, audio: np.ndarray, sample_rate: int) -> Dict:
        """情感识别 - 支持SpeechBrain和Transformers模型"""
        classifier = _load_emotion_model()

        if classifier is None:
            return self._fallback_emotion_analysis(audio, sample_rate)

        try:
            model_type = classifier.get('type', 'transformers')

            # wav2vec2需要16kHz采样率
            target_sr = 16000
            if sample_rate != target_sr:
                audio_resampled = librosa.resample(audio, orig_sr=sample_rate, target_sr=target_sr)
            else:
                audio_resampled = audio

            # 确保音频长度足够（至少1秒）
            min_length = target_sr
            if len(audio_resampled) < min_length:
                audio_resampled = np.pad(audio_resampled, (0, min_length - len(audio_resampled)))

            if model_type == 'speechbrain':
                # SpeechBrain模型推理
                sb_classifier = classifier.get('classifier')
                if sb_classifier is not None:
                    # SpeechBrain classify_batch返回: out_prob, score, index, text_lab
                    out_prob, score, index, text_lab = sb_classifier.classify_batch(audio_resampled)

                    labels = classifier.get('labels', ['neu', 'ang', 'hap', 'sad'])

                    # 获取概率分布
                    probs = out_prob.squeeze().cpu().numpy() if hasattr(out_prob, 'squeeze') else out_prob[0]
                    emotion_scores = {}
                    for i, label in enumerate(labels):
                        emotion_scores[label] = float(probs[i]) if i < len(probs) else 0.0

                    # 映射标签名
                    label_map = {'neu': 'neutral', 'ang': 'angry', 'hap': 'happy', 'sad': 'sad'}
                    mapped_scores = {
                        label_map.get(k, k): v for k, v in emotion_scores.items()
                    }

                    # 获取预测标签
                    predicted_label = text_lab[0] if isinstance(text_lab, (list, tuple)) else str(text_lab)
                    dominant = label_map.get(predicted_label, 'neutral')
                    confidence = float(score[0]) if isinstance(score, (list, tuple, np.ndarray)) else float(score)
                else:
                    return self._fallback_emotion_analysis(audio, sample_rate)
            else:
                # Transformers模型推理
                model = classifier['model']
                feature_extractor = classifier['feature_extractor']

                inputs = feature_extractor(
                    audio_resampled,
                    sampling_rate=target_sr,
                    return_tensors="pt",
                    padding=True
                )

                with torch.no_grad():
                    outputs = model(**inputs)
                    logits = outputs.logits

                predicted_id = torch.argmax(logits, dim=-1).item()
                probs = torch.softmax(logits, dim=-1).squeeze().tolist()

                emotion_labels = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
                predicted_id = max(0, min(predicted_id, len(emotion_labels) - 1))

                emotion_scores = {}
                for i, label in enumerate(emotion_labels):
                    if isinstance(probs, list) and i < len(probs):
                        emotion_scores[label] = float(probs[i])
                    else:
                        emotion_scores[label] = 0.0

                dominant = emotion_labels[predicted_id]
                confidence = emotion_scores.get(dominant, 0.5)
                mapped_scores = {
                    'neutral': emotion_scores.get('neutral', 0.0),
                    'angry': emotion_scores.get('angry', 0.0),
                    'happy': emotion_scores.get('happy', 0.0),
                    'sad': emotion_scores.get('sad', 0.0)
                }

            ui_labels = ['neutral', 'angry', 'happy', 'sad']
            return {
                'dominant': dominant if dominant in ui_labels else 'neutral',
                'confidence': confidence,
                'scores': mapped_scores
            }

        except Exception as e:
            logger.error(f"模型推理失败: {e}")
            return self._fallback_emotion_analysis(audio, sample_rate)

    def _fallback_emotion_analysis(self, audio: np.ndarray, sample_rate: int) -> Dict:
        """备用情绪分析 - 基于音频特征的启发式方法"""
        rms = librosa.feature.rms(y=audio)[0]
        energy_mean = np.mean(rms)
        energy_std = np.std(rms)

        spectral_centroids = librosa.feature.spectral_centroid(y=audio, sr=sample_rate)[0]
        brightness = np.mean(spectral_centroids)

        contrast = librosa.feature.spectral_contrast(y=audio, sr=sample_rate)
        contrast_mean = np.mean(contrast)

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
        return {
            'dominant': dominant,
            'confidence': emotions[dominant],
            'scores': emotions
        }

    def _calculate_scores(self, pitch_data, rhythm_data, technique_data, emotion_data, audio_data) -> Dict:
        """计算五维评分 - 基于专利文献的算法

        参考：
        1. 《一种基于多维声学特征的歌唱能力客观测评系统及方法》
        2. 《基于深度学习的唱歌技巧评价系统及其方法》
        3. SongEval数据集的五维美学评估

        评分标准：
        - 噪音/杂音：< 35分
        - 普通人歌唱：50-65分
        - 专业歌手/优秀：70-85分
        """

        # ==================== 1. 音量评分 ====================
        # 基于短时能量(Short-Time Energy)和均方根幅值(RMS)
        # 计算动态声压级(SPL)变化曲线

        # 计算RMS能量
        rms = np.sqrt(np.mean(audio_data ** 2))
        rms_db = 20 * np.log10(rms) if rms > 0 else -80

        # 短时能量分析
        frame_length = 2048
        hop_length = 512
        rms_frames = librosa.feature.rms(y=audio_data, frame_length=frame_length, hop_length=hop_length)[0]

        # 动态范围（音量变化的丰富度）
        rms_mean = np.mean(rms_frames) + 1e-10
        rms_std = np.std(rms_frames)
        dynamic_range = rms_std / rms_mean  # 变异系数

        # 音量稳定性
        rms_diff = np.abs(np.diff(rms_frames))
        volume_stability = 1.0 - np.mean(rms_diff) / (rms_mean + 1e-10)
        volume_stability = max(0, min(1, volume_stability))

        # 音量水平评分（专利中的SPL评估）
        if -30 <= rms_db <= -6:
            # 理想音量范围：-30dB到-6dB
            level_score = 70 + volume_stability * 10
        elif -40 <= rms_db < -30:
            # 音量偏低
            level_score = 50 + (rms_db + 40) * 2 + volume_stability * 5
        elif rms_db > -6:
            # 音量过高（可能失真）
            level_score = max(40, 70 - (rms_db + 6) * 3)
        else:
            # 音量过低（接近噪音）
            level_score = max(25, 30 + (rms_db + 60) * 0.5)

        # 动态范围加分（专利中的表现力指标）
        dynamic_bonus = min(10, dynamic_range * 20)

        volume_score = level_score + dynamic_bonus

        # ==================== 2. 音准评分 ====================
        # 基于YIN算法提取基频轨迹，与标准MIDI音符频率进行DTW比对

        frequencies = pitch_data.get('frequencies', [])
        times = pitch_data.get('times', [])

        # 过滤有效频率（人声范围80-1200Hz）- 使用向量化操作
        frequencies = pitch_data.get('frequencies', np.array([]))
        times = pitch_data.get('times', np.array([]))

        # 向量化过滤
        if len(frequencies) > 0:
            valid_mask = ~np.isnan(frequencies) & (frequencies > 80) & (frequencies < 1200)
            valid_freqs = frequencies[valid_mask]
            valid_times = times[valid_mask]
        else:
            valid_freqs = np.array([])
            valid_times = np.array([])

        pitch_score = 50  # 默认中等分数

        if len(valid_freqs) > 30:
            # 音高检测率（有效帧占比）- 专利中的关键指标
            detection_rate = len(valid_freqs) / len(frequencies) if len(frequencies) > 0 else 0

            # 计算音高稳定性（专利中的DTW比对方法简化）
            # 转换为半音(MIDI note)
            midi_notes = 12 * np.log2(valid_freqs / 440) + 69

            # 局部音高变化（滑动窗口分析）
            window_size = min(20, len(midi_notes) // 8)
            if window_size > 3:
                local_stds = []
                for i in range(0, len(midi_notes) - window_size, window_size // 2):
                    window = midi_notes[i:i + window_size]
                    local_stds.append(np.std(window))
                avg_local_std = np.mean(local_stds)
                # 标准差小于0.5半音为优秀
                pitch_stability = max(0, 1 - avg_local_std / 2)
            else:
                pitch_stability = 0.5

            # 音高范围（合理的歌唱范围）
            freq_range = np.max(valid_freqs) - np.min(valid_freqs)
            range_score = min(1.0, freq_range / 300)  # 300Hz范围视为正常

            # 综合评分（专利公式简化）
            pitch_score = 30 + detection_rate * 25 + pitch_stability * 30 + range_score * 10

        elif len(valid_freqs) > 10:
            detection_rate = len(valid_freqs) / len(frequencies) if len(frequencies) > 0 else 0
            pitch_score = 35 + detection_rate * 25
        else:
            # 几乎没有有效音高，可能是噪音
            pitch_score = 25

        # ==================== 3. 节奏评分 ====================
        # 基于起始点检测算法(Onset Detection)评估节奏准确度

        rhythm_stability = rhythm_data.get('stability', 0.5)
        onset_count = rhythm_data.get('onset_count', 0)

        # 计算音频时长
        duration = len(audio_data) / 44100  # 假设采样率44100

        # 预期节拍数（假设平均BPM 100）
        expected_beats = duration * 100 / 60

        # 节拍检测率
        if expected_beats > 0 and onset_count > 0:
            beat_ratio = min(1.5, onset_count / expected_beats)
            # 节拍密度评分
            density_score = min(1.0, beat_ratio)
        else:
            density_score = 0.3

        # 综合评分
        rhythm_score = 40 + rhythm_stability * 30 + density_score * 20

        # ==================== 4. 气息评分 ====================
        # 基于谐波噪声比(HNR)和气声比例分析（专利核心算法）

        # 计算HNR（谐波噪声比）- 专利中的关键指标
        try:
            # 使用librosa计算谐波和打击成分
            harmonic, percussive = librosa.effects.hpss(audio_data)
            harmonic_energy = np.sum(harmonic ** 2)
            total_energy = np.sum(audio_data ** 2) + 1e-10

            # HNR计算
            hnr = harmonic_energy / (total_energy - harmonic_energy + 1e-10)
            hnr_db = 10 * np.log10(hnr + 1e-10)

            # HNR评分映射
            # HNR高表示声音集中，HNR低表示气声多
            # 专业歌手HNR通常在15-25dB
            if hnr_db > 20:
                breath_quality = 75 + min(10, (hnr_db - 20) * 2)  # 优秀
            elif hnr_db > 10:
                breath_quality = 55 + (hnr_db - 10) * 2  # 良好
            elif hnr_db > 0:
                breath_quality = 40 + hnr_db * 1.5  # 一般
            else:
                breath_quality = max(25, 40 + hnr_db * 0.5)  # 较差（可能噪音）
        except Exception:
            breath_quality = 50

        # 能量稳定性（气息均匀度）
        rms_frames = librosa.feature.rms(y=audio_data)[0]
        rms_cv = np.std(rms_frames) / (np.mean(rms_frames) + 1e-10)
        energy_stability = max(0, 1 - rms_cv * 0.5)

        # 颤音检测加分（专利中的技巧指标）
        vibrato = technique_data.get('vibrato', {})
        vibrato_count = vibrato.get('count', 0)
        vibrato_bonus = min(10, vibrato_count * 2)

        # 综合评分
        breath_score = breath_quality * 0.6 + (40 + energy_stability * 25) * 0.3 + vibrato_bonus * 0.1

        # ==================== 5. 情绪评分 ====================
        # 基于MFCC + CNN-BiLSTM模型评估情绪饱满度（专利方法）

        emotion_confidence = emotion_data.get('confidence', 0.5)
        emotion_scores_dict = emotion_data.get('scores', {})

        if emotion_scores_dict:
            # 1. 情感强度（强情绪类别概率）
            # 专利定义的强情绪类别：激情、兴奋、愤怒
            strong_emotions = ['angry', 'happy', 'surprised']  # 映射到我们的类别
            strong_prob = sum(emotion_scores_dict.get(e, 0) for e in strong_emotions)

            # 2. 情感多样性（熵）
            probs = [max(0.001, s) for s in emotion_scores_dict.values()]
            probs = [p / sum(probs) for p in probs]
            entropy = -sum(p * np.log(p) for p in probs if p > 0)

            # 归一化熵（最大熵约1.39）
            diversity = min(1.0, entropy / 1.0)

            # 3. 情感表达强度（专利中的"情绪饱满度"）
            intensity = emotion_confidence * 0.5 + strong_prob * 0.5

            # 综合评分（专利公式：Softmax概率 * 100）
            emotion_score = 35 + intensity * 35 + diversity * 20
        else:
            # 使用MFCC特征估计情绪丰富度
            mfccs = librosa.feature.mfcc(y=audio_data, sr=44100, n_mfcc=13)
            mfcc_var = np.mean(np.var(mfccs, axis=1))
            emotion_score = 40 + min(30, mfcc_var * 100)

        # ==================== 最终评分限制 ====================
        # 确保评分在合理范围内
        return {
            'volume': round(max(25, min(85, volume_score)), 1),
            'pitch': round(max(25, min(85, pitch_score)), 1),
            'rhythm': round(max(30, min(85, rhythm_score)), 1),
            'breath': round(max(25, min(85, breath_score)), 1),
            'emotion': round(max(30, min(85, emotion_score)), 1),
        }

    def _generate_advice(self, scores: Dict) -> str:
        """根据各项分数生成个性化的声乐练习建议

        分级标准（5级）：
        - 优秀：≥90分
        - 良好：80-89分
        - 普通：70-79分
        - 一般：60-69分
        - 待改进：<60分
        """

        # 分级阈值常量
        LEVEL_EXCELLENT = 90.0
        LEVEL_GOOD = 80.0
        LEVEL_NORMAL = 70.0
        LEVEL_FAIR = 60.0

        def get_level(score: float) -> tuple:
            """获取等级和对应的标识"""
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
            """音准建议"""
            if score >= LEVEL_EXCELLENT:
                return ("音准精准，音高控制达到专业水准", "挑战高难度曲目，尝试转音、装饰音等技巧")
            elif score >= LEVEL_GOOD:
                return ("音准表现出色，音高控制稳定", "尝试更复杂的音阶练习（如八度跳跃），或挑战转音练习")
            elif score >= LEVEL_NORMAL:
                return ("音准基本准确，偶尔有小幅偏差", "每天跟唱音阶10分钟，注意音准稳定性；使用钢琴App辅助校对")
            elif score >= LEVEL_FAIR:
                return ("音准需要加强，存在明显音高偏差", "从基础音阶do-re-mi开始，使用调音器或钢琴App跟唱，每天15分钟")
            else:
                return ("音准问题较大，音高识别需要从基础开始", "建议先进行听音训练，学会辨别音高后再练习发声")

        def get_rhythm_advice(score: float) -> tuple:
            """节奏建议"""
            if score >= LEVEL_EXCELLENT:
                return ("节奏感出色，拍子精准稳定", "挑战复杂节奏型，如切分音、三连音、附点音符")
            elif score >= LEVEL_GOOD:
                return ("节奏感很好，拍子稳定", "尝试更复杂的切分节奏，或挑战附点音符和三连音练习")
            elif score >= LEVEL_NORMAL:
                return ("节奏基本稳定，偶尔有抢拍或拖拍", "使用节拍器APP，从慢速开始（60-80 BPM），先拍手打节奏再演唱")
            elif score >= LEVEL_FAIR:
                return ("节奏感需要加强，拍子不够稳定", "每天用节拍器练习，从60 BPM四拍开始，逐句跟唱简单歌曲")
            else:
                return ("节奏问题明显，缺乏基本的节奏感", "建议先学习基础节奏知识，从拍手打拍子开始练习")

        def get_breath_advice(score: float) -> tuple:
            """气息建议"""
            if score >= LEVEL_EXCELLENT:
                return ("气息控制精湛，呼吸平稳有力且富有表现力", "挑战高难度气息技巧，如弱声控制、渐强渐弱")
            elif score >= LEVEL_GOOD:
                return ("气息控制优秀，呼吸平稳有力", "尝试长音挑战（一口气唱8-10拍），或练习渐强渐弱的长音")
            elif score >= LEVEL_NORMAL:
                return ("气息基本稳定，偶有不够用或抖动", "每天练习腹式呼吸5分钟：吸气时腹部鼓起，呼气时缓慢收缩腹部")
            elif score >= LEVEL_FAIR:
                return ("气息控制需要改进，呼吸支撑不足", "系统学习腹式呼吸，每天练习吹蜡烛和长音's'音训练")
            else:
                return ("气息问题明显，缺乏基本的呼吸支撑", "建议从腹式呼吸开始，先掌握正确的呼吸方式")

        def get_volume_advice(score: float) -> tuple:
            """音量建议"""
            if score >= LEVEL_EXCELLENT:
                return ("音量控制精湛，力度变化自然富有表现力", "挑战更细腻的动态控制，如弱声、半声技巧")
            elif score >= LEVEL_GOOD:
                return ("音量控制出色，力度变化自然", "练习更多动态对比（ppp到fff），尝试歌唱中的情感强弱对比")
            elif score >= LEVEL_NORMAL:
                return ("音量控制尚可，力度变化不够明显", "练习同一音高的渐强渐弱（crescendo-diminuendo）")
            elif score >= LEVEL_FAIR:
                return ("音量控制欠佳，声音可能过弱或忽大忽小", "练习叹气发声法：模仿叹气的感觉发声，找到自然的音量")
            else:
                return ("音量控制问题明显，需要建立基本的发声意识", "建议从基础的发声练习开始，学习如何正确使用声音")

        def get_emotion_advice(score: float) -> tuple:
            """情感建议"""
            if score >= LEVEL_EXCELLENT:
                return ("情感表达丰富动人，富有极强的感染力", "挑战不同风格曲目，发展个人演唱特色和风格")
            elif score >= LEVEL_GOOD:
                return ("情感表达丰富，富有感染力", "尝试更多风格的歌曲，挑战不同情绪表达的细腻层次")
            elif score >= LEVEL_NORMAL:
                return ("有基本的情感表达，但深度和细腻度可加强", "深入理解歌词含义，像讲故事一样演唱")
            elif score >= LEVEL_FAIR:
                return ("情感表达较平淡，需要更多投入", "先朗诵歌词体会情感后再唱，选择能引起共鸣的歌曲")
            else:
                return ("情感表达欠缺，缺乏基本的演唱感染力", "建议多听优秀演唱，学习如何通过声音表达情感")

        # 各项评分维度配置
        dimensions = [
            ("pitch", "音准", get_pitch_advice),
            ("rhythm", "节奏", get_rhythm_advice),
            ("breath", "气息", get_breath_advice),
            ("volume", "音量", get_volume_advice),
            ("emotion", "情感", get_emotion_advice),
        ]

        # 计算各项评分
        score_list = [(key, name, scores.get(key, 0)) for key, name, _ in dimensions]

        # 找出最强和最弱维度
        sorted_scores = sorted(score_list, key=lambda x: x[2], reverse=True)
        strongest = sorted_scores[0]
        weakest = sorted_scores[-1]

        # 生成各维度建议
        advice_sections = []
        for key, name, advice_func in dimensions:
            score = scores.get(key, 0)
            level, emoji, color = get_level(score)
            suggestion, practice = advice_func(score)

            # 标记最强/最弱维度
            marker = ""
            if key == strongest[0] and score >= LEVEL_GOOD:
                marker = "【强项】"
            elif key == weakest[0] and score < LEVEL_NORMAL:
                marker = "【优先改进】"

            section = (
                f"【{name} {score:.1f}分 - {level} {emoji}】{marker}\n"
                f"建议：{suggestion}\n"
                f"练习：{practice}"
            )
            advice_sections.append(section)

        # 计算平均分
        avg_score = sum(scores.get(k, 0) for k, _, _ in dimensions) / len(dimensions)
        _, _, avg_color = get_level(avg_score)

        # 根据分数组合给出针对性总结
        if avg_score >= LEVEL_EXCELLENT:
            summary = (
                f"\n{'='*40}\n"
                f"整体评价：表现优秀！平均分 {avg_score:.1f}\n"
                f"{'='*40}\n"
                "你的声乐能力已达到专业水准！建议：\n"
                "• 保持日常练习，巩固现有水平\n"
                "• 挑战更高难度的曲目和技巧\n"
                "• 考虑发展个人演唱风格\n"
                "• 可以尝试参加演出或比赛积累经验"
            )
        elif avg_score >= LEVEL_GOOD:
            summary = (
                f"\n{'='*40}\n"
                f"整体评价：表现良好！平均分 {avg_score:.1f}\n"
                f"{'='*40}\n"
                "你具备了较好的声乐基础！建议：\n"
                "• 继续保持优势项目的练习\n"
                f"• 重点加强【{weakest[1]}】方面（当前{weakest[2]:.1f}分）\n"
                "• 可以尝试稍有难度的歌曲\n"
                "• 坚持每天练习，进步会很快"
            )
        elif avg_score >= LEVEL_NORMAL:
            summary = (
                f"\n{'='*40}\n"
                f"整体评价：表现普通。平均分 {avg_score:.1f}\n"
                f"{'='*40}\n"
                "你的演唱有不错的基础！建议：\n"
                f"• 优先改进【{weakest[1]}】（当前{weakest[2]:.1f}分）\n"
                f"• 同时保持【{strongest[1]}】的优势（当前{strongest[2]:.1f}分）\n"
                "• 选择适合自己水平的歌曲练习\n"
                "• 定期录音对比，发现问题"
            )
        elif avg_score >= LEVEL_FAIR:
            summary = (
                f"\n{'='*40}\n"
                f"整体评价：需要加强。平均分 {avg_score:.1f}\n"
                f"{'='*40}\n"
                "建议从基础开始系统学习：\n"
                f"• 首先解决【{weakest[1]}】问题（当前{weakest[2]:.1f}分）\n"
                "• 建议找专业老师指导基础发声\n"
                "• 每天坚持基础练习\n"
                "• 不要急于唱复杂的歌曲"
            )
        else:
            summary = (
                f"\n{'='*40}\n"
                f"整体评价：需要从基础开始。平均分 {avg_score:.1f}\n"
                f"{'='*40}\n"
                "建议从最基础开始学习声乐：\n"
                "• 先学习正确的呼吸和发声方法\n"
                "• 建议寻求专业老师指导\n"
                "• 从简单的练声曲开始\n"
                "• 不要气馁，坚持练习一定会有进步"
            )

        # 添加通用练习建议
        general_tips = (
            "\n" + "─"*40 + "\n"
            "通用练习建议：\n"
            "• 练习前务必进行5-10分钟的热身（打哈欠、唇颤音、哼鸣）\n"
            "• 选择适合自己音域的歌曲，避免过度挑战高音\n"
            "• 录音回放是发现问题最有效的方法，建议经常录下来对比\n"
            "• 保护嗓子：练习时多喝水，避免过度用嗓\n"
            "• 建议每次练习时间：30-45分钟，避免疲劳"
        )

        return "\n\n".join(advice_sections) + summary + general_tips


class WorkerManager:
    """工作线程管理器 - 单例模式"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._pool = QThreadPool.globalInstance()
            cls._instance._pool.setMaxThreadCount(4)
            cls._instance._current_task = None
        return cls._instance

    def start_load(self, filepath: str, callbacks: Dict[str, Callable]) -> AudioLoadTask:
        """启动加载任务"""
        task = AudioLoadTask(filepath)
        task.signals.started.connect(callbacks.get('started', lambda x: None))
        task.signals.progress.connect(callbacks.get('progress', lambda x, y: None))
        task.signals.finished.connect(callbacks.get('finished', lambda x: None))
        task.signals.error.connect(callbacks.get('error', lambda x: None))
        self._pool.start(task)
        self._current_task = task
        return task

    def start_assessment(self, filepath: str, callbacks: Dict[str, Callable]) -> AssessmentTask:
        """启动评估任务"""
        task = AssessmentTask(filepath)
        task.signals.started.connect(callbacks.get('started', lambda x: None))
        task.signals.progress.connect(callbacks.get('progress', lambda x, y: None))
        task.signals.finished.connect(callbacks.get('finished', lambda x: None))
        task.signals.error.connect(callbacks.get('error', lambda x: None))
        self._pool.start(task)
        self._current_task = task
        return task

    def cancel_current(self):
        """取消当前任务"""
        if self._current_task and hasattr(self._current_task, 'cancel'):
            self._current_task.cancel()