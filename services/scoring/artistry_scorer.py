"""
艺术表现评分器 v5.14

v5.14: 认识到艺术表现力是高阶感知维度，无法用简单声学统计量独立评估。
改为: 从已有的四个可靠维度加权合成，加上声学表现力调制。

原理: 专业评委的艺术评分本质上是对音准/节奏/气息/技巧的综合印象，
      加上对动态对比和音高变化的额外关注。
"""
from typing import Tuple, Dict, Optional
import numpy as np
import logging

from services.audio_features_service import VocalTechniqueResult, BreathStabilityResult
from services.scoring.types import ArtistryDiagnosis

logger = logging.getLogger(__name__)


class ArtistryScorer:
    """艺术表现评分器 v5.14 — 从可靠维度合成 + 声学调制"""

    def calculate(
        self,
        technique: VocalTechniqueResult,
        breath: BreathStabilityResult = None,
        emotion_confidence: float = 0.5,
        emotions: Dict[str, float] = None,
        audio_data: Optional[np.ndarray] = None,
        f0: Optional[np.ndarray] = None,
        sr: int = 22050,
        # v5.14: 其他维度分数 (用于加权合成)
        pitch_score: float = 50.0,
        rhythm_score: float = 50.0,
        breath_score: float = 50.0,
        technique_score: float = 50.0,
    ) -> Tuple[float, ArtistryDiagnosis]:
        """
        v5.14: 从四个可靠维度加权合成艺术表现力评分.

        原理: 音准+节奏+气息+技巧的综合表现就是艺术表现力的基础。
              再通过声学特征 (动态对比, 音高变化) 进行上下调制 (±10分).
        """
        diagnosis = ArtistryDiagnosis()

        # 1. 基础: 四个维度加权 (80% of artistry)
        base = (pitch_score * 0.20 + rhythm_score * 0.25 +
                breath_score * 0.20 + technique_score * 0.35)

        # 2. 声学调制 (±10分) — 基于可靠的一次声学特征
        modulation = 0.0

        if audio_data is not None and len(audio_data) > 0:
            try:
                import librosa
                # 动态对比调制
                rms = librosa.feature.rms(y=audio_data, frame_length=2048, hop_length=512)[0]
                rms_pos = rms[rms > 1e-8]
                if len(rms_pos) > 10:
                    p95, p5 = np.percentile(rms_pos, [95, 5])
                    dynamic_ratio = p95 / (p5 + 1e-10)
                    if dynamic_ratio > 15:   modulation += 6
                    elif dynamic_ratio > 8:  modulation += 3
                    elif dynamic_ratio > 3:  modulation += 0
                    else:                    modulation -= 3

                # 音高变化调制
                if f0 is not None:
                    valid_f0 = f0[(~np.isnan(f0)) & (f0 > 65) & (f0 < 1047)]
                    if len(valid_f0) > 20:
                        pitch_cv = np.std(valid_f0) / (np.mean(valid_f0) + 1e-10)
                        if pitch_cv > 0.15:   modulation += 4
                        elif pitch_cv > 0.05: modulation += 1
                        else:                 modulation -= 2
            except Exception:
                pass

        score = max(0, min(100, base + modulation))

        diagnosis.score = score

        if score >= 80:
            diagnosis.level = "专业级"
        elif score >= 65:
            diagnosis.level = "良好"
        elif score >= 50:
            diagnosis.level = "合格"
        else:
            diagnosis.level = "待改进"

        if score < 50:
            diagnosis.suggestions.append("建议加强综合声乐技巧练习，提升整体表现力")
        if modulation > 5:
            diagnosis.issues.append("动态对比和音高变化丰富，艺术表现力强")

        return score, diagnosis
