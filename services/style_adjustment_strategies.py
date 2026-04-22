"""
风格调整策略模块
使用策略模式重构风格调整逻辑，消除 if-elif 分支
"""
from typing import Callable, Dict, Protocol
from dataclasses import dataclass
from functools import wraps
import logging
import threading

logger = logging.getLogger(__name__)


class StyleProfileProtocol(Protocol):
    """风格配置协议"""
    style: str
    pitch_tolerance: float
    rhythm_tolerance: float
    breath_weight: float
    artistry_weight: float


# 定义调整函数类型
ScoreAdjuster = Callable[[float, StyleProfileProtocol], float]

# 基准阈值
BASE_PITCH_TOLERANCE = 20.0
BASE_RHYTHM_TOLERANCE = 0.25


class StyleAdjustmentRegistry:
    """
    风格调整策略注册表

    使用装饰器模式注册各风格的调整策略
    支持运行时动态注册
    """

    _strategies: Dict[str, Dict[str, ScoreAdjuster]] = {
        'pitch': {},
        'rhythm': {},
        'breath': {},
        'technique': {},
        'artistry': {}
    }
    _lock: threading.Lock = threading.Lock()  # 线程安全锁

    @classmethod
    def register(cls, dimension: str, style: str):
        """
        装饰器：注册调整策略

        Args:
            dimension: 维度名称 (pitch/rhythm/breath/technique/artistry)
            style: 风格名称

        Returns:
            装饰器函数

        示例:
            @StyleAdjustmentRegistry.register('pitch', 'ballad')
            def adjust_pitch_ballad(score, profile):
                ...
        """
        def decorator(func: ScoreAdjuster) -> ScoreAdjuster:
            with cls._lock:
                cls._strategies[dimension][style] = func
            logger.debug(f"[StyleAdjustmentRegistry] Registered: {dimension}/{style}")
            return func
        return decorator

    @classmethod
    def get_adjustment(cls, dimension: str, style: str) -> ScoreAdjuster:
        """
        获取调整策略

        Args:
            dimension: 维度名称
            style: 风格名称

        Returns:
            调整函数，如果未注册则返回恒等函数
        """
        with cls._lock:
            return cls._strategies[dimension].get(
                style,
                lambda score, profile: score  # 默认：无调整
            )

    @classmethod
    def register_default(cls, dimension: str, func: ScoreAdjuster):
        """
        注册默认策略

        Args:
            dimension: 维度名称
            func: 默认调整函数
        """
        with cls._lock:
            cls._strategies[dimension]['__default__'] = func

    @classmethod
    def list_strategies(cls) -> Dict[str, list]:
        """列出所有已注册的策略"""
        with cls._lock:
            return {
                dim: list(styles.keys())
                for dim, styles in cls._strategies.items()
            }


# ============== 音准调整策略 ==============

@StyleAdjustmentRegistry.register('pitch', 'ballad')
def adjust_pitch_ballad(score: float, profile: StyleProfileProtocol) -> float:
    """
    抒情风格音准调整 - 严格但允许情感化处理

    特点：
    - 音准要求严格
    - 但允许情感化装饰音
    - 高分段不额外扣分
    """
    tolerance_factor = profile.pitch_tolerance / BASE_PITCH_TOLERANCE

    if score >= 80:
        # 高分段不额外扣分（精准音准已被认可）
        adjusted = score
    elif score >= 60:
        # 中分段：轻微调整
        adjusted = score * (0.95 + tolerance_factor * 0.05)
    else:
        # 低分段：标准处理
        adjusted = score * tolerance_factor

    return min(100, max(0, adjusted))


@StyleAdjustmentRegistry.register('pitch', 'rock')
def adjust_pitch_rock(score: float, profile: StyleProfileProtocol) -> float:
    """
    摇滚风格音准调整 - 更宽松

    特点：
    - 允许嘶吼和力量表达
    - 音准容差大
    - 低分段显著提升
    """
    tolerance_factor = profile.pitch_tolerance / BASE_PITCH_TOLERANCE

    if tolerance_factor > 1.0:
        if score < 70:
            # 低分段：显著提升
            adjusted = score + (70 - score) * (tolerance_factor - 1.0) * 0.4
        else:
            # 高分段：适度提升
            adjusted = score + (100 - score) * (tolerance_factor - 1.0) * 0.2
    else:
        adjusted = score

    return min(100, max(0, adjusted))


