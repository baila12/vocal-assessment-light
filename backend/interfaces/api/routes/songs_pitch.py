"""歌曲音高路由 v7.13 — 参考 F0 曲线 (选歌录音参考线数据源)

GET /api/v1/songs/{id}/pitch — 歌曲 F0 曲线

说明: 不走 validate_filepath (白名单仅含 upload/test)。
歌曲文件路径来自歌曲库入库时已验证的 song.filepath (songs_dir 子树)。
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from backend.application.songs.song_library_service import (
    SongLibraryService,
    SongNotFoundError,
)
from backend.application.songs_pitch.get_song_pitch import GetSongPitchUseCase
from backend.interfaces.api.deps import get_song_service, get_song_pitch_usecase
from backend.interfaces.api.schemas.songs_pitch import (
    SongPitchResponse,
    SongPitchData,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/songs/{song_id}/pitch", response_model=SongPitchResponse)
async def get_song_pitch(
    song_id: str,
    service: SongLibraryService = Depends(get_song_service),
    usecase: GetSongPitchUseCase = Depends(get_song_pitch_usecase),
) -> SongPitchResponse:
    """返回歌曲预提取/即时提取的 F0 曲线"""
    try:
        song = service.get_song(song_id)
    except SongNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    if not song.filepath:
        raise HTTPException(status_code=400, detail='该歌曲无音频文件')
    if not Path(song.filepath).exists():
        raise HTTPException(status_code=404, detail='歌曲音频文件不存在')

    try:
        # CPU 密集 (librosa.yin) → thread pool, 避免阻塞事件循环
        curve = await asyncio.to_thread(usecase.execute, song_id, song.filepath)
    except Exception:
        logger.exception('歌曲音高提取失败: %s', song_id)
        raise HTTPException(status_code=500, detail='音高提取失败，请稍后重试')

    return SongPitchResponse(data=SongPitchData.from_curve(curve))
