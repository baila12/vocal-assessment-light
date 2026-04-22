"""
音频分析服务
负责音频特征提取和分析

设计原则：
- 单一职责：只负责音频分析
- 依赖注入：通过构造函数传入依赖
- 返回 DTO：统一的数据传输对象
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, List
import traceback

import librosa
import numpy as np
from scipy import signal

from config import Config
from services.audio_features_service import AudioFeaturesService, AudioFeaturesResult

# 深度学习服务 v5.0
from services.dl_services import VoiceQualityDetector, SingingStyleClassifier, SelfReferencedDTW

# 风格自适应评分 v5.1
from services.style_aware_scorer import StyleAnalyzer, MusicStyle


@dataclass
class WaveformData:
    """波形数据 DTO"""
    times: List[float] = field(default_factory=list)
    amplitudes: List[float] = field(default_factory=list)


@dataclass
class PitchCurveData:
    """音高曲线数据 DTO"""
    times: List[float] = field(default_factory=list)
    frequencies: List[float] = field(default_factory=list)
    confidence: List[float] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class AudioAnalysisResult:
    """音频分析结果 DTO"""
    success: bool
    filepath: str
    filename: str
    duration: float
    sample_rate: int
    file_size: float

    # 音量信息
    volume_info: Dict = field(default_factory=dict)

    # 音高信息
    pitch_info: Dict = field(default_factory=dict)

    # 节奏信息
    rhythm_info: Dict = field(default_factory=dict)

    # 波形数据
    waveform: Optional[WaveformData] = None

    # 音高曲线
    pitch_curve: Optional[PitchCurveData] = None

    # Log-Mel 频谱图数据 (用于可视化)
    log_mel_spectrogram: Optional[Dict] = None

    # RMS 短时能量数据 (用于可视化)
    rms_energy: Optional[Dict] = None

    # 中间计算结果（供评分服务使用）
    _audio_data: Optional[np.ndarray] = field(default=None, repr=False)
    _valid_freqs: Optional[np.ndarray] = field(default=None, repr=False)
    _f0: Optional[np.ndarray] = field(default=None, repr=False)
    _pitch_stability: float = 0.5
    _tonal_clarity: float = 0.5
    _voice_clarity: float = 0.5
    _vibrato_count: int = 0

    # 高级特征提取结果 v4.0
    _advanced_features: Optional[AudioFeaturesResult] = field(default=None, repr=False)

    # 深度学习分析结果 v5.0
    _voice_quality: Optional[Dict] = field(default=None, repr=False)  # 人声质量检测结果
    _singing_style: Optional[Dict] = field(default=None, repr=False)  # 唱法识别结果
    _pitch_stability_dl: Optional[Dict] = field(default=None, repr=False)  # 自参照DTW结果

    # 风格自适应评分 v5.1
    _music_style: Optional[str] = field(default=None, repr=False)  # 音乐风格 (pop/folk/rock等)
    _style_confidence: float = 0.0  # 风格分类置信度
    _music_mood: Optional[str] = field(default=None, repr=False)  # 音乐情绪
    _style_profile: Optional['StyleProfile'] = field(default=None, repr=False)  # 风格配置档案

    # 错误信息
    error: Optional[str] = None
    traceback: Optional[str] = None


class AudioService:
    """
    音频分析服务

    职责：
    - 加载音频文件
    - 提取音频特征
    - 计算中间指标

    不负责：
    - 评分计算（由 ScoreService 负责）
    - 建议生成（由 AdviceService 负责）
    """

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self._hop_length = self.config.AUDIO_HOP_LENGTH
        self._frame_length = self.config.AUDIO_FRAME_LENGTH
        # 高级特征提取服务 v4.0
        self._features_service = AudioFeaturesService(
            sample_rate=self.config.AUDIO_SAMPLE_RATE,
            hop_length=self._hop_length
        )
        # 深度学习服务 v5.0（延迟初始化）
        self._voice_quality_detector = None
        self._style_classifier = None
        self._self_ref_dtw = None
        # 风格分析器 v5.1（延迟初始化）
        self._style_analyzer = None

    def analyze(
        self,
        filepath: str,
        include_waveform: bool = True,
        include_pitch_curve: bool = True,
        quick_mode: bool = False
    ) -> AudioAnalysisResult:
        """
        分析音频文件

        Args:
            filepath: 音频文件路径
            include_waveform: 是否包含波形数据
            include_pitch_curve: 是否包含音高曲线
            quick_mode: 快速模式（跳过耗时DL分析）

        Returns:
            AudioAnalysisResult: 分析结果
        """
        try:
            # 加载音频
            audio_data, sample_rate = librosa.load(filepath, sr=None, mono=True)
            duration = len(audio_data) / sample_rate
            file_size = Path(filepath).stat().st_size / (1024 * 1024)
            filename = Path(filepath).name

            # 初始化结果
            result = AudioAnalysisResult(
                success=True,
                filepath=filepath,
                filename=filename,
                duration=duration,
                sample_rate=sample_rate,
                file_size=file_size
            )

            # ========== 性能优化：降采样到16kHz ==========
            # 人声基频范围65-1047Hz，16kHz采样率足够（奈奎斯特频率8kHz）
            TARGET_SR = 16000
            original_sr = sample_rate
            if sample_rate > TARGET_SR:
                audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=TARGET_SR)
                sample_rate = TARGET_SR

            # 存储原始数据供后续使用
            result._audio_data = audio_data

            # 音量分析
            result.volume_info = self._analyze_volume(audio_data)

            # 音高检测（使用更快的yin算法）
            pitch_result = self._analyze_pitch(audio_data, sample_rate)
            result.pitch_info = pitch_result['info']
            result._valid_freqs = pitch_result['valid_freqs']
            result._f0 = pitch_result['f0']
            result._pitch_stability = pitch_result['stability']

            # Chroma 特征分析（简化版，减少计算量）
            result._tonal_clarity = self._analyze_tonal_clarity_fast(audio_data, sample_rate)

            # 节奏分析
            result.rhythm_info = self._analyze_rhythm(audio_data, sample_rate)

            # 人声质量评估
            result._voice_clarity = self._analyze_voice_clarity(audio_data)

            # 颤音检测
            result._vibrato_count = self._detect_vibrato(
                pitch_result['valid_freqs'], sample_rate
            )

            # 波形数据
            if include_waveform:
                result.waveform = self._get_waveform_data(audio_data, sample_rate)

            # 音高曲线
            if include_pitch_curve:
                result.pitch_curve = self._get_pitch_curve_data(
                    audio_data, sample_rate
                )

            # Log-Mel 频谱图数据
            result.log_mel_spectrogram = self._compute_log_mel_spectrogram(
                audio_data, sample_rate
            )

            # RMS 短时能量数据
            result.rms_energy = self._compute_rms_energy(
                audio_data, sample_rate
            )

            # 高级特征提取 v4.1（传递f0用于气息评估）
            result._advanced_features = self._features_service.extract_all_features(
                audio_data, result._f0, singing_style='pop'
            )

            # ========== 深度学习分析 v5.0 ==========
            # 快速模式跳过耗时DL分析
            if not quick_mode:
                # 人声质量检测
                voice_quality_result = self._run_voice_quality_detection(filepath)
                if voice_quality_result:
                    result._voice_quality = {
                        'has_voice': voice_quality_result.has_voice,
                        'voice_ratio': voice_quality_result.voice_ratio,
                        'is_valid': voice_quality_result.is_valid_for_analysis,
                        'confidence': voice_quality_result.confidence,
                        'method': voice_quality_result.method
                    }
                    # 如果音频不适合分析，设置警告
                    if not voice_quality_result.is_valid_for_analysis:
                        result.pitch_info['warning'] = 'Audio may not be suitable for vocal analysis'

                # 唱法识别
                style_result = self._run_style_classification(filepath)
                singing_style = 'pop'  # 默认
                if style_result:
                    result._singing_style = {
                        'style': style_result.style.value,
                        'confidence': style_result.confidence,
                        'probabilities': style_result.probabilities,
                        'method': style_result.method
                    }
                    singing_style = style_result.style.value
                    # 使用识别的风格重新提取高级特征
                    result._advanced_features = self._features_service.extract_all_features(
                        audio_data, result._f0, singing_style=singing_style
                    )

                # 自参照DTW音准评估（仅对有效人声）
                if result._voice_quality and result._voice_quality.get('is_valid', True):
                    dtw_result = self._run_self_referenced_dtw(filepath)
                    if dtw_result:
                        result._pitch_stability_dl = {
                            'overall_stability': dtw_result.overall_stability,
                            'stable_note_ratio': dtw_result.stable_note_ratio,
                            'avg_deviation_cents': dtw_result.avg_deviation_cents,
                            'intentional_variations': dtw_result.intentional_variations,
                            'unintentional_drifts': dtw_result.unintentional_drifts,
                            'notes_count': len(dtw_result.notes),
                            'method': dtw_result.method
                        }

                # ========== 音乐风格分析 v5.1 ==========
                # 使用深度学习模型分析音乐风格
                style_analysis = self._run_music_style_analysis(filepath)
                if style_analysis:
                    music_style, style_profile, style_features = style_analysis
                    result._music_style = music_style.value
                    result._style_confidence = style_features.get('genre_confidence', 0)
                    result._music_mood = style_features.get('mood', 'unknown')
                    # 存储style_profile供评分服务使用
                    result._style_profile = style_profile

            return result

        except Exception as e:
            return AudioAnalysisResult(
                success=False,
                filepath=filepath,
                filename=Path(filepath).name if Path(filepath).exists() else '',
                duration=0,
                sample_rate=0,
                file_size=0,
                error=str(e),
                traceback=traceback.format_exc()
            )

    def _analyze_volume(self, audio_data: np.ndarray) -> Dict:
        """分析音量信息"""
        rms = np.sqrt(np.mean(audio_data ** 2))
        avg_db = 20 * np.log10(rms) if rms > 0 else -80
        peak = np.max(np.abs(audio_data))
        peak_db = 20 * np.log10(peak) if peak > 0 else -80

        rms_frames = librosa.feature.rms(
            y=audio_data,
            frame_length=self._frame_length,
            hop_length=self._hop_length
        )[0]
        valid_rms = rms_frames[rms_frames > 0]
        dynamic_range = 20 * np.log10(
            np.max(valid_rms) / np.min(valid_rms)
        ) if len(valid_rms) > 0 else 0

        return {
            'avg_db': round(avg_db, 1),
            'peak_db': round(peak_db, 1),
            'dynamic_range': round(dynamic_range, 1)
        }

    def _analyze_pitch(
        self,
        audio_data: np.ndarray,
        sample_rate: int
    ) -> Dict:
        """
        分析音高信息

        性能优化：使用yin算法替代pyin，速度提升约2倍
        yin不返回voiced_flag，需要自行计算
        """
        # 使用yin算法（比pyin快约2倍）
        f0 = librosa.yin(
            audio_data,
            fmin=self.config.PITCH_FMIN,
            fmax=self.config.PITCH_FMAX,
            sr=sample_rate,
            hop_length=self._hop_length
        )

        # yin返回的是频率，nan表示无声
        valid_mask = ~np.isnan(f0) & (f0 > 80) & (f0 < 1200)
        valid_freqs = f0[valid_mask]

        if len(valid_freqs) > 0:
            min_freq = float(np.min(valid_freqs))
            max_freq = float(np.max(valid_freqs))
            min_note = librosa.hz_to_note(min_freq)
            max_note = librosa.hz_to_note(max_freq)
            pitch_stability = self._calculate_pitch_stability(valid_freqs)
        else:
            min_freq, max_freq, min_note, max_note = 0, 0, '--', '--'
            pitch_stability = 0.5

        return {
            'info': {
                'min_freq': round(min_freq, 1),
                'max_freq': round(max_freq, 1),
                'min_note': min_note,
                'max_note': max_note,
                'valid_frames': int(np.sum(valid_mask)),
                'total_frames': int(len(f0)),
                'stability': round(pitch_stability * 100, 1)
            },
            'valid_freqs': valid_freqs,
            'f0': f0,
            'stability': pitch_stability
        }

    def _calculate_pitch_stability(self, valid_freqs: np.ndarray) -> float:
        """计算音高稳定性 - 基于音调直方图方法"""
        if len(valid_freqs) < 20:
            return 0.5

        # 将频率转换为 MIDI 音符
        midi_notes = 12 * np.log2(valid_freqs / 440) + 69

        # 折叠到一个八度内（12 个半音）
        folded_notes = midi_notes % 12

        # 计算音调直方图
        hist, _ = np.histogram(folded_notes, bins=12, range=(0, 12))
        hist_normalized = hist / (np.sum(hist) + 1e-10)

        # 计算熵 - 熵越低表示音高越集中在特定音符上（更稳定）
        entropy = -np.sum(hist_normalized * np.log2(hist_normalized + 1e-10))
        max_entropy = np.log2(12)  # 均匀分布的熵

        # 稳定性 = 1 - 归一化熵
        stability = 1.0 - (entropy / max_entropy)

        return max(0, min(1, stability))

    def _analyze_tonal_clarity(
        self,
        audio_data: np.ndarray,
        sample_rate: int
    ) -> float:
        """分析调性清晰度"""
        y_harmonic = librosa.effects.harmonic(audio_data, margin=8)
        chroma = librosa.feature.chroma_cqt(
            y=y_harmonic,
            sr=sample_rate,
            hop_length=self._hop_length
        )
        chroma_mean = np.mean(chroma, axis=1)
        return np.max(chroma_mean) / (np.mean(chroma_mean) + 1e-10)

    def _analyze_tonal_clarity_fast(
        self,
        audio_data: np.ndarray,
        sample_rate: int
    ) -> float:
        """
        快速调性清晰度分析（简化版）

        使用频谱质心替代chroma特征，避免耗时的CQT计算
        对于评分影响较小，但大幅提升性能
        """
        try:
            # 使用频谱质心作为调性清晰度的代理指标
            # 质心变化小 = 调性稳定
            centroid = librosa.feature.spectral_centroid(
                y=audio_data,
                sr=sample_rate,
                hop_length=self._hop_length
            )[0]

            # 计算质心的稳定性（变异系数的倒数）
            centroid_cv = np.std(centroid) / (np.mean(centroid) + 1e-10)
            clarity = 1.0 / (1.0 + centroid_cv)

            return float(max(0, min(1, clarity)))
        except Exception:
            return 0.5

    def _analyze_rhythm(
        self,
        audio_data: np.ndarray,
        sample_rate: int
    ) -> Dict:
        """分析节奏信息"""
        onset_env = librosa.onset.onset_strength(y=audio_data, sr=sample_rate)
        tempo, beat_frames = librosa.beat.beat_track(
            onset_envelope=onset_env,
            sr=sample_rate
        )
        onset_frames = librosa.onset.onset_detect(
            onset_envelope=onset_env,
            sr=sample_rate
        )
        onset_count = len(onset_frames)

        if len(beat_frames) > 1:
            beat_intervals = np.diff(beat_frames) * self._hop_length / sample_rate
            rhythm_stability = 1.0 - min(
                1.0,
                np.std(beat_intervals) / (np.mean(beat_intervals) + 1e-10)
            )
        else:
            rhythm_stability = 0.5

        return {
            'bpm': round(float(np.atleast_1d(tempo)[0]), 1),
            'stability': round(rhythm_stability * 100, 1),
            'onset_count': onset_count
        }

    def _analyze_voice_clarity(self, audio_data: np.ndarray) -> float:
        """分析人声清晰度"""
        spectral_flatness = librosa.feature.spectral_flatness(y=audio_data)[0]
        return 1.0 - np.mean(spectral_flatness)

    def _detect_vibrato(
        self,
        valid_freqs: np.ndarray,
        sample_rate: int
    ) -> int:
        """检测颤音"""
        vibrato_count = 0
        if len(valid_freqs) < 40:
            return vibrato_count

        try:
            dt = self._hop_length / sample_rate
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
                    vibrato_count = len(peaks)
        except Exception:
            pass

        return vibrato_count

    def _get_waveform_data(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        max_points: int = 2000
    ) -> WaveformData:
        """获取降采样的波形数据"""
        total_samples = len(audio_data)
        if total_samples <= max_points:
            downsampled = audio_data
        else:
            factor = total_samples // max_points
            downsampled = audio_data[::factor]

        times = np.linspace(0, total_samples / sample_rate, len(downsampled))

        return WaveformData(
            times=times.tolist(),
            amplitudes=downsampled.tolist()
        )

    def _get_pitch_curve_data(
        self,
        audio_data: np.ndarray,
        sample_rate: int
    ) -> PitchCurveData:
        """
        获取音高曲线数据

        性能优化：使用yin算法替代pyin
        """
        try:
            f0 = librosa.yin(
                audio_data,
                fmin=librosa.note_to_hz('C2'),
                fmax=librosa.note_to_hz('C6'),
                sr=sample_rate,
                hop_length=self._hop_length
            )

            times = librosa.times_like(f0, sr=sample_rate, hop_length=self._hop_length)
            # yin不返回voiced_flag，用非nan判断
            confidence = (~np.isnan(f0)).astype(float)

            return PitchCurveData(
                times=times.tolist(),
                frequencies=np.where(np.isnan(f0), 0, f0).tolist(),
                confidence=confidence.tolist()
            )
        except Exception as e:
            return PitchCurveData(error=str(e))

    def _compute_log_mel_spectrogram(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        n_mels: int = 64,
        n_fft: int = 2048
    ) -> Dict:
        """
        计算 Log-Mel 频谱图数据

        Args:
            audio_data: 音频数据
            sample_rate: 采样率
            n_mels: 梅尔带数量 (默认 64)
            n_fft: FFT 窗口大小 (默认 2048)

        Returns:
            包含频谱图数据的字典
        """
        try:
            # 计算梅尔频谱图
            mel_spectrogram = librosa.feature.melspectrogram(
                y=audio_data,
                sr=sample_rate,
                n_mels=n_mels,
                n_fft=n_fft,
                hop_length=self._hop_length
            )

            # 转换为对数刻度 (dB)
            log_mel = librosa.power_to_db(mel_spectrogram, ref=np.max)

            # 时间轴
            times = librosa.times_like(log_mel, sr=sample_rate, hop_length=self._hop_length)

            # 频率轴 (梅尔频率)
            mel_frequencies = librosa.mel_frequencies(n_mels=n_mels, fmin=0, fmax=sample_rate/2)

            return {
                'data': log_mel.tolist(),
                'times': times.tolist(),
                'frequencies': mel_frequencies.tolist(),
                'n_mels': n_mels,
                'hop_length': self._hop_length,
                'sample_rate': sample_rate,
                'vmin': -80,
                'vmax': 0
            }
        except Exception as e:
            return {'error': str(e)}

    def _compute_rms_energy(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        frame_length: int = 2048
    ) -> Dict:
        """
        计算短时能量 (RMS)

        Args:
            audio_data: 音频数据
            sample_rate: 采样率
            frame_length: 帧长 (默认 2048)

        Returns:
            包含 RMS 能量数据的字典
        """
        try:
            # 计算 RMS 能量
            rms = librosa.feature.rms(
                y=audio_data,
                frame_length=frame_length,
                hop_length=self._hop_length
            )[0]

            # 时间轴
            times = librosa.times_like(rms, sr=sample_rate, hop_length=self._hop_length)

            return {
                'times': times.tolist(),
                'values': rms.tolist(),
                'frame_length': frame_length,
                'hop_length': self._hop_length,
                'sample_rate': sample_rate,
                'max': float(np.max(rms)),
                'mean': float(np.mean(rms))
            }
        except Exception as e:
            return {'error': str(e)}

    # ========== 深度学习服务辅助方法 v5.0 ==========

    def _get_voice_quality_detector(self):
        """延迟初始化人声质量检测器"""
        if self._voice_quality_detector is None:
            self._voice_quality_detector = VoiceQualityDetector()
        return self._voice_quality_detector

    def _get_style_classifier(self):
        """延迟初始化唱法分类器"""
        if self._style_classifier is None:
            self._style_classifier = SingingStyleClassifier()
        return self._style_classifier

    def _get_self_ref_dtw(self):
        """延迟初始化自参照DTW"""
        if self._self_ref_dtw is None:
            self._self_ref_dtw = SelfReferencedDTW()
        return self._self_ref_dtw

    def _get_style_analyzer(self):
        """延迟初始化风格分析器 v5.1"""
        if self._style_analyzer is None:
            self._style_analyzer = StyleAnalyzer(use_dl=True)
        return self._style_analyzer

    def _run_voice_quality_detection(self, filepath: str):
        """
        运行人声质量检测

        Args:
            filepath: 音频文件路径

        Returns:
            VoiceQualityResult 或 None
        """
        try:
            detector = self._get_voice_quality_detector()
            return detector.detect(filepath)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Voice quality detection failed: {e}")
            return None

    def _run_style_classification(self, filepath: str):
        """
        运行唱法识别

        Args:
            filepath: 音频文件路径

        Returns:
            StyleClassificationResult 或 None
        """
        try:
            classifier = self._get_style_classifier()
            return classifier.classify(filepath)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Style classification failed: {e}")
            return None

    def _run_self_referenced_dtw(self, filepath: str):
        """
        运行自参照DTW音准评估

        Args:
            filepath: 音频文件路径

        Returns:
            SelfReferencedPitchResult 或 None
        """
        try:
            dtw = self._get_self_ref_dtw()
            return dtw.analyze(filepath)
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Self-referenced DTW failed: {e}")
            return None

    def _run_music_style_analysis(self, filepath: str):
        """
        运行音乐风格分析 v5.1

        使用深度学习模型分析音乐风格和情绪

        Args:
            filepath: 音频文件路径

        Returns:
            tuple: (MusicStyle, StyleProfile, style_features) 或 None
        """
        try:
            analyzer = self._get_style_analyzer()
            style, style_features = analyzer.analyze(filepath)
            profile = analyzer.get_style_profile(style)
            return style, profile, style_features
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Music style analysis failed: {e}")
            return None
