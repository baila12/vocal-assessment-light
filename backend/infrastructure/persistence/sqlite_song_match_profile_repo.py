"""
SqliteSongMatchProfileRepository — 歌曲匹配特征 profile 仓储 (stdlib sqlite3)

与 SqliteSongRepository 同一数据库 (settings.songs_db), 独立表 song_match_profiles。
`:`memory:` 用于单元测试; 参数化查询防 SQL 注入; 线程锁串行化并发写。
chroma 以 JSON TEXT 存储 (tuple→list), 读取时还原为 tuple。
"""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

from backend.domain.song_match.value_objects import SongMatchProfile

_SCHEMA = """
CREATE TABLE IF NOT EXISTS song_match_profiles (
    song_id          TEXT PRIMARY KEY,
    title            TEXT NOT NULL DEFAULT '',
    artist           TEXT NOT NULL DEFAULT '',
    bpm              REAL NOT NULL DEFAULT 0,
    key              TEXT NOT NULL DEFAULT '',
    chroma           TEXT NOT NULL DEFAULT '[]',
    duration_seconds REAL NOT NULL DEFAULT 0,
    feature_version  TEXT NOT NULL DEFAULT '1.0',
    updated_at       TEXT NOT NULL DEFAULT ''
)
"""


class SqliteSongMatchProfileRepository:
    """SQLite 匹配特征仓储实现

    Args:
        db_path: 数据库路径, 默认 `:memory:` (测试用)
    """

    def __init__(self, db_path: str | Path = ':memory:'):
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(_SCHEMA)
        self._conn.commit()
        self._lock = threading.Lock()

    def close(self) -> None:
        """关闭数据库连接"""
        with self._lock:
            self._conn.close()

    def get(self, song_id: str) -> SongMatchProfile | None:
        """按歌曲 ID 查询, 不存在返回 None"""
        with self._lock:  # 读同样加锁: 与 save/delete 串行化, 避免读到半提交行
            row = self._conn.execute(
                'SELECT * FROM song_match_profiles WHERE song_id = ?', (song_id,)
            ).fetchone()
            return self._row_to_profile(row) if row else None

    def list_all(self) -> list[SongMatchProfile]:
        """列出全部 profile (供匹配枚举)"""
        with self._lock:  # 读同样加锁: 与 save/delete 串行化
            rows = self._conn.execute('SELECT * FROM song_match_profiles').fetchall()
            return [self._row_to_profile(r) for r in rows]

    def save(self, profile: SongMatchProfile) -> SongMatchProfile:
        """保存/更新 profile (INSERT OR REPLACE upsert)"""
        with self._lock:
            self._conn.execute(
                """
                INSERT OR REPLACE INTO song_match_profiles
                    (song_id, title, artist, bpm, key, chroma,
                     duration_seconds, feature_version, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    profile.song_id,
                    profile.title,
                    profile.artist,
                    float(profile.bpm),
                    profile.key,
                    json.dumps([float(c) for c in profile.chroma]),
                    float(profile.duration_seconds),
                    profile.feature_version,
                    profile.updated_at,
                ),
            )
            self._conn.commit()
        return profile

    def delete(self, song_id: str) -> bool:
        """删除 profile, 返回是否删除成功"""
        with self._lock:
            cur = self._conn.execute(
                'DELETE FROM song_match_profiles WHERE song_id = ?', (song_id,)
            )
            self._conn.commit()
        return cur.rowcount > 0

    @staticmethod
    def _row_to_profile(row: sqlite3.Row) -> SongMatchProfile:
        """数据库行 → 领域值对象 (chroma JSON → tuple)"""
        chroma = tuple(float(c) for c in json.loads(row['chroma'] or '[]'))
        if len(chroma) != 12:  # 防御: 非 12 维行 (手工改库/迁移) → 零向量, 不抛异常
            chroma = (0.0,) * 12
        return SongMatchProfile(
            song_id=row['song_id'],
            title=row['title'],
            artist=row['artist'],
            bpm=float(row['bpm']),
            key=row['key'],
            chroma=chroma,
            duration_seconds=float(row['duration_seconds']),
            feature_version=row['feature_version'],
            updated_at=row['updated_at'],
        )
