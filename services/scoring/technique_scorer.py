"""
发声技术评分器

负责发声技术维度的评分计算和诊断生成
v5.6 - 支持混合音频检测，调整HNR评估策略
"""
from typing import Tuple
import logging

from services.audio_features_service import VocalTechniqueResult
from services.scoring_config import TechniqueThresholds, EmpiricalThresholds
from services.scoring.types import TechniqueDiagnosis

logger = logging.getLogger(__name__)


class TechniqueScorer:
    """
    发声技术评分器

    组成部分：
    - HNR (声带闭合): 40%
    - CPP (声带闭合质量): 30%
    - 技巧完成度: 30%
    """

    def __init__(self, thresholds: TechniqueThresholds, singing_style: str = 'pop',
                 empirical: EmpiricalThresholds = None):
        """
        初始化发声技术评分器

        Args:
            thresholds: 技术阈值配置
            singing_style: 唱法类型 (pop/classical/folk/rap)
            empirical: 经验阈值配置
        """
        self.thresholds = thresholds
        self.singing_style = singing_style
        self.empirical = empirical or EmpiricalThresholds()

    def calculate(
        self,
        hnr: float,
        cpp: float,
        technique: VocalTechniqueResult,
        is_mixed_audio: bool = False,
        mixed_audio_confidence: float = 0.0
    ) -> Tuple[float, TechniqueDiagnosis]:
        """
        计算发声技术评分

        Args:
            hnr: 谐波噪声比
            cpp: 声门闭合周期峰值
            technique: 发声技巧分析结果
            is_mixed_audio: 是否为混合音频（带伴奏）
            mixed_audio_confidence: 混合音频检测置信度

        Returns:
            (分数, 诊断信息)
        """
        diagnosis = TechniqueDiagnosis()

        # HNR 评分 - 根据唱法和混合音频状态调整标准
        hnr_score = self._calculate_hnr_score(hnr, technique.technique_score, is_mixed_audio)

        # CPP 评分 - 根据唱法调整标准
        cpp_score = self._calculate_cpp_score(cpp, technique.technique_score)

        # 技巧完成度
        technique_score = technique.technique_score

        # 加权平均
        score = (
            hnr_score * self.thresholds.hnr_weight +
            cpp_score * self.thresholds.cpp_weight +
            technique_score * self.thresholds.technique_weight
        )

        # 诊断
        self._generate_diagnosis(diagnosis, hnr, technique, is_mixed_audio)

        score = max(0, min(100, score))

        diagnosis.score = score
        diagnosis.hnr = hnr
        diagnosis.cpp = cpp
        diagnosis.vibrato_quality = technique.vibrato_quality
        diagnosis.is_mixed_audio = is_mixed_audio

        if score >= 80:
            diagnosis.level = "专业级"
        elif score >= 70:
            diagnosis.level = "良好"
        elif score >= 60:
            diagnosis.level = "合格"
        else:
            diagnosis.level = "待改进"

        return score, diagnosis

    def _calculate_hnr_score(self, hnr: float, technique_score: float, is_mixed_audio: bool = False) -> float:
        """
        计算 HNR 分数

        注意：轻柔唱法/气声唱法的HNR天然较低（6-12dB是正常的）
        混合音频（带伴奏）的HNR会更低，因为伴奏会被误判为噪声

        参考：
        - 美声: 18-25dB (完全闭合)
        - 流行实声: 12-18dB
        - 流行轻柔/气声: 6-12dB (这是艺术选择，不是技术问题)
        - 混合音频: HNR通常偏低 30-50%，需要调整标准
        """
        # 混合音频修正系数：混合音频的HNR通常偏低 (经验值，来自empirical配置)
        if is_mixed_audio:
            # 对于混合音频，使用更宽松的标准
            # 伴奏会增加"噪声"能量，导致HNR降低
            correction = self.empirical.hnr_mixed_correction
            hnr_adjusted = hnr * correction
            logger.info(f"混合音频检测: 原始HNR={hnr:.1f}, 调整后HNR={hnr_adjusted:.1f} (修正系数={correction})")
        else:
            hnr_adjusted = hnr

        if self.singing_style == 'classical':
            # 美声：HNR > 28dB 满分 (v5.19: 20→28)
            return min(100, hnr_adjusted / 28 * 100)
        elif self.singing_style == 'folk':
            # 民族：HNR 18-25dB 满分 (v5.19: 提升天花板)
            if hnr_adjusted >= 25:
                return 100
            elif hnr_adjusted >= 18:
                return 80 + (hnr_adjusted - 18) * 2.86
            elif hnr_adjusted >= 12:
                return 60 + (hnr_adjusted - 12) * 3.33
            else:
                return max(30, hnr_adjusted / 12 * 60)
        else:
            # v6.1 流行: 降低高技巧阈值 (v5.19: 70; v6.1: technique_score 0-85, 35 合理)
            if technique_score >= 35:
                # 检测到足够技巧，HNR低可能是艺术选择（气声唱法）
                if hnr_adjusted >= 22:      # v5.19: 12→22
                    return 100
                elif hnr_adjusted >= 14:    # v5.19: 8→14
                    return 80 + (hnr_adjusted - 14) * 2.5
                elif hnr_adjusted >= 8:
                    return 60 + (hnr_adjusted - 8) * 3.33
                elif hnr_adjusted >= 5:
                    return 45 + (hnr_adjusted - 5) * 5
                else:
                    return max(10, hnr_adjusted / 5 * 45)
            else:
                # 低技巧分，可能是真正的技术问题
                if hnr_adjusted >= 22:      # v5.19: 15→22
                    return 100
                elif hnr_adjusted >= 14:    # v5.19: 10→14
                    return 75 + (hnr_adjusted - 14) * 3.13
                elif hnr_adjusted >= 8:
                    return 50 + (hnr_adjusted - 8) * 4.17
                else:
                    return max(5, hnr_adjusted / 8 * 50)

    def _calculate_cpp_score(self, cpp: float, technique_score: float) -> float:
        """
        计算 CPP 分数 v5.19 — 提高满分天花板

        CPP反映声带闭合质量，但流行唱法（尤其是轻柔唱法）CPP天然较低
        参考：
        - 美声: CPP > 3.0 为优秀 (v5.19: 2.0→3.0)
        - 流行实声: CPP > 2.5 为优秀 (v5.19: 1.0→2.5)
        - 流行轻柔/气声: CPP > 0.5 为正常
        """
        if self.singing_style == 'classical':
            # v5.19: 提升 CPP 天花板
            if cpp >= 3.0:
                return 100
            elif cpp >= 2.0:
                return 80 + (cpp - 2.0) * 20
            elif cpp >= 1.0:
                return 60 + (cpp - 1.0) * 20
            else:
                return max(30, cpp / 1.0 * 60)
        else:
            # 流行/民族：如果技巧分高，CPP低可能是艺术选择
            if technique_score >= 35:  # v6.1: 阈值 70→35 (technique_score 现在是 0-85)
                if cpp >= 2.0:      # v5.19: 0.5→2.0
                    return 90
                elif cpp >= 1.0:    # v5.19: 0.2→1.0
                    return 70 + (cpp - 1.0) * 20
                elif cpp >= 0.3:
                    return 50 + (cpp - 0.3) * 28.6
                else:
                    return max(15, 30 + cpp * 66.7)
            else:
                if cpp >= 2.5:      # v5.19: 1.0→2.5
                    return 100
                elif cpp >= 1.5:    # v5.19: 0.5→1.5
                    return 75 + (cpp - 1.5) * 25
                elif cpp >= 0.5:
                    return 50 + (cpp - 0.5) * 25
                else:
                    return max(5, cpp / 0.5 * 50)  # v5.19: */70→*50

    def _generate_diagnosis(
        self,
        diagnosis: TechniqueDiagnosis,
        hnr: float,
        technique: VocalTechniqueResult,
        is_mixed_audio: bool = False
    ) -> None:
        """生成诊断信息"""
        # 混合音频提示
        if is_mixed_audio:
            diagnosis.issues.append("检测到混合音频（带伴奏），HNR评估已调整")

        if hnr < 5:
            diagnosis.issues.append("HNR过低，声带闭合不足")
            diagnosis.suggestions.append("建议进行声带闭合训练，减少漏气")
        elif hnr > 25 and self.singing_style == 'pop':
            diagnosis.issues.append("HNR过高，声音可能过于'实'")
            diagnosis.suggestions.append("可适当增加气声，丰富音色质感")

        if technique.vibrato_count > 0:
            if technique.vibrato_quality >= 70:
                diagnosis.issues.append(f"颤音技巧良好({technique.vibrato_count}次)")
            else:
                diagnosis.issues.append("颤音规范性有待提高")
