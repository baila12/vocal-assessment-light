"""Pydantic v2 评估相关 Schema"""

from __future__ import annotations
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator


class NormalizationInfo(BaseModel):
    """归一化透明度信息 — v7.1.2"""
    applied: bool = True
    note: str = ""


class UploadResponse(BaseModel):
    """上传分析响应 — v7.2 六维格式 + 归一化透明度"""
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
    # v7.14 审查 6.3: 维度评分失败 fallback 告警 (假 50.0 可辨识)
    scoring_warnings: list[str] = Field(default_factory=list)
    normalization: NormalizationInfo = Field(default_factory=NormalizationInfo)
    # 基础信息
    duration: Optional[float] = None
    duration_display: str = ""
    # v7.14: 上传时可选自动匹配标准歌曲 (auto_match=true 时注入)
    matched_song: Optional[dict] = None
    matched_candidates: list[dict] = Field(default_factory=list)
    fallback_reason: str = ""


class AnalyzeRequest(BaseModel):
    """分析请求"""
    filepath: str
    reference_filepath: Optional[str] = None
    mode: Literal["quick", "professional"] = "quick"


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

    @field_validator("filename")
    @classmethod
    def _sanitize_filename(cls, v: str) -> str:
        """防止路径穿越 — filename 会拼入 output_dir / f'{filename}_report.pdf'。

        v7.19 整理: 旧实现无任何校验, filename='../../evil' 可写出 output_dir。
        """
        v = v.strip()
        # 剥离目录分隔符与穿越片段 (Windows 反斜杠 + POSIX 斜杠)
        v = v.replace("\\", "_").replace("/", "_")
        # 去重路径片段 (.. / ~ 等)
        v = v.replace("..", "_").replace("~", "_")
        # 剥离控制字符
        v = "".join(ch for ch in v if ch.isprintable() or ch in ("-", "_", "(", ")", " ", "·"))
        # 长度上限 (Windows MAX_PATH 安全余量)
        v = v[:64] or "report"
        return v


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
