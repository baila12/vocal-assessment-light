"""
SqliteSongRepository — SQLite 标准歌曲库仓储 (stdlib sqlite3)

零额外依赖 (项目未引入 SQLAlchemy), 参数化查询防 SQL 注入。
`:memory:` 用于单元测试; 生产使用 `settings.songs_db_path`。
"""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

from backend.domain.songs.entities import Song
from backend.domain.songs.value_objects import SongMetadata

_SCHEMA = """
CREATE TABLE IF NOT EXISTS songs (
    id               TEXT PRIMARY KEY,
    title            TEXT NOT NULL,
    artist           TEXT NOT NULL,
    key              TEXT NOT NULL DEFAULT 'C',
    bpm              INTEGER NOT NULL DEFAULT 0,
    difficulty       TEXT NOT NULL DEFAULT 'beginner',
    style            TEXT NOT NULL DEFAULT 'pop',
    vocal_range      TEXT NOT NULL DEFAULT '',
    filepath         TEXT NOT NULL DEFAULT '',
    duration_seconds REAL NOT NULL DEFAULT 0,
    feature_status   TEXT NOT NULL DEFAULT 'pending',
    scoring_config   TEXT NOT NULL DEFAULT '{}',
    created_at       TEXT NOT NULL DEFAULT ''
)
"""

# 增量迁移: 旧库 (v7.11-) 无 vocal_range 列时 ALTER TABLE 补齐
_MIGRATIONS = (
    "vocal_range",
)


class SqliteSongRepository:
    """SQLite 歌曲仓储实现

    Args:
        db_path: 数据库路径, 默认 `:memory:` (测试用)
    """

    def __init__(self, db_path: str | Path = ':memory:'):
        # check_same_thread=False: FastAPI 线程池在不同线程调用
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(_SCHEMA)
        self._apply_migrations()
        self._conn.commit()
        self._lock = threading.Lock()  # 串行化并发写

    def _apply_migrations(self) -> None:
        """轻量列迁移 — 旧库 (v7.11-) 无 vocal_range 列时 ALTER TABLE 补齐."""
        existing = {
            row[1] for row in self._conn.execute('PRAGMA table_info(songs)').fetchall()
        }
        for column in _MIGRATIONS:
            if column not in existing:
                self._conn.execute(
                    f'ALTER TABLE songs ADD COLUMN {column} TEXT NOT NULL DEFAULT \'\''
                )

    def close(self) -> None:
        """关闭数据库连接"""
        with self._lock:
            self._conn.close()

    def add(self, song: Song) -> Song:
        """新增歌曲"""
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO songs
                    (id, title, artist, key, bpm, difficulty, style, vocal_range,
                     filepath, duration_seconds, feature_status, scoring_config, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    song.id,
                    song.metadata.title,
                    song.metadata.artist,
                    song.metadata.key,
                    song.metadata.bpm,
                    song.metadata.difficulty,
                    song.metadata.style,
                    song.metadata.vocal_range,
                    song.filepath,
                    song.duration_seconds,
                    song.feature_status,
                    json.dumps(song.scoring_config, ensure_ascii=False),
                    song.created_at,
                ),
            )
            self._conn.commit()
        return song

    def get_by_id(self, song_id: str) -> Song | None:
        """按 ID 查询"""
        row = self._conn.execute(
            'SELECT * FROM songs WHERE id = ?', (song_id,)
        ).fetchone()
        return self._row_to_song(row) if row else None

    def list(
        self,
        *,
        page: int,
        limit: int,
        style: str | None = None,
        difficulty: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Song], int]:
        """分页列表 + 筛选 + 搜索 (参数化查询)"""
        where: list[str] = []
        params: list = []

        if style:
            where.append('style = ?')
            params.append(style)
        if difficulty:
            where.append('difficulty = ?')
            params.append(difficulty)
        if search:
            where.append('(LOWER(title) LIKE ? OR LOWER(artist) LIKE ?)')
            like = f'%{search.strip().lower()}%'
            params.extend([like, like])

        where_sql = f'WHERE {" AND ".join(where)}' if where else ''

        total = self._conn.execute(
            f'SELECT COUNT(*) FROM songs {where_sql}', params
        ).fetchone()[0]

        offset = (page - 1) * limit
        rows = self._conn.execute(
            f'SELECT * FROM songs {where_sql} '
            'ORDER BY created_at DESC, rowid ASC LIMIT ? OFFSET ?',
            params + [limit, offset],
        ).fetchall()

        return [self._row_to_song(r) for r in rows], int(total)

    def delete(self, song_id: str) -> bool:
        """删除歌曲"""
        with self._lock:
            cur = self._conn.execute('DELETE FROM songs WHERE id = ?', (song_id,))
            self._conn.commit()
        return cur.rowcount > 0

    def find_duplicate(self, metadata: SongMetadata) -> Song | None:
        """按 (歌名+歌手) 查找重复歌曲"""
        row = self._conn.execute(
            'SELECT * FROM songs '
            'WHERE LOWER(TRIM(title)) = ? AND LOWER(TRIM(artist)) = ? LIMIT 1',
            (metadata.title.strip().lower(), metadata.artist.strip().lower()),
        ).fetchone()
        return self._row_to_song(row) if row else None

    def list_all_with_filepath(self) -> list[Song]:
        """列出所有 filepath 非空且文件存在的歌曲 (供匹配特征预算式预计算)"""
        rows = self._conn.execute(
            "SELECT * FROM songs WHERE filepath != ''"
        ).fetchall()
        songs = []
        for row in rows:
            song = self._row_to_song(row)
            if song.filepath and Path(song.filepath).exists():
                songs.append(song)
        return songs

    @staticmethod
    def _row_to_song(row: sqlite3.Row) -> Song:
        """数据库行 → 领域实体"""
        return Song(
            id=row['id'],
            metadata=SongMetadata(
                title=row['title'],
                artist=row['artist'],
                key=row['key'],
                bpm=row['bpm'],
                difficulty=row['difficulty'],
                style=row['style'],
                vocal_range=row['vocal_range'],
            ),
            filepath=row['filepath'],
            duration_seconds=row['duration_seconds'],
            feature_status=row['feature_status'],
            scoring_config=json.loads(row['scoring_config'] or '{}'),
            created_at=row['created_at'],
        )
