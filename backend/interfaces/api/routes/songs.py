"""歌曲库路由 v7.9 — 标准曲库 CRUD + 分页/筛选/搜索

POST   /api/v1/songs        — 添加歌曲 (音频文件 + 元数据)
GET    /api/v1/songs        — 列表 (page/limit/style/difficulty/search)
GET    /api/v1/songs/{id}   — 详情
DELETE /api/v1/songs/{id}   — 删除
"""

from __future__ import annotations

import logging
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend.infrastructure.config import Settings
from backend.interfaces.api.deps import get_settings, get_song_service
from backend.application.songs.song_library_service import (
    SongLibraryService,
    SongNotFoundError,
    DuplicateSongError,
)
from backend.domain.songs.value_objects import (
    SongMetadata,
    DIFFICULTY_LABELS,
    STYLE_LABELS,
)
from backend.interfaces.api.schemas.songs import (
    SongOut,
    SongListResponse,
    SongCreateResponse,
    SongDetailResponse,
    SongDeleteResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()

_ERROR_MISSING_METADATA = '歌名和歌手不能为空'


@router.post("/songs", response_model=SongCreateResponse)
async def create_song(
    title: str = Form(''),
    artist: str = Form(''),
    key: str = Form('C'),
    bpm: int = Form(0),
    difficulty: str = Form('beginner'),
    style: str = Form('pop'),
    file: UploadFile | None = File(None),
    service: SongLibraryService = Depends(get_song_service),
    settings: Settings = Depends(get_settings),
) -> SongCreateResponse:
    """添加歌曲到标准曲库"""
    title = title.strip()
    artist = artist.strip()
    if not title or not artist:
        raise HTTPException(status_code=400, detail=_ERROR_MISSING_METADATA)
    if difficulty not in DIFFICULTY_LABELS:
        raise HTTPException(status_code=400, detail=f'无效的难度: {difficulty}')
    if style not in STYLE_LABELS:
        raise HTTPException(status_code=400, detail=f'无效的风格: {style}')

    metadata = SongMetadata(
        title=title,
        artist=artist,
        key=key.strip() or 'C',
        bpm=max(0, bpm),
        difficulty=difficulty,
        style=style,
    )

    # 保存音频文件 (可选) — 写入失败返回明确错误, 不泄露内部路径
    filepath = ''
    if file is not None:
        ext = Path(file.filename or '').suffix.lower()
        if ext not in settings.allowed_extensions:
            raise HTTPException(status_code=400, detail=f'不支持的音频格式: {ext or "unknown"}')
        try:
            songs_dir = settings.songs_dir
            songs_dir.mkdir(parents=True, exist_ok=True)
            stored_name = f'{uuid.uuid4().hex[:12]}{ext}'
            target = songs_dir / stored_name
            with open(target, 'wb') as out:
                shutil.copyfileobj(file.file, out)
            filepath = str(target)
        except Exception:
            logger.exception('歌曲文件保存失败')
            raise HTTPException(status_code=500, detail='文件保存失败，请稍后重试')

    try:
        song = service.add_song(metadata, filepath=filepath)
    except DuplicateSongError as exc:
        # 清理已保存的孤立文件 (重复检测在入库时才触发)
        if filepath:
            try:
                Path(filepath).unlink(missing_ok=True)
            except OSError:
                logger.warning('清理孤立歌曲文件失败: %s', filepath)
        raise HTTPException(status_code=409, detail=str(exc))

    logger.info('歌曲入库: %s - %s (%s)', song.metadata.title, song.metadata.artist, song.id)
    return SongCreateResponse(song=SongOut.from_song(song))


@router.get("/songs", response_model=SongListResponse)
async def list_songs(
    page: int = 1,
    limit: int = 20,
    style: str | None = None,
    difficulty: str | None = None,
    search: str | None = None,
    service: SongLibraryService = Depends(get_song_service),
) -> SongListResponse:
    """歌曲库列表 — 分页 + 风格/难度筛选 + 歌名/歌手搜索"""
    page = max(1, page)
    limit = max(1, min(50, limit))
    result = service.list_songs(
        page=page, limit=limit, style=style, difficulty=difficulty, search=search,
    )
    return SongListResponse(
        songs=[SongOut.from_song(s) for s in result.songs],
        total=result.total,
        page=result.page,
        limit=result.limit,
    )


@router.get("/songs/{song_id}", response_model=SongDetailResponse)
async def get_song(
    song_id: str,
    service: SongLibraryService = Depends(get_song_service),
) -> SongDetailResponse:
    """歌曲详情"""
    try:
        song = service.get_song(song_id)
    except SongNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return SongDetailResponse(song=SongOut.from_song(song))


@router.delete("/songs/{song_id}", response_model=SongDeleteResponse)
async def delete_song(
    song_id: str,
    service: SongLibraryService = Depends(get_song_service),
) -> SongDeleteResponse:
    """删除歌曲"""
    try:
        service.delete_song(song_id)
    except SongNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return SongDeleteResponse(deleted=True)
