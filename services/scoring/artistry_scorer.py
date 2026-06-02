"""
艺术表现评分器 v5.10

基于声乐表现力特征的评分，替代原来基于Wav2Vec2情绪模型的评分。
IEMOCAP语音情感模型对唱歌的域不匹配问题已解决。

评分维度：
- 颤音质量 (30%): 颤音的规范性和美感
- 动态范围 (30%): 强弱对比的表现力
- 技巧多样性 (20%): 颤音/滑音/假声的综合运用
- 气息表现力 (20%): 气息支撑的艺术表现
"""
from typing import Tuple, Dict
import numpy as np
import logging

from services.audio_features_service import VocalTechniqueResult, BreathStabilityResult
from services.scoring import ArtistryDiagnosis

logger = logging.getLogger(__name__)


class ArtistryScorer:
    """
    艺术表现评分器 v5.10

    基于声乐特征评估演唱表现力，不再依赖跨域情绪模型。
    """

    def calculate(
        self,
        technique: VocalTechniqueResult,
        breath: BreathStabilityResult = None,
        emotion_confidence: float = 0.5,
        emotions: Dict[str, float] = None
    ) -> Tuple[float, ArtistryDiagnosis]:
        """
        计算艺术表现评分

        Args:
            technique: 发声技巧分析结果
            breath: 气息稳定性分析结果（可选）
            emotion_confidence: 情感识别置信度（仅作小幅加分，已去重）
            emotions: 情感分布字典（已废弃，保留兼容）

        Returns:
            (分数, 诊断信息)
        """
        diagnosis = ArtistryDiagnosis()

        # 1. 颤音质量评分 (30%)
        vibrato_score = self._calculate_vibrato_score(technique, diagnosis)

        # 2. 动态范围评分 (30%)
        dynamic_score = self._calculate_dynamic_score(breath, diagnosis)

        # 3. 技巧多样性评分 (20%)
        diversity_score = self._calculate_diversity_score(technique, diagnosis)

        # 4. 气息表现力评分 (20%)
        breath_express_score = self._calculate_breath_express_score(breath, diagnosis)

        # 加权平均
        score = (
            vibrato_score * 0.30 +
            dynamic_score * 0.30 +
            diversity_score * 0.20 +
            breath_express_score * 0.20
        )

        # 5. 情感模型输出作为小幅加分（已降权至 +5 顶分）
        emotion_bonus = min(5.0, emotion_confidence * 10)
        score += emotion_bonus

        score = max(0, min(100, score))

        diagnosis.score = score
        diagnosis.emotion_score = vibrato_score
        diagnosis.dynamics_score = dynamic_score

        if score >= 80:
            diagnosis.level = "专业级"
        elif score >= 70:
            diagnosis.level = "良好"
        elif score >= 60:
            diagnosis.level = "合格"
        else:
            diagnosis.level = "待改进"

        if score < 60:
            diagnosis.suggestions.append("建议加强声乐技巧练习，提升演唱表现力")

        return score, diagnosis

    def _calculate_vibrato_score(
        self,
        technique: VocalTechniqueResult,
        diagnosis: ArtistryDiagnosis
    ) -> float:
        """基于颤音质量计算表现力得分"""
        vibrato_count = technique.vibrato_count
        vibrato_quality = technique.vibrato_quality

        if vibrato_count == 0:
            return 30.0  # 无颤音 = 基础分

        # 颤音质量 70+ 表示规范性好
        if vibrato_quality >= 80:
            score = 85.0
            diagnosis.issues.append(f"颤音技巧优秀({vibrato_count}次, 质量{vibrato_quality:.0f})")
        elif vibrato_quality >= 60:
            score = 75.0
            diagnosis.issues.append(f"颤音技巧良好({vibrato_count}次)")
        else:
            score = 60.0 + vibrato_quality * 0.15

        # 颤音次数加分
        score += min(15, vibrato_count * 1.5)

        return max(0, min(100, score))

    def _calculate_dynamic_score(
        self,
        breath: BreathStabilityResult,
        diagnosis: ArtistryDiagnosis
    ) -> float:
        """基于动态范围计算表现力得分"""
        if breath is None:
            return 30.0

        dynamic_range = breath.dynamic_range
        crescendo_quality = getattr(breath, 'crescendo_quality', 0)

        # 动态范围 > 20dB 表示优秀的强弱对比
        if dynamic_range > 30:
            score = 85.0
            diagnosis.issues.append(f"动态范围宽广({dynamic_range:.0f}dB)，表现力强")
        elif dynamic_range > 20:
            score = 75.0
        elif dynamic_range > 10:
            score = 65.0
        else:
            score = 25.0
            diagnosis.issues.append("动态范围偏小，建议加强强弱对比")

        # 渐强渐弱质量加分
        if crescendo_quality > 50:
            score += 10

        return max(0, min(100, score))

    def _calculate_diversity_score(
        self,
        technique: VocalTechniqueResult,
        diagnosis: ArtistryDiagnosis
    ) -> float:
        """基于技巧多样性计算表现力得分"""
        technique_count = sum([
            1 if technique.vibrato_count > 0 else 0,
            1 if technique.slide_count > 0 else 0,
            1 if technique.falsetto_segments > 0 else 0
        ])

        score = 25.0  # 基础分

        if technique_count >= 3:
            score = 90.0
            diagnosis.issues.append("演唱技巧丰富（颤音+滑音+假声）")
        elif technique_count == 2:
            score = 75.0
            diagnosis.issues.append("演唱技巧多样")
        elif technique_count == 1:
            score = 65.0
        else:
            diagnosis.issues.append("演唱技巧较为单调单一，建议丰富表现手法")

        # 技巧完成度加分
        if technique.technique_score > 70:
            score += 10

        return max(0, min(100, score))

    def _calculate_breath_express_score(
        self,
        breath: BreathStabilityResult,
        diagnosis: ArtistryDiagnosis
    ) -> float:
        """基于气息表现力计算得分"""
        if breath is None:
            return 30.0

        prof_score = breath.professional_breath_score
        is_artistic = breath.is_artistic_fluctuation
        soft_quality = getattr(breath, 'soft_singing_quality', 0)

        score = 30.0

        # 专业气息得分贡献
        if prof_score > 80:
            score += 20
            if is_artistic:
                diagnosis.issues.append("气息表现力强，具有艺术化起伏")
        elif prof_score > 60:
            score += 10
        elif prof_score > 40:
            score += 5

        # 弱唱控制力
        if soft_quality > 70:
            score += 15
            diagnosis.issues.append("弱唱控制力优秀")
        elif soft_quality > 50:
            score += 8

        return max(0, min(100, score))