"""
气息评分器

负责气息维度的评分计算和诊断生成
v4.1 专业气息评估体系
"""
from typing import Tuple
import logging

from services.audio_features_service import BreathStabilityResult
from services.scoring_config import BreathThresholds
from services.scoring.types import BreathDiagnosis

logger = logging.getLogger(__name__)


class BreathScorer:
    """
    气息评分器 v4.1

    核心改进：
    1. 使用专业气息综合得分（professional_breath_score）
    2. 区分艺术化起伏和随机抖动
    3. 正向加分为主，负向扣分为辅
    4. 四大细分维度：长音支撑(40%)、动态控制(25%)、气口设计(20%)、气声技巧(15%)

    专业标准：
    - 满分：专业气息控制能力（长音支撑、弱唱质量、可控气声）
    - 良好：气息稳定，无明显问题
    - 合格：有改进空间
    - 底线：严重漏气(HNR<3dB)
    """

    def __init__(self, thresholds: BreathThresholds):
        """
        初始化气息评分器

        Args:
            thresholds: 气息阈值配置
        """
        self.thresholds = thresholds

    def calculate(
        self,
        breath_stability: BreathStabilityResult
    ) -> Tuple[float, BreathDiagnosis]:
        """
        计算气息评分

        Args:
            breath_stability: 气息稳定性分析结果

        Returns:
            (分数, 诊断信息)
        """
        diagnosis = BreathDiagnosis()

        # 使用专业气息综合得分
        professional_score = breath_stability.professional_breath_score

        # 如果专业得分有效，使用它
        if professional_score > 0:
            score = professional_score
        else:
            # 兼容旧逻辑 - 使用配置化阈值
            fluctuation = breath_stability.rms_fluctuation
            score, level = self.thresholds.get_score(fluctuation)
            diagnosis.level = level

        # 填充细分维度得分
        diagnosis.long_note_support = breath_stability.long_note_support_score
        diagnosis.dynamic_control = breath_stability.dynamic_control_score
        diagnosis.breath_design = breath_stability.breath_design_score
        diagnosis.breath_technique = breath_stability.breath_technique_score

        # 专业能力标记
        diagnosis.is_artistic = breath_stability.is_artistic_fluctuation
        diagnosis.has_controlled_breathiness = breath_stability.controlled_breathiness > 30

        # 生成诊断信息
        if breath_stability.is_artistic_fluctuation:
            diagnosis.positives.append("检测到艺术化的强弱起伏处理")

        # 长音评估
        if breath_stability.long_note_count > 0:
            if breath_stability.long_note_support_score > 80:
                diagnosis.positives.append(f"长音气息支撑优秀({breath_stability.long_note_count}处)")
                diagnosis.long_note_bonus = 5
            elif breath_stability.long_note_support_score > 60:
                diagnosis.positives.append(f"长音气息支撑良好({breath_stability.long_note_count}处)")
        # 没有长音不扣分，只是没有加分

        # 弱唱评估
        if breath_stability.soft_segment_count > 0:
            if breath_stability.soft_singing_quality > 70:
                diagnosis.positives.append("弱唱气息控制优秀")
                diagnosis.soft_singing_bonus = 5
            elif breath_stability.soft_singing_quality > 50:
                diagnosis.positives.append("弱唱气息控制良好")

        # 气口设计评估
        if breath_stability.clean_breath_count > 0:
            diagnosis.positives.append(f"无痕换气{breath_stability.clean_breath_count}处")

        # 气声技巧评估
        if breath_stability.controlled_breathiness > 50:
            diagnosis.positives.append("气声技巧运用得当")
        elif breath_stability.uncontrolled_leak > 30:
            diagnosis.issues.append("存在无效漏气")
            diagnosis.suggestions.append("建议加强声带闭合训练，减少漏气")

        # 动态范围评估
        if breath_stability.dynamic_range > 30:
            diagnosis.positives.append(f"动态范围宽广({breath_stability.dynamic_range:.0f}dB)")

        # 严重问题（仅严重问题才放到issues）
        if breath_stability.breath_breaks > 3:
            score -= min(15, (breath_stability.breath_breaks - 3) * 3)
            diagnosis.issues.append(f"存在{breath_stability.breath_breaks}处气息断层")

        score = max(0, min(100, score))

        diagnosis.score = score
        diagnosis.fluctuation = breath_stability.rms_fluctuation

        # 更新等级
        if score >= 85:
            diagnosis.level = "专业级"
        elif score >= 70:
            diagnosis.level = "良好"
        elif score >= 55:
            diagnosis.level = "合格"
        else:
            diagnosis.level = "待改进"

        # 建议生成
        if breath_stability.long_note_support_score < 60:
            diagnosis.suggestions.append("建议进行长音气息支撑训练")
        if breath_stability.dynamic_control_score < 60:
            diagnosis.suggestions.append("建议练习渐强渐弱的气息控制")
        if score < 60:
            diagnosis.suggestions.append("建议进行腹式呼吸训练，增强气息支撑")

        return score, diagnosis
