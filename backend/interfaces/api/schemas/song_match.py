"""歌曲自动匹配 Schema — v7.14 上传音频自动匹配标准歌曲"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SongMatchResponse(BaseModel):
    """POST /api/v1/songs/match 响应"""
    success: bool = True
    matched: bool = False
    matched_song: dict | None = None       # {"id","title","artist","confidence"}
    candidates: list[dict] = Field(default_factory=list)  # Top-N 候选 (confidence 降序)
    fallback_reason: str = ''              # no_match / no_profiles / audio_too_short / timeout
    detected_key: str = ''                 # 用户音频检测调性
    partial: bool = False                  # 超时部分匹配
    elapsed_ms: float = 0.0
    error: str | None = None
