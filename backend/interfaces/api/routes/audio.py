"""音频播放路由 v7.0 — 文件流式传输 + 路径安全校验"""

from __future__ import annotations
from pathlib import Path
from urllib.parse import unquote
import re

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import FileResponse

from backend.interfaces.api.deps import get_flask_config, get_settings
from backend.infrastructure.config import Settings

router = APIRouter()

MIME_TYPES = {
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
}


@router.get("/audio")
async def serve_audio(
    file: str = Query(..., description="音频文件路径"),
    config=Depends(get_flask_config),
    settings: Settings = Depends(get_settings),
):
    """安全地流式传输音频文件"""
    filepath_raw = unquote(file)

    if not filepath_raw:
        raise HTTPException(status_code=404, detail="缺少文件路径")

    # 路径遍历防护
    if ".." in filepath_raw or "~" in filepath_raw:
        raise HTTPException(status_code=403, detail="无效的文件路径")
    if re.search(r"[\x00-\x1f\x7f]", filepath_raw):
        raise HTTPException(status_code=403, detail="无效的文件路径")

    filepath_obj = Path(filepath_raw)
    if filepath_obj.suffix.lower() not in config.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=403, detail="不支持的文件格式")

    try:
        filepath_obj = filepath_obj.resolve()
    except Exception:
        raise HTTPException(status_code=403, detail="无效的文件路径")

    # 目录锁: 仅允许 uploads/、test_data/audio/ 和 songs_dir/ (v7.10 歌曲库)
    # 用 is_relative_to() 而非 startswith — 避免同名前缀兄弟目录 (如 songs_evil/) 越界
    upload_dir = config.UPLOAD_FOLDER.resolve()
    test_dir = (config.PROJECT_ROOT / "tests" / "test_data" / "audio").resolve()
    songs_dir = settings.songs_dir.resolve()

    if not (
        filepath_obj.is_relative_to(upload_dir)
        or filepath_obj.is_relative_to(test_dir)
        or filepath_obj.is_relative_to(songs_dir)
    ):
        raise HTTPException(status_code=403, detail="无权访问此文件")

    if not filepath_obj.exists() or not filepath_obj.is_file():
        raise HTTPException(status_code=404, detail="文件不存在")

    mime_type = MIME_TYPES.get(filepath_obj.suffix.lower(), "audio/mpeg")
    return FileResponse(filepath_obj, media_type=mime_type)
