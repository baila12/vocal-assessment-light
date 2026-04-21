"""
API 请求验证模块
使用 Pydantic 进行请求数据验证
"""
from typing import Optional, List
from pydantic import BaseModel, field_validator


class UploadRequest(BaseModel):
    """上传请求验证"""
    filename: str
    content_type: str

    @field_validator('content_type')
    @classmethod
    def validate_audio_content(cls, v: str) -> str:
        if not v.startswith('audio/'):
            raise ValueError('Must be audio content type')
        return v


class AnalyzeRequest(BaseModel):
    """分析请求验证"""
    filepath: str

    @field_validator('filepath')
    @classmethod
    def validate_filepath(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError('filepath cannot be empty')
        # 防止路径遍历
        if '..' in v:
            raise ValueError('Invalid path: path traversal detected')
        return v


class SeparateRequest(BaseModel):
    """人声分离请求验证"""
    filepath: str
    model: str = 'htdemucs_ft'
    two_stems: str = 'vocals'

    @field_validator('filepath')
    @classmethod
    def validate_filepath(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError('filepath cannot be empty')
        if '..' in v:
            raise ValueError('Invalid path: path traversal detected')
        return v

    @field_validator('model')
    @classmethod
    def validate_model(cls, v: str) -> str:
        allowed_models = [
            'htdemucs', 'htdemucs_ft', 'mdx', 'mdx_extra',
            'mdx_q', 'mdx_extra_q', 'demucs', 'demucs48'
        ]
        if v not in allowed_models:
            raise ValueError(f'model must be one of: {allowed_models}')
        return v

    @field_validator('two_stems')
    @classmethod
    def validate_two_stems(cls, v: str) -> str:
        allowed_stems = ['vocals', 'drums', 'bass', 'other']
        if v not in allowed_stems:
            raise ValueError(f'two_stems must be one of: {allowed_stems}')
        return v


class ReportRequest(BaseModel):
    """报告生成请求验证"""
    analysis_result: dict
    filename: str = 'report'
    format: str = 'image'

    @field_validator('format')
    @classmethod
    def validate_format(cls, v: str) -> str:
        if v not in ['pdf', 'image']:
            raise ValueError('format must be pdf or image')
        return v

    @field_validator('analysis_result')
    @classmethod
    def validate_analysis_result(cls, v: dict) -> dict:
        required_keys = ['success', 'scores', 'total_score']
        for key in required_keys:
            if key not in v:
                raise ValueError(f'analysis_result missing required key: {key}')
        return v


class CompareRequest(BaseModel):
    """对比分析请求验证"""
    standard_path: str
    user_path: str

    @field_validator('standard_path', 'user_path')
    @classmethod
    def validate_path(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError('path cannot be empty')
        if '..' in v:
            raise ValueError('Invalid path: path traversal detected')
        return v
