"""评分领域异常"""

from __future__ import annotations


class DomainError(Exception):
    """领域层基础异常"""
    pass


class InvalidScoreError(DomainError):
    """无效分值异常 — 输入数据不满足评分前提条件"""

    def __init__(self, dimension: str, reason: str) -> None:
        self.dimension = dimension
        self.reason = reason
        super().__init__(f"[{dimension}] {reason}")


class NonVoiceDetectedError(DomainError):
    """非人声检测异常 — 输入不是可评分的人声"""

    def __init__(self, confidence: float = 0.0) -> None:
        self.confidence = confidence
        super().__init__(f"Non-voice audio detected (confidence: {confidence:.2f})")


class InsufficientDataError(DomainError):
    """数据不足异常 — 音频太短或特征提取失败"""

    def __init__(self, dimension: str, detail: str = "") -> None:
        self.dimension = dimension
        super().__init__(f"[{dimension}] Insufficient data{f': {detail}' if detail else ''}")


class HeuristicWarning(DomainError):
    """启发式标记警告 — 非错误，提醒调用方此为代理指标"""

    def __init__(self, dimension: str, reason: str) -> None:
        self.dimension = dimension
        super().__init__(f"[{dimension}] ⚠️ HEURISTIC: {reason}")
