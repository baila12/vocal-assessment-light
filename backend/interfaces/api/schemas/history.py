"""Pydantic v2 历史记录 Schema"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


class HistoryRecordOut(BaseModel):
    """历史记录条目"""
    id: Optional[int | str] = None
    filename: str = ""
    filepath: str = ""
    total_score: float = 0.0
    level: str = ""
    grade: str = ""
    mode: str = "quick"
    advice: list[str] = Field(default_factory=list)
    scores: dict[str, float] = Field(default_factory=dict)
    created_at: Optional[str] = None
    basic_info: Optional[dict] = None
    duration: Optional[float] = None  # v7.3: 音频时长 (秒)


class HistoryListResponse(BaseModel):
    """历史记录列表响应"""
    success: bool = True
    history: list[dict] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    total_pages: int = 0
    limit: int = 20


class HistoryDetailResponse(BaseModel):
    """历史记录详情响应"""
    success: bool = True
    record: Optional[dict] = None


class HistoryDeleteResponse(BaseModel):
    """历史记录删除响应"""
    success: bool = True


class HistoryBatchDeleteRequest(BaseModel):
    """批量删除请求"""
    ids: list[int | str]


class HistoryBatchDeleteResponse(BaseModel):
    """批量删除响应"""
    success: bool = True
    deleted_count: int = 0


class TestFileInfo(BaseModel):
    """测试文件信息"""
    filename: str
    filepath: str
    size: str


class TestFilesResponse(BaseModel):
    """测试文件列表响应"""
    success: bool = True
    files: list[dict] = Field(default_factory=list)
