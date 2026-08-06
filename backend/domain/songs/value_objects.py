"""
歌曲库值对象 — 歌曲元数据/难度/风格

不可变值对象, 零外部依赖 (frozen dataclass)。
风格枚举与 comparison 领域 STYLE_WEIGHTS 的键对齐 (pop/classical/folk/rap)。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

SongDifficulty = Literal['beginner', 'intermediate', 'advanced']
SongStyle = Literal['pop', 'classical', 'folk', 'rap']
SongFeatureStatus = Literal['pending', 'preparing', 'ready', 'failed']

# 显示标签 (前端展示用, 领域内部用英文键)
DIFFICULTY_LABELS = {
    'beginner': '初级',
    'intermediate': '中级',
    'advanced': '高级',
}
STYLE_LABELS = {
    'pop': '流行',
    'classical': '美声',
    'folk': '民谣',
    'rap': '说唱',
}


@dataclass(frozen=True)
class SongMetadata:
    """歌曲元数据 — 不可变

    Fields:
        title: 歌名
        artist: 歌手
        key: 调性 (如 C Major / D)
        bpm: 速度 (0 = 未知)
        difficulty: 难度 (beginner/intermediate/advanced)
        style: 风格 (pop/classical/folk/rap)
        vocal_range: 音域 (如 C3-E5, '' = 未知) — v7.12 选歌录音
    """
    title: str
    artist: str
    key: str = 'C'
    bpm: int = 0
    difficulty: SongDifficulty = 'beginner'
    style: SongStyle = 'pop'
    vocal_range: str = ''

    def __post_init__(self) -> None:
        """运行时校验 — Literal 类型注解仅为编译期提示"""
        if self.difficulty not in DIFFICULTY_LABELS:
            raise ValueError(f'无效的难度: {self.difficulty}')
        if self.style not in STYLE_LABELS:
            raise ValueError(f'无效的风格: {self.style}')

    def duplicate_key(self) -> tuple[str, str]:
        """重复检测键 — 歌名+歌手 (大小写与首尾空白归一化)

        数据库.feature: "曲库中已存在 '月亮代表我的心 - 邓丽君'"
        """
        return self.title.strip().lower(), self.artist.strip().lower()

    @property
    def difficulty_label(self) -> str:
        """难度中文标签"""
        return DIFFICULTY_LABELS.get(self.difficulty, self.difficulty)

    @property
    def style_label(self) -> str:
        """风格中文标签"""
        return STYLE_LABELS.get(self.style, self.style)
