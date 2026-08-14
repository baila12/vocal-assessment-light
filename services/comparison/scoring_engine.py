"""
对比评分引擎

基于偏差计算结果进行加权评分：
- 音准 40%
- 节奏 30%
- 音量 15%
- 气息 15%

支持风格自适应权重调整
"""

import numpy as np
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

from .deviation_calculator import DeviationResult, FrameDeviation

logger = logging.getLogger(__name__)


@dataclass
class DimensionScore:
    """单维度评分"""
    score: float           # 0-100
    avg_deviation: float   # 平均偏差
    max_deviation: float   # 最大偏差
    problem_count: int     # 问题帧数量
    details: Dict          # 详细信息


@dataclass
class ComparisonScoreResult:
    """对比评分结果"""
    overall_score: float           # 综合评分 0-100
    level: str                     # 等级：优秀/良好/中等/及格/需改进
    confidence: float              # 对齐置信度

    dimensions: Dict[str, DimensionScore]  # 各维度评分

    suggestions: List[str]         # 改进建议
    problem_summary: Dict          # 问题汇总


class ComparisonScoringEngine:
    """
    对比评分引擎

    基于偏差计算结果进行加权评分
    """

    # 默认权重 — 经验值，与主评分系统保持一致
    DEFAULT_WEIGHTS = {
        'pitch': 0.40,
        'rhythm': 0.30,
        'volume': 0.15,
        'breath': 0.15
    }

    # 风格自适应权重 — 经验值，未经实验校准
    STYLE_WEIGHTS = {
        'pop': {
            'pitch': 0.40,
            'rhythm': 0.30,
            'volume': 0.15,
            'breath': 0.15
        },
        'classical': {
            'pitch': 0.50,
            'rhythm': 0.20,
            'volume': 0.20,
            'breath': 0.10
        },
        'folk': {
            'pitch': 0.35,
            'rhythm': 0.25,
            'volume': 0.20,
            'breath': 0.20
        },
        'rap': {
            'pitch': 0.20,
            'rhythm': 0.50,
            'volume': 0.20,
            'breath': 0.10
        }
    }

    # 等级阈值 — 经验值
    LEVEL_THRESHOLDS = [
        (90, '优秀'),
        (80, '良好'),
        (70, '中等'),
        (60, '及格'),
        (0, '需改进')
    ]

    def __init__(self, style: str = 'pop'):
        """
        Args:
            style: 演唱风格 (pop/classical/folk/rap)
        """
        self.style = style
        self.weights = self.STYLE_WEIGHTS.get(style, self.DEFAULT_WEIGHTS)

    def score(
        self,
        deviation_result: DeviationResult,
        confidence: float = 1.0,
        total_frames: int = 0
    ) -> ComparisonScoreResult:
        """
        计算评分

        Args:
            deviation_result: 偏差计算结果
            confidence: 对齐置信度
            total_frames: 总帧数

        Returns:
            ComparisonScoreResult
        """
        # 计算各维度评分
        pitch_score = self._score_pitch(deviation_result)
        rhythm_score = self._score_rhythm(deviation_result)
        volume_score = self._score_volume(deviation_result)
        breath_score = self._score_breath(deviation_result)

        dimensions = {
            'pitch': pitch_score,
            'rhythm': rhythm_score,
            'volume': volume_score,
            'breath': breath_score
        }

        # 计算综合评分
        overall_score = (
            pitch_score.score * self.weights['pitch'] +
            rhythm_score.score * self.weights['rhythm'] +
            volume_score.score * self.weights['volume'] +
            breath_score.score * self.weights['breath']
        )

        # 考虑对齐置信度
        overall_score = overall_score * confidence

        # 确定等级
        level = self._determine_level(overall_score)

        # 生成改进建议
        suggestions = self._generate_suggestions(dimensions)

        # 问题汇总
        problem_summary = self._summarize_problems(deviation_result)

        return ComparisonScoreResult(
            overall_score=round(overall_score, 1),
            level=level,
            confidence=confidence,
            dimensions=dimensions,
            suggestions=suggestions,
            problem_summary=problem_summary
        )

    def _score_pitch(self, deviation: DeviationResult) -> DimensionScore:
        """
        音准评分

        使用分段线性评分曲线（经验值）：
        - 0音分 -> 100分
        - 50音分 -> 75分
        - 100音分 -> 25分
        - 150音分以上 -> 10分（保底）
        """
        avg_cents = deviation.avg_pitch_cents
        max_cents = deviation.max_pitch_cents

        # 分段线性评分 — 经验值，未经实验校准
        if avg_cents <= 0:
            score = 100.0
        elif avg_cents <= 50:
            score = 100 - (avg_cents / 50) * 25   # 经验值: 每音分扣0.5分
        elif avg_cents <= 100:
            score = 75 - ((avg_cents - 50) / 50) * 50  # 经验值: 每音分扣1分
        else:
            score = max(10, 25 - ((avg_cents - 100) / 50) * 15)  # 经验值: 每音分扣0.3分

        # 保底10分
        score = max(10, score)

        # 统计问题帧
        problem_count = sum(
            1 for f in deviation.problem_frames
            if f.problem_type and 'pitch' in f.problem_type
        )

        return DimensionScore(
            score=round(score, 1),
            avg_deviation=round(avg_cents, 1),
            max_deviation=round(max_cents, 1),
            problem_count=problem_count,
            details={
                'avg_cents': round(avg_cents, 1),
                'max_cents': round(max_cents, 1),
                # v7.18 P1 (F2): 八度错误率 (独立信号, 折叠后评分已公平)
                'octave_error_rate': round(getattr(deviation, 'octave_error_rate', 0.0), 4),
            }
        )

    def _score_rhythm(self, deviation: DeviationResult) -> DimensionScore:
        """
        节奏评分

        基于平均节奏偏差（经验值）
        """
        avg_ms = deviation.avg_rhythm_ms

        # 50ms以内满分，每增加5ms扣1分 — 经验值
        if avg_ms <= 50:
            score = 100
        else:
            score = max(10, 100 - (avg_ms - 50) / 5)

        # 统计问题帧
        problem_count = sum(
            1 for f in deviation.problem_frames
            if f.problem_type and 'rhythm' in f.problem_type
        )

        return DimensionScore(
            score=round(score, 1),
            avg_deviation=round(avg_ms, 1),
            max_deviation=0.0,
            problem_count=problem_count,
            details={
                'avg_offset_ms': round(avg_ms, 1),
                # v7.18 P1 (F1): 整体速度比 (用户相对参考, 1.0=同速)
                'tempo_ratio': round(getattr(deviation, 'tempo_ratio', 1.0), 4),
            }
        )

    def _score_volume(self, deviation: DeviationResult) -> DimensionScore:
        """
        音量评分 — v7.18 P1 (F3): 动态匹配偏差 (z-score 归一化, 0-~2)

        avg_volume_percent 现为归一化能量包络的动态形状偏差 (录音增益差异已被 z-score 消除)。
        score = (1 - avg_deviation) × 100 — 偏差 0.1 → 90, 0.5 → 50, 1.0 → 0
        """
        avg_dev = deviation.avg_volume_percent

        score = max(0.0, (1.0 - avg_dev) * 100.0)

        return DimensionScore(
            score=round(score, 1),
            avg_deviation=round(avg_dev, 3),
            max_deviation=0.0,
            problem_count=0,
            details={
                'avg_dynamic_deviation': round(avg_dev, 3)
            }
        )

    def _score_breath(self, deviation: DeviationResult) -> DimensionScore:
        """
        气息评分

        基于气息稳定性
        """
        avg_stability = deviation.avg_breath_stability

        # 气息稳定性直接映射到评分
        score = avg_stability * 100

        # 统计问题帧
        problem_count = sum(
            1 for f in deviation.problem_frames
            if f.problem_type and 'breath' in f.problem_type
        )

        return DimensionScore(
            score=round(score, 1),
            avg_deviation=round(1 - avg_stability, 2),
            max_deviation=0.0,
            problem_count=problem_count,
            details={
                'avg_stability': round(avg_stability, 2)
            }
        )

    def _determine_level(self, score: float) -> str:
        """确定等级"""
        for threshold, level in self.LEVEL_THRESHOLDS:
            if score >= threshold:
                return level
        return '需改进'

    def _generate_suggestions(self, dimensions: Dict[str, DimensionScore]) -> List[str]:
        """生成改进建议"""
        suggestions = []

        # 音准建议
        pitch = dimensions['pitch']
        if pitch.score < 70:
            suggestions.append(
                f"音准偏差较大（平均{pitch.avg_deviation}音分），建议练习音阶，注意音高准确性"
            )
        elif pitch.score < 85:
            suggestions.append(
                f"音准整体良好，部分段落略有偏差，建议多听标准音频找准音高"
            )

        # 节奏建议
        rhythm = dimensions['rhythm']
        if rhythm.score < 70:
            suggestions.append(
                f"节奏偏差明显（平均{rhythm.avg_deviation}ms），建议跟着节拍器练习"
            )
        elif rhythm.score < 85:
            suggestions.append(
                "节奏基本正确，注意不要抢拍或拖拍"
            )

        # 音量建议
        volume = dimensions['volume']
        if volume.score < 70:
            suggestions.append(
                f"音量控制不稳定，建议练习气息支持，保持稳定的音量输出"
            )

        # 气息建议
        breath = dimensions['breath']
        if breath.score < 70:
            suggestions.append(
                "气息稳定性不足，建议练习腹式呼吸，增强气息控制能力"
            )

        # 如果表现优秀
        if not suggestions:
            suggestions.append("表现优秀！与标准音频高度匹配，继续保持练习")

        return suggestions

    def _summarize_problems(self, deviation: DeviationResult) -> Dict:
        """问题汇总"""
        summary = {
            'total_problem_frames': len(deviation.problem_frames),
            'pitch_high_count': 0,
            'pitch_low_count': 0,
            'rhythm_fast_count': 0,
            'rhythm_slow_count': 0,
            'breath_unstable_count': 0
        }

        for frame in deviation.problem_frames:
            if frame.problem_type:
                if 'pitch_high' in frame.problem_type:
                    summary['pitch_high_count'] += 1
                elif 'pitch_low' in frame.problem_type:
                    summary['pitch_low_count'] += 1
                elif frame.problem_type == 'rhythm_fast':
                    summary['rhythm_fast_count'] += 1
                elif frame.problem_type == 'rhythm_slow':
                    summary['rhythm_slow_count'] += 1
                elif frame.problem_type == 'breath_unstable':
                    summary['breath_unstable_count'] += 1

        return summary

    def to_dict(self, result: ComparisonScoreResult) -> Dict:
        """
        将评分结果转换为字典（用于JSON序列化）

        Args:
            result: 评分结果

        Returns:
            字典表示
        """
        return {
            'overall_score': result.overall_score,
            'level': result.level,
            'confidence': result.confidence,
            'dimensions': {
                name: {
                    'score': dim.score,
                    'avg_deviation': dim.avg_deviation,
                    'max_deviation': dim.max_deviation,
                    'problem_count': dim.problem_count,
                    'details': dim.details
                }
                for name, dim in result.dimensions.items()
            },
            'suggestions': result.suggestions,
            'problem_summary': result.problem_summary
        }
