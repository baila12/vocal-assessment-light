"""
节奏评分器 v5.10

基于onset密度和规律性的节奏评估，替代原来的beat_track方法
"""
from typing import Tuple
import logging

from services.audio_features_service import RhythmAlignmentResult
from services.scoring_config import RhythmThresholds, EmpiricalThresholds
from services.scoring import RhythmDiagnosis

logger = logging.getLogger(__name__)


class RhythmScorer:
    """
    节奏评分器 v5.10

    使用onset间隔变异系数(CV)评估节奏规律性，不再依赖beat_track。
    支持无伴奏独唱、弹性速度(Rubato)、非西方节奏体系。

    评估标准：
    - CV < 0.2: 节奏规律 → 高分
    - CV 0.2-0.3: 弹性节奏 → 中等分
    - CV > 0.5: 节奏混乱 → 低分
    """

    # onset密度正常范围 (events/second, 经验值)
    ONSET_DENSITY_MIN = 0.3   # 过慢 — 可能有大量无演唱段
    ONSET_DENSITY_MAX = 8.0   # 过快 — 可能是噪声或器乐密集段

    def __init__(self, thresholds: RhythmThresholds, empirical: EmpiricalThresholds = None):
        """
        初始化节奏评分器

        Args:
            thresholds: 节奏阈值配置
            empirical: 经验阈值配置
        """
        self.thresholds = thresholds
        self.empirical = empirical or EmpiricalThresholds()

    def calculate(
        self,
        rhythm_alignment: RhythmAlignmentResult
    ) -> Tuple[float, RhythmDiagnosis]:
        """
        计算节奏评分

        Args:
            rhythm_alignment: 节奏对齐分析结果

        Returns:
            (分数, 诊断信息)
        """
        diagnosis = RhythmDiagnosis()
        deviation = rhythm_alignment.avg_deviation_ratio

        # 使用配置计算基础分
        score, level = self.thresholds.get_score(deviation)
        diagnosis.level = level

        # onset不规则度惩罚 (CV-based, 阈值来自empirical配置)
        # v5.11: 人声onset自然比器乐更不规则,提高惩罚触发阈值
        irregularity = rhythm_alignment.irregularity
        irregularity_threshold = self.empirical.rhythm_irregularity_threshold
        if irregularity > irregularity_threshold:
            # 分级惩罚: 中等不规则轻罚,极度不规则重罚
            if irregularity > 1.2:
                penalty = min(25, 10 + (irregularity - 1.2) * 15)
                diagnosis.issues.append(f"节奏极不规则，onset间隔严重不稳定(CV={irregularity*100:.0f}%)")
            elif irregularity > 0.8:
                penalty = min(15, (irregularity - irregularity_threshold) * 25)
                diagnosis.issues.append(f"节奏不规则度较高，onset变异系数={irregularity*100:.0f}%")
            elif irregularity > 0.5:
                penalty = min(8, (irregularity - irregularity_threshold) * 15)
                diagnosis.issues.append(f"节奏略有波动，onset变异系数={irregularity*100:.0f}%")
            else:
                penalty = (irregularity - irregularity_threshold) * 10
            score -= penalty

        # onset密度检查（替代原来的BPM检查）
        onset_density = rhythm_alignment.beats_per_second
        if onset_density > 0:
            if onset_density < self.ONSET_DENSITY_MIN:
                diagnosis.issues.append(f"onset密度过低({onset_density:.1f} evt/s)，可能有大段无演唱区域")
            elif onset_density > self.ONSET_DENSITY_MAX:
                diagnosis.issues.append(f"onset密度异常高({onset_density:.1f} evt/s)，可能为非人声音频")

        score = max(0, min(100, score))

        diagnosis.score = score
        diagnosis.deviation_ratio = deviation

        if deviation > self.thresholds.pass_threshold:
            diagnosis.suggestions.append("建议配合节拍器练习，加强节奏感")
        if irregularity > 0.5:
            diagnosis.suggestions.append("节奏变动过大，建议先跟随原唱练习稳定节奏")

        return score, diagnosis
