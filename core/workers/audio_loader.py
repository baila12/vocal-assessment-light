"""
音频加载任务

异步加载音频文件并提取基本信息
"""
from PySide6.QtCore import QRunnable
from pathlib import Path
from typing import Dict
import numpy as np
import librosa
import soundfile as sf
import logging

from .signals import WorkerSignals
from .cache import get_audio_cache

logger = logging.getLogger(__name__)


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
            cache = get_audio_cache()
            cached = cache.get(self.filepath)
            if cached is not None:
                audio_data, sample_rate = cached
                logger.debug("使用缓存音频数据")
            else:
                audio_data, sample_rate = librosa.load(self.filepath, sr=None, mono=True)
                cache.set(self.filepath, audio_data, sample_rate)

            self.signals.progress.emit("分析参数", 50)

            # 3. 技术参数
            duration = len(audio_data) / sample_rate
            minutes = int(duration // 60)
            seconds = int(duration % 60)

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

            # 4. 音量信息
            volume_info = self._compute_volume_info(audio_data)

            self.signals.progress.emit("分析音高", 85)

            # 5. 音高统计
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

        # 动态范围计算
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