@StyleAdjustmentRegistry.register('pitch', 'upbeat')
def adjust_pitch_upbeat(score: float, profile: StyleProfileProtocol) -> float:
    """
    快歌风格音准调整 - 节奏优先

    特点：
    - 节奏优先，音准适度放宽
    - 音准容差较大
    """
    tolerance_factor = profile.pitch_tolerance / BASE_PITCH_TOLERANCE

    if tolerance_factor > 1.0:
        if score < 70:
            adjusted = score + (70 - score) * (tolerance_factor - 1.0) * 0.35
        else:
            adjusted = score + (100 - score) * (tolerance_factor - 1.0) * 0.15
    else:
        adjusted = score

    return min(100, max(0, adjusted))


@StyleAdjustmentRegistry.register('pitch', 'rb_jazz')
def adjust_pitch_rb_jazz(score: float, profile: StyleProfileProtocol) -> float:
    """
    R&B/爵士风格音准调整 - 允许即兴变化

    特点：
    - 允许即兴变化和装饰音
    - 即兴风格加分
    """
    tolerance_factor = profile.pitch_tolerance / BASE_PITCH_TOLERANCE

    if tolerance_factor > 1.0:
        if score < 70:
            adjusted = score + (70 - score) * (tolerance_factor - 1.0) * 0.3
        else:
            adjusted = score + (100 - score) * (tolerance_factor - 1.0) * 0.15
    else:
        adjusted = score

    # R&B/爵士：即兴风格加分
    if score >= 60:
        adjusted += 3.0

    return min(100, max(0, adjusted))


@StyleAdjustmentRegistry.register('pitch', 'folk')
def adjust_pitch_folk(score: float, profile: StyleProfileProtocol) -> float:
    """
    民谣风格音准调整 - 自然质朴

    特点：
    - 音准要求较高
    - 允许自然情感表达
    """
    tolerance_factor = profile.pitch_tolerance / BASE_PITCH_TOLERANCE

    if score >= 80:
        adjusted = score
    elif score >= 60:
        adjusted = score * (0.97 + tolerance_factor * 0.03)
    else:
        adjusted = score * tolerance_factor

    return min(100, max(0, adjusted))


@StyleAdjustmentRegistry.register('pitch', 'pop')
def adjust_pitch_pop(score: float, profile: StyleProfileProtocol) -> float:
    """
    流行风格音准调整 - 标准处理

    特点：
    - 均衡评分
    - 适度调整
    """
    tolerance_factor = profile.pitch_tolerance / BASE_PITCH_TOLERANCE

    if tolerance_factor > 1.0:
        adjusted = score + (100 - score) * (tolerance_factor - 1.0) * 0.1
    else:
        adjusted = score

    return min(100, max(0, adjusted))


# ============== 节奏调整策略 ==============

@StyleAdjustmentRegistry.register('rhythm', 'ballad')
def adjust_rhythm_ballad(score: float, profile: StyleProfileProtocol) -> float:
    """
    抒情风格节奏调整 - 允许rubato

    特点：
    - 允许自由速度
    - 艺术化节奏处理加分
    """
    if profile.rhythm_tolerance > BASE_RHYTHM_TOLERANCE:
        # 允许自由速度：节奏评分更宽松
        if score >= 70:
            adjusted = score + (100 - score) * 0.15
        elif score >= 50:
            adjusted = score + (70 - score) * 0.1
        else:
            adjusted = score
    else:
        adjusted = score

    return min(100, max(0, adjusted))


@StyleAdjustmentRegistry.register('rhythm', 'upbeat')
def adjust_rhythm_upbeat(score: float, profile: StyleProfileProtocol) -> float:
    """
    快歌风格节奏调整 - 要求精准

    特点：
    - 节奏要求严格
    - 完美节奏加分
    """
    tolerance_factor = profile.rhythm_tolerance / BASE_RHYTHM_TOLERANCE

    if tolerance_factor < 1.0:
        # 快歌/舞曲：要求精准
        if score >= 85:
            adjusted = score + 2.0  # 精准节奏额外加分
        elif score >= 70:
            adjusted = score
        else:
            adjusted = score * (0.9 + tolerance_factor * 0.1)
    else:
        adjusted = score

    # 快歌完美节奏加分
    if score >= 90:
        adjusted += 3.0

    return min(100, max(0, adjusted))


@StyleAdjustmentRegistry.register('rhythm', 'rock')
def adjust_rhythm_rock(score: float, profile: StyleProfileProtocol) -> float:
    """
    摇滚风格节奏调整 - 力量感优先

    特点：
    - 节奏稳定性重要
    - 力量表达加分
    """
    if score >= 70:
        adjusted = score + 2.0
    else:
        adjusted = score

    return min(100, max(0, adjusted))


