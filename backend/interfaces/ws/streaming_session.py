"""
流式会话管理 — Phase 3 WebSocket 实时评分的核心状态机

每个 WebSocket 连接对应一个 StreamingSession 实例。
管理: 音频缓冲累积、增量特征提取、评分调度。
"""

from __future__ import annotations
import logging
import time
import uuid
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


class StreamingSession:
    """流式评分会话 — 单例管理一个 WebSocket 连接的完整生命周期"""

    MAX_BUFFER_SECONDS = 120.0     # 最大录音时长 (防止内存溢出)
    PARTIAL_SCORE_INTERVAL = 2.0   # 增量评分间隔 (秒)
    PITCH_UPDATE_INTERVAL_SECONDS = 2.0  # 实时音高推送间隔 (秒, v7.13)
    FRAME_SAMPLES = 2048            # 每帧采样数 (16kHz, ~128ms)

    def __init__(self) -> None:
        self.id = uuid.uuid4().hex[:12]
        self.created_at = time.time()

        # 音频缓冲 (list of np.ndarray, accumulated then concatenated)
        self._audio_chunks: list[np.ndarray] = []
        self._total_samples = 0
        self._sample_rate = 16000

        # P2-13: audio_buffer 增量缓存 — 避免每 2s 周期全量 np.concatenate 重建
        # (60s 录音 ~469 块, 每周期 3 次全量重建 → 1 次惰性重建)
        self._cached_buffer: Optional[np.ndarray] = None
        self._buffer_dirty: bool = True

        # 增量特征缓存
        self._pitch_data: list[dict] = []   # [{frequencies, times, confidence}, ...]
        self._last_partial_at: float = 0.0
        self._pitch_computed_samples = 0    # v7.13: 已计算音高的采样位置 (增量推送)

        # 状态
        self.is_active = False
        self.mode: str = "quick"
        self.song_id: Optional[str] = None  # v7.12: 选歌录音 — 参考歌曲 ID

    @property
    def duration(self) -> float:
        """当前累积的音频时长 (秒)"""
        return self._total_samples / self._sample_rate

    @property
    def audio_buffer(self) -> Optional[np.ndarray]:
        """获取完整的音频数据 (用于最终评分) — 惰性拼接 + 缓存 (P2-13)

        仅当有新音频追加 (dirty) 时才重建; 重复访问命中缓存返回同一数组。
        返回的数组是内部缓存, 调用方必须以只读方式使用 (既有调用方均 astype 拷贝)。
        """
        if not self._audio_chunks:
            return None
        if self._buffer_dirty or self._cached_buffer is None:
            self._cached_buffer = np.concatenate(self._audio_chunks)
            self._buffer_dirty = False
        return self._cached_buffer

    def append_audio(self, pcm: np.ndarray) -> None:
        """添加一帧 PCM 数据 (Float32, 16kHz, 2048 samples)"""
        if self.duration >= self.MAX_BUFFER_SECONDS:
            return  # 静默丢弃 (防溢出)

        self._audio_chunks.append(pcm.astype(np.float32))
        self._total_samples += len(pcm)
        # P2-13: 追加使缓存失效 — 下次 audio_buffer 访问时重建
        self._buffer_dirty = True

    def ready_for_partial(self) -> bool:
        """是否应该发送增量评分"""
        now = time.time()
        if now - self._last_partial_at >= self.PARTIAL_SCORE_INTERVAL:
            self._last_partial_at = now
            return self.duration >= 2.0  # 至少2秒音频
        return False

    def ready_for_pitch_update(self) -> bool:
        """v7.13: 是否应推送实时音高 — 至少 2s 新音频 (样本驱动, 确定性可测)"""
        new_samples = self._total_samples - self._pitch_computed_samples
        return new_samples >= int(self._sample_rate * self.PITCH_UPDATE_INTERVAL_SECONDS)

    def get_new_audio_segment(self) -> Optional[np.ndarray]:
        """v7.13: 自上次音高计算以来的新增音频段 (Float32)"""
        buffer = self.audio_buffer
        if buffer is None or self._pitch_computed_samples >= len(buffer):
            return None
        return buffer[self._pitch_computed_samples:]

    def mark_pitch_computed(self) -> None:
        """v7.13: 记录当前已计算的采样位置"""
        self._pitch_computed_samples = self._total_samples

    def compute_partial(self) -> dict:
        """
        计算增量评分 (简化版: 仅实时音高)

        v7.14 审查 5.2 修复:
        - 节奏: 无参考歌曲不可评 → `rhythm: None` (原硬编码 50.0 假分, 前端 ?? 0 安全)
        - 音准: 去除绝对频率偏置 (旧公式 261.6Hz C4 基准歧视男低音) →
          改为 voiced 覆盖率 (与 `_score_lightweight` 同款中性公式)
        """
        buffer = self.audio_buffer
        if buffer is None or len(buffer) < self._sample_rate:
            return {
                "event": "partial_score",
                "pitch": 0.0,
                "rhythm": None,
                "progress": min(1.0, self.duration / 60.0),
                "elapsed_s": self.duration,
            }

        # 中性音高代理: voiced 覆盖率 (无参考歌曲, 无法评绝对音准, 只评发声稳定度)
        try:
            import librosa
            f0, voiced_flag, _ = librosa.pyin(
                buffer.astype(np.float64),
                fmin=65.0,
                fmax=1047.0,
                sr=self._sample_rate,
                hop_length=512,
            )
            valid = f0[~np.isnan(f0)]
            if len(valid) > 10:
                detection_rate = len(valid) / max(len(f0), 1)
                pitch_score = min(100.0, max(0.0, detection_rate * 80.0 + 20.0))
            else:
                pitch_score = 0.0
        except Exception as e:
            logger.warning("WS partial pitch failed: %s, using 0.0", e, exc_info=True)
            pitch_score = 0.0

        return {
            "event": "partial_score",
            "pitch": round(pitch_score, 1),
            "rhythm": None,
            "progress": min(1.0, self.duration / 60.0),
            "elapsed_s": round(self.duration, 1),
        }

    def cleanup(self) -> None:
        """释放资源 — WebSocket 断开时调用"""
        self._audio_chunks.clear()
        self._cached_buffer = None  # P2-13: 释放缓存防泄漏
        self._buffer_dirty = True
        self._pitch_data.clear()
        self.is_active = False
