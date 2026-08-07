"""歌曲音高 Schema — v7.13 参考音高 API"""

from __future__ import annotations

from pydantic import BaseModel, Field

from backend.domain.songs_pitch.value_objects import SongPitchCurve


class SongPitchData(BaseModel):
    """歌曲 F0 曲线响应数据"""
    song_id: str
    frequencies: list[float] = Field(default_factory=list)   # Hz, 0 = 无声
    times: list[float] = Field(default_factory=list)         # 秒
    confidence: list[float] = Field(default_factory=list)    # 0-1
    sample_rate: int = 16000
    hop_length: int = 512
    duration_seconds: float = 0.0
    frame_count: int = 0

    @classmethod
    def from_curve(cls, curve: SongPitchCurve) -> 'SongPitchData':
        """领域值对象 → API 响应 (解耦序列化)"""
        return cls(
            song_id=curve.song_id,
            frequencies=list(curve.frequencies),
            times=list(curve.times),
            confidence=list(curve.confidence),
            sample_rate=curve.sample_rate,
            hop_length=curve.hop_length,
            duration_seconds=curve.duration_seconds,
            frame_count=curve.frame_count,
        )


class SongPitchResponse(BaseModel):
    """GET /api/v1/songs/{id}/pitch 响应"""
    success: bool = True
    data: SongPitchData | None = None
    error: str | None = None
