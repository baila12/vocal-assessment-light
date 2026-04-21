"""
音频分析器 - 提取音频详细信息
包含: 基本信息、技术参数、音量信息、音高统计
"""
import numpy as np
import librosa
from pathlib import Path
from typing import Dict, Optional
import soundfile as sf


class AudioAnalyzer:
    """音频信息分析器"""

    SUPPORTED_FORMATS = {'.wav', '.mp3', '.flac', '.m4a', '.ogg', '.aac'}

    def __init__(self):
        self.audio_data = None
        self.sample_rate = None
        self.filepath = None

    def analyze(self, filepath: str) -> Dict:
        """全面分析音频文件"""
        self.filepath = filepath
        path = Path(filepath)

        result = {
            'basic_info': self._get_basic_info(path),
            'technical_params': None,
            'volume_info': None,
            'pitch_stats': None,
            'valid': False,
            'error': None
        }

        try:
            self.audio_data, self.sample_rate = librosa.load(filepath, sr=None, mono=True)
            info = sf.info(filepath)
            result['technical_params'] = self._get_technical_params(info)
            result['volume_info'] = self._get_volume_info()
            result['pitch_stats'] = self._get_pitch_stats()
            result['valid'] = True
        except Exception as e:
            result['error'] = str(e)

        return result

    def _get_basic_info(self, path: Path) -> Dict:
        """获取基本信息"""
        return {
            'filename': path.name,
            'filepath': str(path),
            'format': path.suffix.upper().replace('.', ''),
            'size_mb': path.stat().st_size / (1024 * 1024) if path.exists() else 0
        }

    def _get_technical_params(self, info) -> Dict:
        """获取技术参数"""
        duration_seconds = info.duration
        minutes = int(duration_seconds // 60)
        seconds = int(duration_seconds % 60)
        return {
            'sample_rate': info.samplerate,
            'channels': info.channels,
            'channel_name': '单声道' if info.channels == 1 else '立体声',
            'duration_seconds': duration_seconds,
            'duration_formatted': f"{minutes:02d}:{seconds:02d}",
            'bit_depth': getattr(info, 'subtype', '未知')
        }

    def _get_volume_info(self) -> Dict:
        """获取音量信息"""
        if self.audio_data is None:
            return {'avg_db': -80, 'peak_db': -80, 'dynamic_range': 0}
        rms = np.sqrt(np.mean(self.audio_data ** 2))
        avg_db = 20 * np.log10(rms) if rms > 0 else -80
        peak = np.max(np.abs(self.audio_data))
        peak_db = 20 * np.log10(peak) if peak > 0 else -80
        rms_per_frame = librosa.feature.rms(y=self.audio_data)[0]
        min_rms = np.min(rms_per_frame[rms_per_frame > 0]) if np.any(rms_per_frame > 0) else 1e-10
        max_rms = np.max(rms_per_frame)
        dynamic_range = 20 * np.log10(max_rms / min_rms)
        return {'avg_db': float(avg_db), 'peak_db': float(peak_db), 'dynamic_range': float(dynamic_range)}

    def _get_pitch_stats(self) -> Dict:
        """获取音高统计"""
        if self.audio_data is None:
            return {'valid_frames': 0, 'total_frames': 0, 'min_freq': 0, 'max_freq': 0}
        try:
            hop_length = 512
            f0, voiced_flag, _ = librosa.pyin(
                self.audio_data, fmin=librosa.note_to_hz('C2'),
                fmax=librosa.note_to_hz('C6'), sr=self.sample_rate, hop_length=hop_length
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
                'min_freq': min_freq, 'max_freq': max_freq,
                'min_note': min_note, 'max_note': max_note
            }
        except Exception as e:
            return {'valid_frames': 0, 'total_frames': 0, 'min_freq': 0, 'max_freq': 0, 'error': str(e)}

    def get_display_info(self, filepath: str) -> Dict:
        """获取用于显示的信息（格式化后）"""
        raw_info = self.analyze(filepath)
        if not raw_info['valid']:
            return {'error': raw_info['error'], 'filename': raw_info['basic_info']['filename']}
        basic = raw_info['basic_info']
        tech = raw_info['technical_params']
        vol = raw_info['volume_info']
        pitch = raw_info['pitch_stats']
        return {
            'filename': basic['filename'], 'format': basic['format'],
            'duration': tech['duration_formatted'],
            'sample_rate': f"{tech['sample_rate']} Hz",
            'channels': tech['channel_name'],
            'avg_volume': f"{vol['avg_db']:.1f} dB",
            'peak_volume': f"{vol['peak_db']:.1f} dB",
            'dynamic_range': f"{vol['dynamic_range']:.1f} dB",
            'pitch_frames': f"{pitch['valid_frames']} / {pitch['total_frames']}",
            'pitch_range': f"{pitch['min_note']} - {pitch['max_note']}"
        }