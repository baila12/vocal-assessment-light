"""
模型管理基础类型和协议
"""
from enum import Enum, auto
from dataclasses import dataclass
from typing import Protocol, Any


class ModelStatus(Enum):
    """模型状态枚举"""
    AVAILABLE = auto()      # 可用
    LOADING = auto()        # 加载中
    FAILED = auto()         # 加载失败
    DISABLED = auto()       # 已禁用
    HEALTHY = auto()        # 健康检查通过


@dataclass
class ModelInfo:
    """模型信息"""
    name: str
    status: ModelStatus
    priority: int              # 优先级（数字越小优先级越高）
    last_health_check: float = 0.0
    failure_count: int = 0
    last_error: str = ""
    load_time: float = 0.0


class MOSPredictorProtocol(Protocol):
    """MOS预测器协议"""
    def predict(self, audio_path: str) -> Any: ...

    @property
    def is_available(self) -> bool: ...
