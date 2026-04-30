"""
音频数据缓存管理

提供线程安全的音频数据缓存，避免重复加载
"""
import threading
from typing import Dict, Optional, Tuple
import numpy as np
import logging

logger = logging.getLogger(__name__)


class AudioCache:
    """
    音频数据缓存管理器

    线程安全的LRU缓存实现
    """

    def __init__(self, max_size: int = 5):
        """
        初始化缓存

        Args:
            max_size: 最大缓存文件数
        """
        self._cache: Dict[str, Tuple[np.ndarray, int]] = {}
        self._max_size = max_size
        self._lock = threading.Lock()

    def get(self, filepath: str) -> Optional[Tuple[np.ndarray, int]]:
        """
        从缓存获取音频数据

        Args:
            filepath: 文件路径

        Returns:
            (audio_data, sample_rate) 或 None
        """
        with self._lock:
            if filepath in self._cache:
                logger.debug(f"从缓存获取音频: {filepath}")
                return self._cache[filepath]
            return None

    def set(self, filepath: str, audio_data: np.ndarray, sample_rate: int) -> None:
        """
        缓存音频数据

        Args:
            filepath: 文件路径
            audio_data: 音频数据
            sample_rate: 采样率
        """
        with self._lock:
            # 清理旧缓存 (LRU策略)
            if len(self._cache) >= self._max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                logger.debug(f"清理缓存: {oldest_key}")

            self._cache[filepath] = (audio_data, sample_rate)
            logger.debug(f"缓存音频: {filepath}")

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            logger.debug("缓存已清空")

    def __len__(self) -> int:
        return len(self._cache)


# 全局缓存实例
_audio_cache: Optional[AudioCache] = None
_cache_lock = threading.Lock()


def get_audio_cache() -> AudioCache:
    """获取全局音频缓存实例（单例）"""
    global _audio_cache
    if _audio_cache is None:
        with _cache_lock:
            if _audio_cache is None:
                _audio_cache = AudioCache()
    return _audio_cache
