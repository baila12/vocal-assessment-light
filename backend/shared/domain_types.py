"""
共享内核 — 领域基础类型

零框架依赖，所有类型均为不可变值对象。
"""

from dataclasses import dataclass
from typing import NewType, Annotated
from pydantic import Field

# 正浮点数 (编译期约束)
PositiveFloat = Annotated[float, Field(gt=0)]

# 评分值 0-100 (编译期约束)
ScoreValue = Annotated[float, Field(ge=0, le=100)]


@dataclass(frozen=True)
class ScoreLevel:
    """分数等级映射 (不变, v6.3 一致)"""
    label: str       # 专业级/优秀/良好/中等/及格/待改进
    grade: str       # S/A/B/C/D/E
    color: str       # Tailwind CSS 颜色

    @staticmethod
    def from_score(total: float) -> "ScoreLevel":
        if total >= 88:
            return ScoreLevel("专业级", "S", "#22c55e")
        if total >= 78:
            return ScoreLevel("优秀", "A", "#3b82f6")
        if total >= 62:
            return ScoreLevel("良好", "B", "#10b981")
        if total >= 45:
            return ScoreLevel("中等", "C", "#f59e0b")
        if total >= 25:
            return ScoreLevel("及格", "D", "#f97316")
        return ScoreLevel("待改进", "E", "#ef4444")