@StyleAdjustmentRegistry.register('rhythm', 'rb_jazz')
def adjust_rhythm_rb_jazz(score: float, profile: StyleProfileProtocol) -> float:
    """
    R&B/爵士风格节奏调整 - 允许swing/groove

    特点：
    - 允许swing和groove
    - groove加分
    """
    if score >= 65:
        adjusted = score + 2.0  # groove加分
    else:
        adjusted = score

    return min(100, max(0, adjusted))


@StyleAdjustmentRegistry.register('rhythm', 'folk')
def adjust_rhythm_folk(score: float, profile: StyleProfileProtocol) -> float:
    """
    民谣风格节奏调整 - 叙事性自由

    特点：
    - 允许叙事性自由
    - 情感表达优先
    """
    if profile.rhythm_tolerance > BASE_RHYTHM_TOLERANCE:
        if score >= 60:
            adjusted = score + (100 - score) * 0.1
        else:
            adjusted = score
    else:
        adjusted = score

    return min(100, max(0, adjusted))


@StyleAdjustmentRegistry.register('rhythm', 'pop')
def adjust_rhythm_pop(score: float, profile: StyleProfileProtocol) -> float:
    """
    流行风格节奏调整 - 标准处理
    """
    return min(100, max(0, score))


# ============== 气息调整策略 ==============

@StyleAdjustmentRegistry.register('breath', 'ballad')
def adjust_breath_ballad(score: float, profile: StyleProfileProtocol) -> float:
    """
    抒情风格气息调整 - 气息控制是核心

    特点：
    - 气息控制要求高
    - 优秀气息控制加分
    """
    if score >= 75:
        adjusted = score + 5.0  # 优秀气息控制加分
    else:
        adjusted = score * 1.05

    return min(100, max(0, adjusted))


@StyleAdjustmentRegistry.register('breath', 'upbeat')
def adjust_breath_upbeat(score: float, profile: StyleProfileProtocol) -> float:
    """
    快歌风格气息调整 - 气息支撑更重要

    特点：
    - 高强度演唱
    - 气息支撑加分
    """
    if score >= 70:
        adjusted = score + 3.0
    else:
        adjusted = score

    return min(100, max(0, adjusted))


@StyleAdjustmentRegistry.register('breath', 'rock')
def adjust_breath_rock(score: float, profile: StyleProfileProtocol) -> float:
    """
    摇滚风格气息调整 - 气息爆发力

    特点：
    - 爆发力是关键
    - 爆发力加分
    """
    if score >= 65:
        adjusted = score + 4.0  # 爆发力加分
    else:
        adjusted = score

    return min(100, max(0, adjusted))


@StyleAdjustmentRegistry.register('breath', 'rb_jazz')
def adjust_breath_rb_jazz(score: float, profile: StyleProfileProtocol) -> float:
    """
    R&B/爵士风格气息调整 - 气息灵活性
    """
    adjusted = score + 2.0  # 灵活性加分
    return min(100, max(0, adjusted))


@StyleAdjustmentRegistry.register('breath', 'folk')
def adjust_breath_folk(score: float, profile: StyleProfileProtocol) -> float:
    """
    民谣风格气息调整 - 气息与情感结合
    """
    if score >= 70:
        adjusted = score + 4.0
    else:
        adjusted = score * 1.03

    return min(100, max(0, adjusted))


@StyleAdjustmentRegistry.register('breath', 'pop')
def adjust_breath_pop(score: float, profile: StyleProfileProtocol) -> float:
    """
    流行风格气息调整 - 标准处理
    """
    return min(100, max(0, score))


# ============== 技术调整策略 ==============

@StyleAdjustmentRegistry.register('technique', 'rock')
def adjust_technique_rock(score: float, profile: StyleProfileProtocol) -> float:
    """
    摇滚风格技术调整 - 力量感加分
    """
    if score >= 60:
        adjusted = score + 5.0
    else:
        adjusted = score

    return min(100, max(0, adjusted))


@StyleAdjustmentRegistry.register('technique', 'rb_jazz')
def adjust_technique_rb_jazz(score: float, profile: StyleProfileProtocol) -> float:
    """
    R&B/爵士风格技术调整 - 即兴技巧加分
    """
    if score >= 50:
        adjusted = score + 6.0  # 技巧多样性加分
    else:
        adjusted = score + 3.0

    return min(100, max(0, adjusted))


