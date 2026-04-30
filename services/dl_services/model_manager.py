"""
深度学习模型管理器 v2.0

此文件保留为向后兼容的代理模块。
实际实现已重构到 model_manager/ 子模块中。
"""
from .model_manager import (
    ModelStatus,
    ModelInfo,
    MOSPredictorProtocol,
    DLModelManager,
    MOSModelManager,
    get_mos_model_manager,
    reset_mos_model_manager,
    ModelDiagnostic,
)

__all__ = [
    'ModelStatus',
    'ModelInfo',
    'MOSPredictorProtocol',
    'DLModelManager',
    'MOSModelManager',
    'get_mos_model_manager',
    'reset_mos_model_manager',
    'ModelDiagnostic',
]
