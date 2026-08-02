"""
歌曲库实体 — Song 聚合根 + 分页结果

frozen dataclass 保持不可变, 与 comparison/assessment 领域一致。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.domain.songs.value_objects import SongMetadata, SongFeatureStatus


@dataclass(frozen=True)
class Song:
    """标准歌曲聚合根 — 不可变

    Fields:
        id: 唯一 ID (UUID hex 前 12 位)
        metadata: 歌曲元数据
        filepath: 音频文件路径 (绝对路径)
        duration_seconds: 音频时长 (秒)
        feature_status: 特征预提取状态 (pending/preparing/ready/failed)
        scoring_config: 该歌曲关联的评分权重配置 (v6.0 评分参数)
        created_at: 入库时间 (ISO 8601)
    """
    id: str
    metadata: SongMetadata
    filepath: str = ''
    duration_seconds: float = 0.0
    feature_status: SongFeatureStatus = 'pending'
    scoring_config: dict = field(default_factory=dict)
    created_at: str = ''


@dataclass(frozen=True)
class SongListPage:
    """歌曲分页结果 — 不可变"""
    songs: tuple[Song, ...]
    total: int
    page: int
    limit: int
