"""
song_match 领域值对象 — v7.14 上传音频自动匹配标准歌曲

MatchFeatures (用户音频匹配特征) / SongMatchProfile (歌曲预提取特征)
/ MatchCandidate (匹配候选) / MatchResult (匹配结果聚合)。
不可变值对象, 零外部依赖 (frozen dataclass), 与 songs_pitch 领域风格一致。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

CHROMA_BINS = 12
FEATURE_VERSION = '1.0'


@dataclass(frozen=True)
class MatchFeatures:
    """用户音频的匹配特征 — 不可变

    Fields:
        bpm: 检测到的速度 (BPM, 0 = 未检出/静音)
        detected_key: 检测调性 (如 "C", "G#", 由 Krumhansl-Schmuckler 给出)
        key_confidence: 调性检测置信度 (0-1)
        chroma: 12-bin 平均色度向量 (归一化, 非负)
        duration_seconds: 音频时长 (秒)
    """

    bpm: float
    detected_key: str
    key_confidence: float
    chroma: tuple[float, ...]
    duration_seconds: float

    def __post_init__(self) -> None:
        """运行时校验 — BPM 非负 + chroma 12 维 + 置信度 0-1"""
        if self.bpm < 0:
            raise ValueError(f'bpm 不能为负: {self.bpm}')
        if len(self.chroma) != CHROMA_BINS:
            raise ValueError(
                f'chroma 必须为 {CHROMA_BINS} 维, 当前 {len(self.chroma)}'
            )
        if not 0.0 <= self.key_confidence <= 1.0:
            raise ValueError(f'key_confidence 必须在 0-1: {self.key_confidence}')


@dataclass(frozen=True)
class SongMatchProfile:
    """标准歌曲的预提取匹配特征 (持久化到 SQLite) — 不可变

    Fields:
        song_id: 歌曲 ID
        bpm: 提取 BPM
        key: 提取调性 (如 "C")
        chroma: 12-bin 平均色度向量 (JSON 序列化为 list)
        duration_seconds: 歌曲时长 (秒)
        feature_version: 特征版本, 便于未来迁移
        updated_at: 更新时间 (ISO 8601)
    """

    song_id: str
    bpm: float
    key: str
    chroma: tuple[float, ...]
    duration_seconds: float
    title: str = ''
    artist: str = ''
    feature_version: str = FEATURE_VERSION
    updated_at: str = ''

    def __post_init__(self) -> None:
        """运行时校验 — song_id 非空 + chroma 12 维"""
        if not self.song_id:
            raise ValueError('song_id 不能为空')
        if len(self.chroma) != CHROMA_BINS:
            raise ValueError(
                f'chroma 必须为 {CHROMA_BINS} 维, 当前 {len(self.chroma)}'
            )

    def to_dict(self) -> dict[str, Any]:
        """JSON 兼容序列化 (tuple → list)"""
        return {
            'song_id': self.song_id,
            'title': self.title,
            'artist': self.artist,
            'bpm': float(self.bpm),
            'key': self.key,
            'chroma': [float(c) for c in self.chroma],
            'duration_seconds': float(self.duration_seconds),
            'feature_version': self.feature_version,
            'updated_at': self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'SongMatchProfile':
        """从 JSON 兼容 dict 重建"""
        if not data.get('song_id'):
            raise ValueError('song_id 不能为空')
        return cls(
            song_id=data['song_id'],
            title=data.get('title', ''),
            artist=data.get('artist', ''),
            bpm=float(data.get('bpm', 0.0)),
            key=data.get('key', ''),
            chroma=tuple(float(c) for c in data.get('chroma', ())),
            duration_seconds=float(data.get('duration_seconds', 0.0)),
            feature_version=data.get('feature_version', FEATURE_VERSION),
            updated_at=data.get('updated_at', ''),
        )


@dataclass(frozen=True)
class MatchCandidate:
    """单个匹配候选 — 不可变

    Fields:
        song_id/title/artist: 歌曲标识
        confidence: 综合置信度 (0-1)
        factors: 各维度得分 {"bpm","chroma","key","duration"}
        bpm_diff: 用户与歌曲 BPM 绝对差
        key_diff_semitones: 调性差半音数 (五度圈最小距离, 0-6)
        detected_key: 用户音频检测调性
    """

    song_id: str
    title: str
    artist: str
    confidence: float
    factors: dict[str, float] = field(default_factory=dict)
    bpm_diff: float = 0.0
    key_diff_semitones: int = 0
    detected_key: str = ''

    def to_dict(self) -> dict[str, Any]:
        """JSON 兼容序列化 (factors dict 拷贝)"""
        return {
            'song_id': self.song_id,
            'title': self.title,
            'artist': self.artist,
            'confidence': float(self.confidence),
            'factors': dict(self.factors),
            'bpm_diff': float(self.bpm_diff),
            'key_diff_semitones': int(self.key_diff_semitones),
            'detected_key': self.detected_key,
        }


@dataclass(frozen=True)
class MatchResult:
    """匹配结果聚合 — 不可变

    Fields:
        matched: 是否有匹配 (best confidence >= MATCH_THRESHOLD)
        matched_song: 最佳匹配摘要 {"id","title","artist","confidence"}, 无则 None
        candidates: Top-N 候选 (按 confidence 降序)
        fallback_reason: 回退原因 ("no_match"/"audio_too_short"/"no_profiles"), 空=已匹配
        detected_key: 用户音频检测调性
        partial: 是否超时部分匹配
        elapsed_ms: 匹配耗时 (毫秒)
    """

    matched: bool
    matched_song: dict[str, Any] | None = None
    candidates: tuple[MatchCandidate, ...] = ()
    fallback_reason: str = ''
    detected_key: str = ''
    partial: bool = False
    elapsed_ms: float = 0.0
