"""
接口层 - 路由模块
"""
from .upload import upload_bp
from .history import history_bp
from .audio import audio_bp

__all__ = ['upload_bp', 'history_bp', 'audio_bp']