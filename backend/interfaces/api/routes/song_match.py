"""歌曲自动匹配路由 v7.14 — 上传录音自动匹配标准歌曲

POST /api/v1/songs/match — multipart file + top_n Form → 匹配候选列表

用户音频保存到 uploads_dir; 匹配失败 (无候选/空库/超时) 返回优雅降级结果,
无效音频文件返回 400。
"""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend.application.song_match.auto_match_use_case import AutoMatchUseCase
from backend.interfaces.api.deps import get_auto_match_use_case, get_flask_config
from backend.interfaces.api.routes.assessment import sanitize_filename
from backend.interfaces.api.schemas.song_match import SongMatchResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post('/songs/match', response_model=SongMatchResponse)
async def match_song(
    file: UploadFile = File(...),
    top_n: int = Form(3),
    config=Depends(get_flask_config),
    usecase: AutoMatchUseCase = Depends(get_auto_match_use_case),
) -> SongMatchResponse:
    """上传用户录音, 自动匹配最相近的标准歌曲

    Args:
        file: 用户演唱音频 (WAV/MP3)
        top_n: 返回候选数 (1-10)
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail='没有选择文件')
    if not config.is_allowed_extension(file.filename):
        raise HTTPException(status_code=400, detail='不支持的文件格式')
    top_n = max(1, min(10, top_n))

    safe_name = sanitize_filename(file.filename)
    filepath = config.get_upload_path(safe_name)
    content = await file.read()
    filepath.write_bytes(content)

    try:
        result = await asyncio.to_thread(usecase.execute, str(filepath), top_n=top_n)
    except HTTPException:
        raise
    except (OSError, ValueError, RuntimeError):  # 音频解码/特征提取失败 → 400
        logger.warning('音频分析失败: %s', safe_name)
        raise HTTPException(status_code=400, detail='音频文件无效或无法分析，请重试')
    # 其余异常 (DB 错误/权限等) 交全局 500 处理, 不误报为"音频无效"

    return SongMatchResponse(
        success=True,
        matched=result.matched,
        matched_song=result.matched_song,
        candidates=[c.to_dict() for c in result.candidates],
        fallback_reason=result.fallback_reason,
        detected_key=result.detected_key,
        partial=result.partial,
        elapsed_ms=round(result.elapsed_ms, 1),
    )
