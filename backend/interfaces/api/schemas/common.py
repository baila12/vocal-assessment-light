"""Pydantic v2 通用 Schema — API 响应信封"""

from __future__ import annotations
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """标准化 API 响应信封"""
    success: bool = True
    data: Optional[T] = None
    error: Optional[str] = None


class ErrorResponse(BaseModel):
    """标准化错误响应"""
    success: bool = False
    error: str
    detail: Optional[str] = None


class PaginationMeta(BaseModel):
    """分页元数据"""
    total: int
    page: int
    total_pages: int
    limit: int
