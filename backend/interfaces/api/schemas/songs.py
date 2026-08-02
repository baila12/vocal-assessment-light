"""歌曲库 Pydantic Schema — v7.9 标准曲库"""

from __future__ import annotations

from pydantic import BaseModel


class SongMetadataOut(BaseModel):
    """歌曲元数据响应"""
    title: str
    artist: str
    key: str = 'C'
    bpm: int = 0
    difficulty: str = 'beginner'
    style: str = 'pop'


class SongOut(BaseModel):
    """歌曲响应"""
    id: str
    metadata: SongMetadataOut
    filepath: str = ''
    duration_seconds: float = 0.0
    feature_status: str = 'pending'
    scoring_config: dict = {}
    created_at: str = ''

    @classmethod
    def from_song(cls, song) -> 'SongOut':
        """领域实体 → API 响应 (解耦序列化)"""
        m = song.metadata
        return cls(
            id=song.id,
            metadata=SongMetadataOut(
                title=m.title,
                artist=m.artist,
                key=m.key,
                bpm=m.bpm,
                difficulty=m.difficulty,
                style=m.style,
            ),
            filepath=song.filepath,
            duration_seconds=song.duration_seconds,
            feature_status=song.feature_status,
            scoring_config=song.scoring_config,
            created_at=song.created_at,
        )


class SongCreateResponse(BaseModel):
    """添加歌曲响应"""
    success: bool = True
    song: SongOut


class SongListResponse(BaseModel):
    """歌曲列表响应"""
    success: bool = True
    songs: list[SongOut] = []
    total: int = 0
    page: int = 1
    limit: int = 20


class SongDetailResponse(BaseModel):
    """歌曲详情响应"""
    success: bool = True
    song: SongOut


class SongDeleteResponse(BaseModel):
    """删除歌曲响应"""
    success: bool = True
    deleted: bool = True