@StyleAdjustmentRegistry.register('technique', 'ballad')
def adjust_technique_ballad(score: float, profile: StyleProfileProtocol) -> float:
    """
    抒情风格技术调整 - 细腻技巧
    """
    if score >= 70:
        adjusted = score + 3.0
    else:
        adjusted = score

    return min(100, max(0, adjusted))


@StyleAdjustmentRegistry.register('technique', 'folk')
def adjust_technique_folk(score: float, profile: StyleProfileProtocol) -> float:
    """
    民谣风格技术调整 - 自然质朴
    """
    adjusted = score + 2.0  # 自然感加分
    return min(100, max(0, adjusted))


@StyleAdjustmentRegistry.register('technique', 'upbeat')
def adjust_technique_upbeat(score: float, profile: StyleProfileProtocol) -> float:
    """
    快歌风格技术调整 - 技术稳定性
    """
    if score >= 65:
        adjusted = score + 3.0
    else:
        adjusted = score

    return min(100, max(0, adjusted))


@StyleAdjustmentRegistry.register('technique', 'pop')
def adjust_technique_pop(score: float, profile: StyleProfileProtocol) -> float:
    """
    流行风格技术调整
    """
    adjusted = score + 1.0
    return min(100, max(0, adjusted))


# ============== 艺术表现调整策略 ==============

@StyleAdjustmentRegistry.register('artistry', 'folk')
def adjust_artistry_folk(score: float, profile: StyleProfileProtocol) -> float:
    """
    民谣风格艺术表现调整 - 情感表达最重要
    """
    if score >= 60:
        adjusted = score + 8.0  # 情感加分
    else:
        adjusted = score + 4.0

    return min(100, max(0, adjusted))


@StyleAdjustmentRegistry.register('artistry', 'ballad')
def adjust_artistry_ballad(score: float, profile: StyleProfileProtocol) -> float:
    """
    抒情风格艺术表现调整 - 情感深度
    """
    if score >= 60:
        adjusted = score + 6.0
    else:
        adjusted = score + 3.0

    return min(100, max(0, adjusted))


@StyleAdjustmentRegistry.register('artistry', 'rb_jazz')
def adjust_artistry_rb_jazz(score: float, profile: StyleProfileProtocol) -> float:
    """
    R&B/爵士风格艺术表现调整 - 即兴艺术性
    """
    if score >= 55:
        adjusted = score + 7.0
    else:
        adjusted = score + 3.0

    return min(100, max(0, adjusted))


@StyleAdjustmentRegistry.register('artistry', 'rock')
def adjust_artistry_rock(score: float, profile: StyleProfileProtocol) -> float:
    """
    摇滚风格艺术表现调整 - 态度和能量
    """
    if score >= 50:
        adjusted = score + 5.0
    else:
        adjusted = score + 2.0

    return min(100, max(0, adjusted))


@StyleAdjustmentRegistry.register('artistry', 'upbeat')
def adjust_artistry_upbeat(score: float, profile: StyleProfileProtocol) -> float:
    """
    快歌风格艺术表现调整 - 舞台表现力
    """
    if score >= 55:
        adjusted = score + 4.0
    else:
        adjusted = score

    return min(100, max(0, adjusted))


@StyleAdjustmentRegistry.register('artistry', 'pop')
def adjust_artistry_pop(score: float, profile: StyleProfileProtocol) -> float:
    """
    流行风格艺术表现调整
    """
    adjusted = score + 2.0
    return min(100, max(0, adjusted))


# ============== 情绪匹配计算 ==============

# 风格与情绪的最佳匹配
MOOD_STYLE_MATCH: Dict[str, list] = {
    'ballad': ['romantic', 'sad', 'sentimental'],
    'folk': ['sentimental', 'relaxing', 'romantic'],
    'rock': ['energetic', 'epic', 'dark'],
    'upbeat': ['happy', 'energetic', 'uplifting'],
    'rb_jazz': ['romantic', 'glamorous', 'relaxing'],
    'pop': ['happy', 'romantic', 'energetic'],
}


def calculate_mood_bonus(style: str, mood: str) -> float:
    """
    计算情绪匹配度加分

    Args:
        style: 风格名称
        mood: 情绪类型

    Returns:
        加分值
    """
    best_moods = MOOD_STYLE_MATCH.get(style, [])
    if mood.lower() in best_moods:
        return 3.0  # 情绪与风格完美匹配
    return 0.0
