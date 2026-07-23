"""Pydantic v2 评估相关 Schema"""

from __future__ import annotations
from typing import Optional, Literal
from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """上传分析响应 — v7.0 六维格式"""
    success: bool = True
    analysis_id: Optional[str] = None
    total_score: float = Field(ge=0, le=100)
    scores: dict[str, float] = Field(default_factory=dict)
    timbre_adjustment: float = 0.0
    level: str = ""
    grade: str = ""
    advice: list[str] = Field(default_factory=list)
    mode: str = "quick"
    is_voice: bool = True
    filepath: Optional[str] = None
    basic_info: Optional[dict] = None
    heuristic_dimensions: list[str] = Field(default_factory=list)


class AnalyzeRequest(BaseModel):
    """分析请求"""
    filepath: str
    reference_filepath: Optional[str] = None
    mode: str = "quick"


class PitchExtractResponse(BaseModel):
    """音高曲线提取响应"""
    success: bool = True
    data: Optional[dict] = None
    error: Optional[str] = None


class SeparateRequest(BaseModel):
    """人声分离请求"""
    filepath: str
    model: str = "htdemucs_ft"
    two_stems: Optional[Literal["vocals", "drums", "bass", "other"]] = "vocals"


class SeparateResponse(BaseModel):
    """人声分离响应"""
    success: bool = True
    vocals_path: Optional[str] = None
    accompaniment_path: Optional[str] = None
    drums_path: Optional[str] = None
    bass_path: Optional[str] = None
    other_path: Optional[str] = None
    duration: Optional[float] = None
    model_used: Optional[str] = None
    error: Optional[str] = None


class ReportRequest(BaseModel):
    """报告生成请求"""
    analysis_result: dict
    filename: str = "report"
    format: str = "image"  # pdf | image


class ReportResponse(BaseModel):
    """报告生成响应"""
    success: bool = True
    pdf_path: Optional[str] = None
    image_path: Optional[str] = None
    error: Optional[str] = None


class CompareRequest(BaseModel):
    """对比分析请求"""
    standard_filepath: Optional[str] = None
    user_filepath: Optional[str] = None
    style: str = "pop"


class CompareResponse(BaseModel):
    """对比分析响应"""
    success: bool = True
    data: Optional[dict] = None
    error: Optional[str] = None
