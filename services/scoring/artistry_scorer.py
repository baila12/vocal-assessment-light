"""
艺术表现评分器

负责艺术表现维度的评分计算和诊断生成
"""
from typing import Tuple, Dict
import numpy as np
import logging

from services.audio_features_service import VocalTechniqueResult
from services.scoring import ArtistryDiagnosis

logger = logging.getLogger(__name__)


class ArtistryScorer:
    """
    艺术表现评分器

    组成部分：
    - 情感饱满度: 60%
    - 技巧运用: 40%

    注意：emotion_confidence 是模型返回的最大情感概率（通常0.2-0.5），
    不能直接作为情感得分。需要结合情感多样性和技巧运用综合评估。
    """

    def calculate(
        self,
        emotion_confidence: float,
        emotions: Dict[str, float],
        technique: VocalTechniqueResult
    ) -> Tuple[float, ArtistryDiagnosis]:
        """
        计算艺术表现评分

        Args:
            emotion_confidence: 情感识别置信度
            emotions: 情感分布字典
            technique: 发声技巧分析结果

        Returns:
            (分数, 诊断信息)
        """
        diagnosis = ArtistryDiagnosis()

        # 情感评分 - 基于情感多样性和强度
        emotion_score = self._calculate_emotion_score(emotions, diagnosis)

        # 技巧运用评分
        dynamics_score = self._calculate_dynamics_score(technique)

        # 加权平均
        score = emotion_score * 0.6 + dynamics_score * 0.4

        diagnosis.score = score
        diagnosis.emotion_score = emotion_score
        diagnosis.dynamics_score = dynamics_score

        if score >= 80:
            diagnosis.level = "专业级"
        elif score >= 70:
            diagnosis.level = "良好"
        elif score >= 60:
            diagnosis.level = "合格"
        else:
            diagnosis.level = "待改进"

        if score < 60:
            diagnosis.suggestions.append("建议加强情感投入，增强演唱感染力")

        return score, diagnosis

    def _calculate_emotion_score(
        self,
        emotions: Dict[str, float],
        diagnosis: ArtistryDiagnosis
    ) -> float:
        """
        计算情感得分

        Args:
            emotions: 情感分布字典
            diagnosis: 诊断对象（用于添加诊断信息）

        Returns:
            情感得分
        """
        emotion_score = 60  # 基础分

        if emotions:
            probs = [max(0.001, s) for s in emotions.values()]
            total_prob = sum(probs)
            if total_prob > 0:
                probs = [p / total_prob for p in probs]

                # 情感强度：最大概率越高，情感越明确
                max_prob = max(probs)
                emotion_score += max_prob * 20  # 最高+20

                # 情感多样性（熵）
                entropy = -sum(p * np.log(p) for p in probs if p > 0)

                # 熵值适中为好（有一定变化但不过于分散）
                if 0.8 <= entropy <= 1.5:
                    emotion_score += 15  # 情感丰富
                    diagnosis.issues.append("情感表达丰富多样")
                elif entropy < 0.5:
                    emotion_score -= 5  # 略单调
                    diagnosis.issues.append("情感表达较为单调")
                else:
                    emotion_score += 5  # 正常

        return max(0, min(100, emotion_score))

    def _calculate_dynamics_score(self, technique: VocalTechniqueResult) -> float:
        """
        计算技巧运用得分

        Args:
            technique: 发声技巧分析结果

        Returns:
            技巧运用得分
        """
        dynamics_score = 50

        if technique.vibrato_count > 0:
            dynamics_score += min(20, technique.vibrato_count * 2)
        if technique.slide_count > 0:
            dynamics_score += min(15, technique.slide_count * 3)
        if technique.falsetto_segments > 0:
            dynamics_score += min(15, technique.falsetto_segments * 3)

        return max(0, min(100, dynamics_score))