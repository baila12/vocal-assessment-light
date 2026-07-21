"""歌曲库路由 v7.0 — NEW (v6.3 缺失)"""

from fastapi import APIRouter, HTTPException

router = APIRouter()

# Phase 4: SQLite 歌曲库 CRUD
# GET    /api/v1/songs        — 列表
# POST   /api/v1/songs        — 添加
# GET    /api/v1/songs/{id}   — 详情
# DELETE /api/v1/songs/{id}   — 删除


@router.get("/songs")
async def list_songs():
    """歌曲库列表 (stub — Phase 4 实现)"""
    return {"success": True, "songs": [], "total": 0}


@router.get("/songs/{song_id}")
async def get_song(song_id: str):
    """歌曲详情 (stub — Phase 4 实现)"""
    raise HTTPException(status_code=404, detail="歌曲库功能将在 Phase 4 实现")
