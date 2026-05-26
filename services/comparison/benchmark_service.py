"""
基准特征库预加工服务

将标准音频预加工为基准特征库，支持：
- 离线预加工，一次多次使用
- 版本兼容性设计
- 增量更新

基准库存储位置：data/benchmarks/*.npz
"""

import numpy as np
import librosa
import logging
from typing import Dict, Optional, List
from dataclasses import dataclass
from pathlib import Path
import hashlib
import time
import json
import os

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkFeatures:
    """基准音频预加工特征 - 版本兼容性设计"""
    version: str = "2.0"           # 用于未来版本兼容

    # 核心特征（必需）
    pitch_frames: np.ndarray = None      # PYIN基频 (10ms/帧)
    energy_frames: np.ndarray = None     # 短时能量 (RMS, dB)

    # 时间标记
    onset_times: np.ndarray = None       # 音符起始点
    beat_times: np.ndarray = None        # 节拍点
    phrase_boundaries: np.ndarray = None # 乐句边界索引

    # 元数据
    tempo: float = 0.0                   # 全局速度
    key_signature: str = "unknown"       # 调性
    duration: float = 0.0                # 总时长
    sample_rate: int = 22050             # 采样率
    frame_rate: int = 100                # 帧率 (默认100fps)

    # 校验信息
    source_hash: str = ""                # 源文件哈希
    created_at: str = ""                 # 创建时间 (ISO 8601)


