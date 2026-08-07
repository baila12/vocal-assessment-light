"""
歌曲音高曲线值对象 — v7.13 选歌录音参考音高

标准歌曲 F0 曲线, 前端参考线叠加与实时音准对比的数据源。
不可变值对象, 零外部依赖 (frozen dataclass)。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SongPitchCurve:
    """歌曲 F0 曲线值对象 — 不可变

    Fields:
        song_id: 歌曲 ID
        frequencies: 逐帧基频 (Hz, NaN 已归一化为 0.0, 0 = 无声)
        times: 逐帧时间 (秒)
        confidence: 逐帧置信度 (0-1)
        sample_rate: 采样率 (默认 16000)
        hop_length: 帧步长 (默认 512)
    """

    song_id: str
    frequencies: tuple[float, ...]
    times: tuple[float, ...]
    confidence: tuple[float, ...]
    sample_rate: int = 16000
    hop_length: int = 512

    def __post_init__(self) -> None:
        """运行时校验 — 三数组长度一致 + NaN 归一化"""
        n = len(self.frequencies)
        if not (len(self.times) == n and len(self.confidence) == n):
            raise ValueError(
                f'frequencies/times/confidence 长度必须一致: '
                f'{len(self.frequencies)}/{len(self.times)}/{len(self.confidence)}'
            )
        if not self.song_id:
            raise ValueError('song_id 不能为空')

        # NaN → 0.0 (JSON 序列化兼容; 0 = 无声/未检出)
        if any(isinstance(f, float) and math.isnan(f) for f in self.frequencies):
            object.__setattr__(
                self,
                'frequencies',
                tuple(0.0 if isinstance(f, float) and math.isnan(f) else f for f in self.frequencies),
            )

    @property
    def duration_seconds(self) -> float:
        """音频时长 — 末帧时间 (空曲线为 0)"""
        return float(self.times[-1]) if self.times else 0.0

    @property
    def frame_count(self) -> int:
        """帧数"""
        return len(self.frequencies)

    def to_dict(self) -> dict[str, Any]:
        """JSON 兼容序列化 (tuple → list)"""
        return {
            'song_id': self.song_id,
            'frequencies': [float(f) for f in self.frequencies],
            'times': [float(t) for t in self.times],
            'confidence': [float(c) for c in self.confidence],
            'sample_rate': self.sample_rate,
            'hop_length': self.hop_length,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'SongPitchCurve':
        """从 JSON 兼容 dict 重建"""
        if not data.get('song_id'):
            raise ValueError('song_id 不能为空')
        return cls(
            song_id=data['song_id'],
            frequencies=tuple(data.get('frequencies', ())),
            times=tuple(data.get('times', ())),
            confidence=tuple(data.get('confidence', ())),
            sample_rate=data.get('sample_rate', 16000),
            hop_length=data.get('hop_length', 512),
        )
