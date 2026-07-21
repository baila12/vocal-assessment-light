"""
历史记录路由 v7.0 — FastAPI 替代 Flask /api/history

委托到现有 JsonHistoryRepository，零破坏性变更。
⚠️ 字面路径 (batch/all) 必须在参数化路径 ({record_id}) 之前定义。
"""

from __future__ import annotations
from fastapi import APIRouter, Depends, Query, HTTPException

from backend.interfaces.api.deps import get_history_repo, get_flask_config
from backend.interfaces.api.schemas.history import (
    HistoryListResponse,
    HistoryDetailResponse,
    HistoryDeleteResponse,
    HistoryBatchDeleteRequest,
    HistoryBatchDeleteResponse,
    TestFilesResponse,
)

router = APIRouter()


# ===== 集合操作 (必须在参数化路径之前注册) =====

@router.get("/history", response_model=HistoryListResponse)
async def list_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    date: str = Query("all", alias="date"),
    repo=Depends(get_history_repo),
):
    """获取历史记录列表 (分页)"""
    limit = min(limit, 50)
    result = repo.get_paginated(page=page, limit=limit, date_filter=date)
    return HistoryListResponse(
        success=True,
        history=result["records"],
        total=result["total"],
        page=result["page"],
        total_pages=result["total_pages"],
        limit=result["limit"],
    )


@router.delete("/history/batch", response_model=HistoryBatchDeleteResponse)
async def delete_history_batch(
    body: HistoryBatchDeleteRequest, repo=Depends(get_history_repo)
):
    """批量删除历史记录"""
    if not body.ids or len(body.ids) == 0:
        raise HTTPException(status_code=400, detail="ids 不能为空")
    count = repo.delete_batch(body.ids)
    return HistoryBatchDeleteResponse(success=True, deleted_count=count)


@router.delete("/history/all", response_model=HistoryBatchDeleteResponse)
async def delete_history_all(repo=Depends(get_history_repo)):
    """删除所有历史记录"""
    all_records = repo.get_all(limit=1000)
    all_ids = [r.get("id") for r in all_records if r.get("id")]
    count = repo.delete_batch(all_ids)
    return HistoryBatchDeleteResponse(success=True, deleted_count=count)


# ===== 单条操作 (参数化路径放在最后) =====

@router.get("/history/{record_id}", response_model=HistoryDetailResponse)
async def get_history(record_id: str, repo=Depends(get_history_repo)):
    """获取单条历史记录详情"""
    record = repo.get_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return HistoryDetailResponse(success=True, record=record)


@router.delete("/history/{record_id}", response_model=HistoryDeleteResponse)
async def delete_history(record_id: str, repo=Depends(get_history_repo)):
    """删除单条历史记录"""
    ok = repo.delete(record_id)
    if not ok:
        raise HTTPException(status_code=404, detail="删除失败，记录不存在")
    return HistoryDeleteResponse(success=True)


# ===== 测试文件 =====

@router.get("/test-files", response_model=TestFilesResponse)
async def get_test_files(config=Depends(get_flask_config)):
    """获取测试音乐文件列表"""
    test_dir = config.PROJECT_ROOT / "tests" / "test_data" / "audio"
    files = []
    if test_dir.exists():
        for f in test_dir.iterdir():
            if f.suffix.lower() in config.ALLOWED_EXTENSIONS:
                files.append({
                    "filename": f.name,
                    "filepath": str(f),
                    "size": f"{f.stat().st_size / (1024 * 1024):.2f}MB",
                })
    return TestFilesResponse(success=True, files=files)
