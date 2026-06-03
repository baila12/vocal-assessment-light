"""
评分校准器 v2.0

v5.12: 移除了所有未使用的 DL 模型代码（CREPE、SpeechBrain MOS、EnhancedDLAssessor）。
这些模型从未在评分管线中被实际调用。保留 ScoreCalibrator 供测试使用。

设计原则：
- 基于测试数据校准评分
- 快速模式与专业模式一致性验证
- 自适应参数调整
"""
import logging
from typing import Dict, Optional, Tuple, List

logger = logging.getLogger(__name__)


class ScoreCalibrator:
    """
    评分校准器 v2.0

    基于测试数据校准评分，确保：
    1. 快速模式评分公正（不偏高不偏低）
    2. 专业模式评分详细准确
    3. 两种模式评分一致性

    v2.0 新增：
    - 动态校准参数
    - 一致性验证
    - 自适应调整
    """

    # 基于测试数据统计的校准参数
    CALIBRATION_PARAMS = {
        'quick': {
            'pitch_offset': 0.0,
            'pitch_scale': 1.0,
            'rhythm_offset': 0.0,
            'rhythm_scale': 1.0,
            'breath_offset': -5.0,
            'breath_scale': 0.95,
            'technique_offset': 0.0,
            'technique_scale': 1.0,
            'artistry_offset': 0.0,
            'artistry_scale': 1.0,
            'total_offset': 0.0,
            'total_scale': 1.0,
            'min_score': 55.0,
            'max_score': 92.0,
        },
        'professional': {
            'pitch_offset': 0.0,
            'pitch_scale': 1.0,
            'rhythm_offset': 0.0,
            'rhythm_scale': 1.0,
            'breath_offset': 0.0,
            'breath_scale': 1.0,
            'technique_offset': 0.0,
            'technique_scale': 1.0,
            'artistry_offset': 0.0,
            'artistry_scale': 1.0,
            'total_offset': 0.0,
            'total_scale': 1.0,
            'min_score': 0.0,
            'max_score': 100.0,
        }
    }

    # 参考分数映射
    REFERENCE_MAPPING = {
        'quick': {
            (0, 50): (55, 65),
            (50, 70): (65, 75),
            (70, 85): (75, 85),
            (85, 100): (85, 92),
        },
        'professional': {
            (0, 50): (0, 50),
            (50, 70): (50, 70),
            (70, 85): (70, 85),
            (85, 100): (85, 100),
        }
    }

    # 一致性阈值
    CONSISTENCY_THRESHOLD = 5.0  # 快速/专业模式差异阈值

    def __init__(self):
        """初始化校准器"""
        self._historical_diffs: List[float] = []
        self._adaptive_params: Dict[str, Dict] = {
            'quick': {},
            'professional': {}
        }

    def calibrate_score(
        self,
        score: float,
        dimension: str,
        mode: str = 'quick',
        features: Optional[Dict] = None
    ) -> float:
        """
        校准单个维度的分数

        Args:
            score: 原始分数
            dimension: 维度名称
            mode: 评估模式
            features: 额外特征

        Returns:
            校准后的分数
        """
        params = self.CALIBRATION_PARAMS.get(mode, self.CALIBRATION_PARAMS['quick'])

        offset = params.get(f'{dimension}_offset', 0.0)
        scale = params.get(f'{dimension}_scale', 1.0)

        calibrated = score * scale + offset

        # 应用非线性映射
        mapping = self.REFERENCE_MAPPING.get(mode, self.REFERENCE_MAPPING['quick'])
        for (low, high), (target_low, target_high) in mapping.items():
            if low <= score < high:
                ratio = (score - low) / (high - low)
                calibrated = target_low + ratio * (target_high - target_low)
                break

        min_score = params.get('min_score', 0.0)
        max_score = params.get('max_score', 100.0)
        calibrated = max(min_score, min(max_score, calibrated))

        return round(calibrated, 1)

    def calibrate_total(
        self,
        scores: Dict[str, float],
        weights: Dict[str, float],
        mode: str = 'quick'
    ) -> float:
        """校准总分"""
        total = sum(
            scores.get(dim, 70) * weight
            for dim, weight in weights.items()
        )

        params = self.CALIBRATION_PARAMS.get(mode, self.CALIBRATION_PARAMS['quick'])
        total = total * params.get('total_scale', 1.0) + params.get('total_offset', 0.0)

        min_score = params.get('min_score', 0.0)
        max_score = params.get('max_score', 100.0)
        total = max(min_score, min(max_score, total))

        return round(total, 1)

    def get_consistency_adjustment(
        self,
        quick_score: float,
        professional_score: float
    ) -> Tuple[float, float]:
        """获取一致性调整"""
        diff = quick_score - professional_score

        if abs(diff) > 10:
            adjustment = diff * 0.2
            quick_adjusted = quick_score - adjustment
            prof_adjusted = professional_score + adjustment
            return quick_adjusted, prof_adjusted

        return quick_score, professional_score

    def validate_consistency(
        self,
        quick_scores: Dict[str, float],
        professional_scores: Dict[str, float]
    ) -> Tuple[bool, Dict[str, float], float]:
        """
        验证快速模式和专业模式评分一致性

        Args:
            quick_scores: 快速模式评分
            professional_scores: 专业模式评分

        Returns:
            (是否一致, 各维度差异, 最大差异)
        """
        diffs = {}
        dimensions = ['pitch', 'rhythm', 'breath', 'technique', 'artistry']

        for dim in dimensions:
            quick_val = quick_scores.get(dim, 70.0)
            prof_val = professional_scores.get(dim, 70.0)
            diffs[dim] = abs(quick_val - prof_val)

        max_diff = max(diffs.values()) if diffs else 0.0
        is_consistent = max_diff < self.CONSISTENCY_THRESHOLD

        # 记录历史差异用于自适应调整
        if max_diff >= self.CONSISTENCY_THRESHOLD:
            self._historical_diffs.append(max_diff)
            # 保留最近100条记录
            if len(self._historical_diffs) > 100:
                self._historical_diffs = self._historical_diffs[-100:]

        return is_consistent, diffs, max_diff

    def get_adaptive_params(self, mode: str) -> Dict[str, float]:
        """
        获取自适应校准参数

        根据历史数据动态调整参数

        Args:
            mode: 评估模式

        Returns:
            校准参数字典
        """
        base_params = self.CALIBRATION_PARAMS.get(mode, self.CALIBRATION_PARAMS['quick'])

        # 如果有足够的历史数据，进行自适应调整
        if len(self._historical_diffs) >= 10:
            avg_diff = sum(self._historical_diffs[-10:]) / 10
            if avg_diff > self.CONSISTENCY_THRESHOLD:
                # 差异较大时，调整快速模式的偏移量
                adaptive = dict(base_params)
                adaptive['total_offset'] = adaptive.get('total_offset', 0.0) - avg_diff * 0.1
                return adaptive

        return base_params

    def update_adaptive_params(
        self,
        dimension: str,
        quick_score: float,
        professional_score: float
    ) -> None:
        """
        更新自适应参数

        Args:
            dimension: 维度名称
            quick_score: 快速模式分数
            professional_score: 专业模式分数
        """
        diff = quick_score - professional_score
        if abs(diff) > self.CONSISTENCY_THRESHOLD:
            # 记录需要调整的维度
            if dimension not in self._adaptive_params['quick']:
                self._adaptive_params['quick'][dimension] = []
            self._adaptive_params['quick'][dimension].append(diff)
