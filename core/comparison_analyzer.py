"""
比对分析模块 - 标准音频与待评判音频对比
性能优化：添加特征缓存、向量化计算、采样率统一
"""
import numpy as np
import librosa
from typing import Dict, List, Optional
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)


class ComparisonAnalyzer:
    """音频比对分析器 - 性能优化版"""

    # 目标采样率，统一处理
    TARGET_SAMPLE_RATE = 22050

    def __init__(self):
        self.standard_audio = None
        self.standard_sr = None
        self.target_audio = None
        self.target_sr = None
        # 特征缓存
        self._pitch_cache: Dict[str, np.ndarray] = {}
        self._rhythm_cache: Dict[str, tuple] = {}

    def load_standard(self, filepath: str) -> bool:
        try:
            audio, sr = librosa.load(filepath, sr=self.TARGET_SAMPLE_RATE, mono=True)
            self.standard_audio = audio
            self.standard_sr = sr
            # 清除相关缓存
            self._pitch_cache.pop('standard', None)
            self._rhythm_cache.pop('standard', None)
            return True
        except Exception as e:
            logger.error(f"加载标准音频失败: {e}")
            return False

    def load_target(self, filepath: str) -> bool:
        try:
            audio, sr = librosa.load(filepath, sr=self.TARGET_SAMPLE_RATE, mono=True)
            self.target_audio = audio
            self.target_sr = sr
            # 清除相关缓存
            self._pitch_cache.pop('target', None)
            self._rhythm_cache.pop('target', None)
            return True
        except Exception as e:
            logger.error(f"加载待评判音频失败: {e}")
            return False

    def compare(self, standard_path: str = None, target_path: str = None) -> Dict:
        """对比两个音频"""
        if standard_path and target_path:
            self.load_standard(standard_path)
            self.load_target(target_path)
        if self.standard_audio is None or self.target_audio is None:
            return {'error': '请先加载两个音频文件'}

        result = {
            'pitch_diff': self._compare_pitch(),
            'rhythm_diff': self._compare_rhythm(),
            'volume_diff': self._compare_volume(),
            'overall_diff': None,
            'suggestions': []
        }
        result['overall_diff'] = self._calculate_overall_diff(result)
        result['suggestions'] = self._generate_suggestions(result)
        return result

    def _compare_pitch(self) -> Dict:
        # 使用缓存的音高数据
        std_f0 = self._get_cached_pitch('standard', self.standard_audio, self.standard_sr)
        tgt_f0 = self._get_cached_pitch('target', self.target_audio, self.target_sr)

        min_len = min(len(std_f0), len(tgt_f0))
        std_f0, tgt_f0 = std_f0[:min_len], tgt_f0[:min_len]

        valid_mask = ~np.isnan(std_f0) & ~np.isnan(tgt_f0)
        std_valid, tgt_valid = std_f0[valid_mask], tgt_f0[valid_mask]

        if len(std_valid) == 0:
            return {'avg_diff': 0, 'max_diff': 0, 'diff_points': []}

        # 向量化计算
        freq_diff = np.abs(tgt_valid - std_valid)
        avg_diff, max_diff = np.mean(freq_diff), np.max(freq_diff)

        # 向量化差异点检测
        time_indices = np.where(valid_mask)[0]
        hop_length = 512
        threshold = avg_diff * 2

        # 使用向量化替代循环
        diff_mask = freq_diff > threshold
        diff_time_indices = time_indices[diff_mask]

        diff_points = []
        for i in diff_time_indices[:10]:  # 最多返回10个差异点
            idx = np.where(time_indices == i)[0][0]
            time_sec = i * hop_length / self.standard_sr
            diff_points.append({
                'time': float(time_sec),
                'diff_hz': float(freq_diff[idx]),
                'direction': '偏高' if tgt_valid[idx] > std_valid[idx] else '偏低'
            })

        return {'avg_diff': float(avg_diff), 'max_diff': float(max_diff), 'diff_points': diff_points}

    def _get_cached_pitch(self, key: str, audio: np.ndarray, sr: int) -> np.ndarray:
        """获取缓存的音高数据"""
        if key not in self._pitch_cache:
            self._pitch_cache[key] = self._extract_pitch(audio, sr)
        return self._pitch_cache[key]

    def _compare_rhythm(self) -> Dict:
        # 使用缓存的节奏数据
        std_tempo = self._get_cached_rhythm('standard', self.standard_audio, self.standard_sr)
        tgt_tempo = self._get_cached_rhythm('target', self.target_audio, self.target_sr)

        bpm_diff = abs(tgt_tempo - std_tempo)
        if tgt_tempo > std_tempo + 5:
            direction = "偏快"
        elif tgt_tempo < std_tempo - 5:
            direction = "偏慢"
        else:
            direction = "基本一致"
        return {'standard_bpm': float(std_tempo), 'target_bpm': float(tgt_tempo),
                'bpm_diff': float(bpm_diff), 'direction': direction}

    def _get_cached_rhythm(self, key: str, audio: np.ndarray, sr: int) -> float:
        """获取缓存的节奏数据"""
        if key not in self._rhythm_cache:
            tempo, _ = librosa.beat.beat_track(y=audio, sr=sr)
            self._rhythm_cache[key] = float(tempo)
        return self._rhythm_cache[key]

    def _compare_volume(self) -> Dict:
        std_rms = np.sqrt(np.mean(self.standard_audio ** 2))
        tgt_rms = np.sqrt(np.mean(self.target_audio ** 2))
        std_db = 20 * np.log10(std_rms) if std_rms > 0 else -80
        tgt_db = 20 * np.log10(tgt_rms) if tgt_rms > 0 else -80
        db_diff = tgt_db - std_db
        if db_diff > 3:
            direction = "偏大"
        elif db_diff < -3:
            direction = "偏小"
        else:
            direction = "基本一致"
        return {'standard_db': float(std_db), 'target_db': float(tgt_db),
                'db_diff': float(db_diff), 'direction': direction}

    def _extract_pitch(self, audio: np.ndarray, sr: int) -> np.ndarray:
        try:
            f0, _, _ = librosa.pyin(audio, fmin=librosa.note_to_hz('C2'),
                                    fmax=librosa.note_to_hz('C6'), sr=sr, hop_length=512)
            return f0
        except Exception as e:
            logger.warning(f"音高提取失败: {e}")
            return np.array([])

    def _calculate_overall_diff(self, result: Dict) -> float:
        pitch_score = max(0, 100 - result['pitch_diff']['avg_diff'] / 2)
        rhythm_score = max(0, 100 - result['rhythm_diff']['bpm_diff'] / 2)
        volume_score = max(0, 100 - abs(result['volume_diff']['db_diff']) / 0.5)
        return float((pitch_score + rhythm_score + volume_score) / 3)

    def _generate_suggestions(self, result: Dict) -> List[str]:
        suggestions = []
        pitch_diff = result['pitch_diff']
        if pitch_diff['diff_points']:
            first_point = pitch_diff['diff_points'][0]
            suggestions.append(f"注意{first_point['time']:.1f}秒处的音准控制，此处{first_point['direction']}约{first_point['diff_hz']:.0f}Hz")
        if pitch_diff['avg_diff'] > 10:
            suggestions.append("整体音准偏差较大，建议多听标准音频并模仿")
        rhythm_diff = result['rhythm_diff']
        if rhythm_diff['direction'] != "基本一致":
            suggestions.append(f"节奏{rhythm_diff['direction']}，BPM相差{rhythm_diff['bpm_diff']:.1f}，建议跟着节拍器练习")
        volume_diff = result['volume_diff']
        if volume_diff['direction'] != "基本一致":
            suggestions.append(f"音量{volume_diff['direction']}，相差{abs(volume_diff['db_diff']):.1f}dB，建议调整发音力度")
        if not suggestions:
            suggestions.append("整体表现良好，继续保持练习")
        return suggestions