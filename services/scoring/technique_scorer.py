"""
发声技术评分器

负责发声技术维度的评分计算和诊断生成
"""
from typing import Tuple
import logging

from services.audio_features_service import VocalTechniqueResult
from services.scoring_config import TechniqueThresholds
from services.scoring import TechniqueDiagnosis

logger = logging.getLogger(__name__)


class TechniqueScorer:
    """
    发声技术评分器

    组成部分：
    - HNR (声带闭合): 40%
    - CPP (声带闭合质量): 30%
    - 技巧完成度: 30%
    """

    def __init__(self, thresholds: TechniqueThresholds, singing_style: str = 'pop'):
        """
        初始化发声技术评分器

        Args:
            thresholds: 技术阈值配置
            singing_style: 唱法类型 (pop/classical/folk/rap)
        """
        self.thresholds = thresholds
        self.singing_style = singing_style

    def calculate(
        self,
        hnr: float,
        cpp: float,
        technique: VocalTechniqueResult
    ) -> Tuple[float, TechniqueDiagnosis]:
        """
        计算发声技术评分

        Args:
            hnr: 谐波噪声比
            cpp: 声门闭合周期峰值
            technique: 发声技巧分析结果

        Returns:
            (分数, 诊断信息)
        """
        diagnosis = TechniqueDiagnosis()

        # HNR 评分 - 根据唱法调整标准
        hnr_score = self._calculate_hnr_score(hnr, technique.technique_score)

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
        self._generate_diagnosis(diagnosis, hnr, technique)

        score = max(0, min(100, score))

        diagnosis.score = score
        diagnosis.hnr = hnr
        diagnosis.cpp = cpp
        diagnosis.vibrato_quality = technique.vibrato_quality

        if score >= 80:
            diagnosis.level = "专业级"
        elif score >= 70:
            diagnosis.level = "良好"
        elif score >= 60:
            diagnosis.level = "合格"
        else:
            diagnosis.level = "待改进"

        return score, diagnosis

    def _calculate_hnr_score(self, hnr: float, technique_score: float) -> float:
        """
        计算 HNR 分数

        注意：轻柔唱法/气声唱法的HNR天然较低（6-12dB是正常的）
        参考：
        - 美声: 18-25dB (完全闭合)
        - 流行实声: 12-18dB
        - 流行轻柔/气声: 6-12dB (这是艺术选择，不是技术问题)
        """
        if self.singing_style == 'classical':
            # 美声：HNR > 20dB 满分
            return min(100, hnr / 20 * 100)
        elif self.singing_style == 'folk':
            # 民族：HNR 15-20dB 满分
            if hnr >= 18:
                return 100
            elif hnr >= 12:
                return 70 + (hnr - 12) * 5
            else:
                return max(40, hnr / 12 * 70)
        else:
            # 流行：需要区分唱法类型
            if technique_score >= 70:
                # 高技巧得分，HNR低可能是艺术选择（气声唱法）
                if hnr >= 12:
                    return 100
                elif hnr >= 8:
                    return 75 + (hnr - 8) * 6.25
                elif hnr >= 5:
                    return 60 + (hnr - 5) * 5
                else:
                    return max(40, hnr / 5 * 60)
            else:
                # 低技巧分，可能是真正的技术问题
                if hnr >= 15:
                    return 100
                elif hnr >= 10:
                    return 80 + (hnr - 10) * 4
                else:
                    return max(30, hnr / 10 * 80)

    def _calculate_cpp_score(self, cpp: float, technique_score: float) -> float:
        """
        计算 CPP 分数

        CPP反映声带闭合质量，但流行唱法（尤其是轻柔唱法）CPP天然较低
        参考：
        - 美声: CPP > 2.0 为优秀
        - 流行实声: CPP > 1.0 为优秀
        - 流行轻柔/气声: CPP > 0.3 为正常
        """
        if self.singing_style == 'classical':
            if cpp >= 2.0:
                return 100
            elif cpp >= 1.0:
                return 70 + (cpp - 1.0) * 30
            else:
                return max(40, cpp / 1.0 * 70)
        else:
            # 流行/民族：如果技巧分高，CPP低可能是艺术选择
            if technique_score >= 70:
                if cpp >= 0.5:
                    return 85
                elif cpp >= 0.2:
                    return 70 + (cpp - 0.2) * 50
                else:
                    return max(50, 50 + cpp * 100)
            else:
                if cpp >= 1.0:
                    return 100
                elif cpp >= 0.5:
                    return 70 + (cpp - 0.5) * 60
                else:
                    return max(30, cpp / 0.5 * 70)

    def _generate_diagnosis(
        self,
        diagnosis: TechniqueDiagnosis,
        hnr: float,
        technique: VocalTechniqueResult
    ) -> None:
        """生成诊断信息"""
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