class BenchmarkService:
    """
    基准特征库预加工服务

    功能：
    - 从标准音频提取特征并保存为基准库
    - 加载已有基准库
    - 版本迁移
    """

    VERSION = "2.0"
    BENCHMARK_DIR = "data/benchmarks"

    def __init__(self, sample_rate: int = 22050, hop_length: int = 512):
        self.sample_rate = sample_rate
        self.hop_length = hop_length
        self.frame_rate = sample_rate / hop_length

        # 确保基准库目录存在
        os.makedirs(self.BENCHMARK_DIR, exist_ok=True)

    def create_benchmark(
        self,
        audio_path: str,
        name: Optional[str] = None,
        save_to_file: bool = True
    ) -> Dict:
        """
        从音频文件创建基准特征库

        Args:
            audio_path: 音频文件路径
            name: 基准库名称（可选，默认使用文件名）
            save_to_file: 是否保存到文件

        Returns:
            {
                'benchmark_id': 'bm_xxx',
                'name': '歌曲名',
                'features': BenchmarkFeatures,
                'file_path': 'data/benchmarks/bm_xxx.npz'
            }
        """
        start_time = time.time()
        logger.info(f"[BenchmarkService] Creating benchmark from: {audio_path}")

        # 加载音频
        y, sr = librosa.load(audio_path, sr=self.sample_rate, mono=True)

        # 提取特征
        features = self._extract_features(y, sr, audio_path)

        # 生成基准库ID
        source_hash = self._compute_file_hash(audio_path)
        benchmark_id = f"bm_{source_hash[:12]}"

        # 设置名称
        if name is None:
            name = Path(audio_path).stem

        # 设置创建时间
        features.created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        features.source_hash = source_hash

        # 保存到文件
        file_path = None
        if save_to_file:
            file_path = os.path.join(self.BENCHMARK_DIR, f"{benchmark_id}.npz")
            self._save_benchmark(features, file_path)
            logger.info(f"[BenchmarkService] Saved benchmark to: {file_path}")

        compute_time = time.time() - start_time
        logger.info(f"[BenchmarkService] Benchmark created in {compute_time:.2f}s")

        return {
            'benchmark_id': benchmark_id,
            'name': name,
            'features': features,
            'file_path': file_path,
            'compute_time': compute_time
        }

    def load_benchmark(self, benchmark_id: str) -> Optional[BenchmarkFeatures]:
        """
        加载已有基准库

        Args:
            benchmark_id: 基准库ID

        Returns:
            BenchmarkFeatures 或 None
        """
        file_path = os.path.join(self.BENCHMARK_DIR, f"{benchmark_id}.npz")

        if not os.path.exists(file_path):
            logger.warning(f"[BenchmarkService] Benchmark not found: {benchmark_id}")
            return None

        return self._load_benchmark(file_path)

    def get_benchmark_info(self, benchmark_id: str) -> Optional[Dict]:
        """
        获取基准库信息（不含完整特征）

        Args:
            benchmark_id: 基准库ID

        Returns:
            {
                'benchmark_id': 'bm_xxx',
                'duration': 180.5,
                'tempo': 120,
                'onset_count': 45,
                'beat_count': 90
            }
        """
        features = self.load_benchmark(benchmark_id)
        if features is None:
            return None

        return {
            'benchmark_id': benchmark_id,
            'duration': features.duration,
            'tempo': features.tempo,
            'key_signature': features.key_signature,
            'onset_count': len(features.onset_times) if features.onset_times is not None else 0,
            'beat_count': len(features.beat_times) if features.beat_times is not None else 0,
            'version': features.version,
            'created_at': features.created_at
        }

    def list_benchmarks(self) -> List[Dict]:
        """
        列出所有基准库

        Returns:
            [{'benchmark_id': 'bm_xxx', 'name': '歌曲名', ...}, ...]
        """
        benchmarks = []

        for file_name in os.listdir(self.BENCHMARK_DIR):
            if file_name.endswith('.npz'):
                benchmark_id = file_name[:-4]  # 去掉 .npz
                info = self.get_benchmark_info(benchmark_id)
                if info is not None:
                    # 尝试读取名称（从元数据文件）
                    meta_path = os.path.join(self.BENCHMARK_DIR, f"{benchmark_id}.json")
                    if os.path.exists(meta_path):
                        with open(meta_path, 'r', encoding='utf-8') as f:
                            meta = json.load(f)
                            info['name'] = meta.get('name', benchmark_id)
                    else:
                        info['name'] = benchmark_id

                    benchmarks.append(info)

        return benchmarks

    def delete_benchmark(self, benchmark_id: str) -> bool:
        """删除基准库"""
        file_path = os.path.join(self.BENCHMARK_DIR, f"{benchmark_id}.npz")
        meta_path = os.path.join(self.BENCHMARK_DIR, f"{benchmark_id}.json")

        deleted = False

        if os.path.exists(file_path):
            os.remove(file_path)
            deleted = True

        if os.path.exists(meta_path):
            os.remove(meta_path)

        if deleted:
            logger.info(f"[BenchmarkService] Deleted benchmark: {benchmark_id}")

        return deleted

    def _extract_features(self, y: np.ndarray, sr: int, audio_path: str) -> BenchmarkFeatures:
        """提取所有特征"""
        hop_length = self.hop_length

        # 1. 基频 (PYIN)
        f0, voiced_flags, _ = librosa.pyin(
            y,
            fmin=librosa.note_to_hz('C2'),
            fmax=librosa.note_to_hz('C6'),
            sr=sr,
            hop_length=hop_length
        )
        f0 = np.nan_to_num(f0, nan=0.0)

        # 2. 能量 (RMS)
        rms = librosa.feature.rms(y=y, sr=sr, hop_length=hop_length)[0]
        rms_db = 20 * np.log10(rms + 1e-10)

        # 3. 音符起始点
        onset_frames = librosa.onset.onset_detect(y=y, sr=sr, hop_length=hop_length)
        onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=hop_length)

        # 4. 节拍点
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop_length)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop_length)

        # 5. 乐句边界（基于能量变化）
        phrase_boundaries = self._detect_phrases(rms_db)

        # 6. 调性估计
        key_signature = self._estimate_key(y, sr)

        # 7. 时长
        duration = len(y) / sr

        return BenchmarkFeatures(
            version=self.VERSION,
            pitch_frames=f0,
            energy_frames=rms_db,
            onset_times=onset_times,
            beat_times=beat_times,
            phrase_boundaries=phrase_boundaries,
            tempo=float(tempo),
            key_signature=key_signature,
            duration=duration,
            sample_rate=sr,
            frame_rate=int(self.frame_rate)
        )

    def _detect_phrases(self, energy: np.ndarray) -> np.ndarray:
        """
        检测乐句边界

        基于能量的显著下降点
        """
        # 计算能量变化
        energy_diff = np.diff(energy)

        # 寻找显著下降点
        threshold = np.std(energy_diff) * -1.5
        phrase_ends = np.where(energy_diff < threshold)[0]

        # 过滤过短的乐句
        min_phrase_length = int(self.frame_rate * 2)  # 最小2秒
        filtered_boundaries = [0]

        for end in phrase_ends:
            if end - filtered_boundaries[-1] > min_phrase_length:
                filtered_boundaries.append(end)

        return np.array(filtered_boundaries, dtype=np.int32)

    def _estimate_key(self, y: np.ndarray, sr: int) -> str:
        """
        估计调性

        简化实现：基于色度特征
        """
        try:
            chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
            chroma_mean = np.mean(chroma, axis=1)

            # 找到最显著的音
            key_idx = np.argmax(chroma_mean)
            key_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

            # 判断大调或小调（简化）
            # 如果第3个音（相对于主音）较强，倾向于小调
            minor_idx = (key_idx + 3) % 12
            major_idx = (key_idx + 4) % 12

            if chroma_mean[minor_idx] > chroma_mean[major_idx]:
                return f"{key_names[key_idx]}_minor"
            else:
                return f"{key_names[key_idx]}_major"

        except Exception as e:
            logger.warning(f"[BenchmarkService] Key estimation failed: {e}")
            return "unknown"

    def _compute_file_hash(self, file_path: str) -> str:
        """计算文件哈希"""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _save_benchmark(self, features: BenchmarkFeatures, file_path: str) -> None:
        """保存基准库到文件"""
        np.savez(
            file_path,
            version=features.version,
            pitch_frames=features.pitch_frames,
            energy_frames=features.energy_frames,
            onset_times=features.onset_times,
            beat_times=features.beat_times,
            phrase_boundaries=features.phrase_boundaries,
            tempo=features.tempo,
            key_signature=features.key_signature,
            duration=features.duration,
            sample_rate=features.sample_rate,
            frame_rate=features.frame_rate,
            source_hash=features.source_hash,
            created_at=features.created_at
        )

    def _load_benchmark(self, file_path: str) -> BenchmarkFeatures:
        """从文件加载基准库"""
        data = np.load(file_path, allow_pickle=True)

        features = BenchmarkFeatures(
            version=str(data.get('version', '1.0')),
            pitch_frames=data.get('pitch_frames', None),
            energy_frames=data.get('energy_frames', None),
            onset_times=data.get('onset_times', None),
            beat_times=data.get('beat_times', None),
            phrase_boundaries=data.get('phrase_boundaries', None),
            tempo=float(data.get('tempo', 0.0)),
            key_signature=str(data.get('key_signature', 'unknown')),
            duration=float(data.get('duration', 0.0)),
            sample_rate=int(data.get('sample_rate', 22050)),
            frame_rate=int(data.get('frame_rate', 100)),
            source_hash=str(data.get('source_hash', '')),
            created_at=str(data.get('created_at', ''))
        )

        # 版本迁移（如果需要）
        if features.version != self.VERSION:
            features = self._migrate_version(features)

        return features

    def _migrate_version(self, features: BenchmarkFeatures) -> BenchmarkFeatures:
        """版本迁移"""
        # 目前只有 v2.0，未来可以添加迁移逻辑
        logger.info(f"[BenchmarkService] Migrating from v{features.version} to v{self.VERSION}")
        features.version = self.VERSION
        return features
