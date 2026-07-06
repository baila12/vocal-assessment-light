"""
艺术表现评分器 v6.1

v6.1 重构: 基于真实声学特征独立评估艺术表现力，替代旧版合成公式。
旧版 (v5.14): artistry = pitch*0.20 + rhythm*0.25 + breath*0.20 + technique*0.35 + modulation(±10)
新版 (v6.1): 直接使用已计算的声学特征:
  - 颤音品质 (vibrato_quality) — 演唱技巧的运用程度
  - 动态对比 (dynamic_range, crescendo_quality) — 情感的起伏表现
  - 艺术化气息处理 (is_artistic_fluctuation, phrase_coherence) — 乐句塑造
  - 音高变化 (pitch_variation) — 旋律处理的丰富度

文献依据:
  - Sundberg (1987). "The Science of the Singing Voice." — 颤音与表现力关系
  - Canazza et al. (2014). "Expressiveness in Music Performance." — 动态与音高变化
  - 声乐表演评估的通用框架: 技巧运用、动态控制、乐句处理、音色变化
"""
from typing import Tuple, Dict, Optional
import numpy as np
import logging

from services.audio_features_service import VocalTechniqueResult, BreathStabilityResult
from services.scoring.types import ArtistryDiagnosis

logger = logging.getLogger(__name__)


class ArtistryScorer:
    """艺术表现评分器 v6.1 — 基于真实声学特征的独立评分"""

    def calculate(
        self,
        technique: VocalTechniqueResult,
        breath: BreathStabilityResult = None,
        emotion_confidence: float = 0.5,
        emotions: Dict[str, float] = None,
        audio_data: Optional[np.ndarray] = None,
        f0: Optional[np.ndarray] = None,
        sr: int = 22050,
        # v5.14 legacy: retained for backward compatibility (未使用的旧接口参数)
        pitch_score: float = 50.0,
        rhythm_score: float = 50.0,
        breath_score: float = 50.0,
        technique_score: float = 50.0,
    ) -> Tuple[float, ArtistryDiagnosis]:
        """
        v6.1: 基于真实声学特征独立评估艺术表现力。

        四个子维度权重:
          - 技巧运用 (vibrato_quality): 30%
          - 动态控制 (dynamic/crescendo): 30%
          - 乐句处理 (phrase/artistic_fluctuation): 25%
          - 音高变化 (pitch_variation): 15%

        不再依赖其他维度分数。每个子维度基于可测量的声学特征。
        """
        diagnosis = ArtistryDiagnosis()

        # ── 1. 技巧运用 (30%) — vibrato_quality 直接映射 ──
        vibrato_sub = self._calc_vibrato_expressiveness(technique)

        # ── 2. 动态控制 (30%) — dynamic_range + crescendo_quality ──
        dynamic_sub = self._calc_dynamic_expressiveness(breath, audio_data, sr)

        # ── 3. 乐句处理 (25%) — phrase_coherence + artistic_fluctuation ──
        phrase_sub = self._calc_phrase_expressiveness(breath)

        # ── 4. 音高变化 (15%) — pitch variation from f0 ──
        pitch_var_sub = self._calc_pitch_variation_expressiveness(f0)

        # 加权合成
        score = (
            vibrato_sub * 0.30 +
            dynamic_sub * 0.30 +
            phrase_sub * 0.25 +
            pitch_var_sub * 0.15
        )

        score = max(0, min(100, score))
        diagnosis.score = score

        # 等级划分 v6.1 (新基线 0, 调整阈值)
        if score >= 75:
            diagnosis.level = "专业级"
        elif score >= 55:
            diagnosis.level = "良好"
        elif score >= 35:
            diagnosis.level = "合格"
        else:
            diagnosis.level = "待改进"

        # 诊断信息
        if vibrato_sub > 70:
            diagnosis.positives.append("颤音技巧运用出色")
        if dynamic_sub > 70:
            diagnosis.positives.append("动态对比丰富，情感表现力强")
        if phrase_sub > 70:
            diagnosis.positives.append("乐句处理细腻，气息分配合理")
        if pitch_var_sub > 60:
            diagnosis.positives.append("音高变化丰富，旋律处理有表现力")

        if score < 35:
            diagnosis.suggestions.append("建议加强演唱技巧和情感表达训练")
        if vibrato_sub < 20 and dynamic_sub < 20:
            diagnosis.suggestions.append("演唱较为平淡，可增加动态对比和技巧运用")

        return score, diagnosis

    def _calc_vibrato_expressiveness(self, technique: VocalTechniqueResult) -> float:
        """
        技巧运用子分 — 基于颤音品质和数量

        vibrato_quality (0-100) 直接映射，加上数量奖励。
        无颤音时得 0 分 (演唱可能平直但其他维度可弥补)。
        """
        if technique.vibrato_count == 0:
            return 0.0

        # vibrato_quality 连续映射: 0→0, 100→80
        quality_score = technique.vibrato_quality * 0.80

        # 数量奖励: 每个颤音 +2, 上限 20
        count_bonus = min(20, technique.vibrato_count * 2)

        return min(100, quality_score + count_bonus)

    def _calc_dynamic_expressiveness(
        self,
        breath: BreathStabilityResult,
        audio_data: Optional[np.ndarray],
        sr: int
    ) -> float:
        """
        动态控制子分 — 基于 dynamic_range 和 crescendo_quality

        dynamic_range (dB): 0→0, 30→60 (流行唱法典型 10-25dB)
        crescendo_quality (0-100): 0→0, 100→40
        """
        score = 0.0

        # 从 breath 结果获取
        if breath is not None:
            if breath.dynamic_range > 0:
                # 连续映射: 0dB→0, 30dB→60
                score += min(60, breath.dynamic_range * 2.0)
            if breath.crescendo_quality > 0:
                # 连续映射: 0→0, 100→40
                score += breath.crescendo_quality * 0.40
            return min(100, score)

        # 回退: 从 raw audio 计算 dynamic range
        if audio_data is not None and len(audio_data) > 0:
            try:
                import librosa
                rms = librosa.feature.rms(y=audio_data, frame_length=2048, hop_length=512)[0]
                rms_pos = rms[rms > 1e-8]
                if len(rms_pos) > 10:
                    p95, p5 = np.percentile(rms_pos, [95, 5])
                    dynamic_ratio = p95 / (p5 + 1e-10)
                    dynamic_db = 20 * np.log10(dynamic_ratio)
                    # 连续映射: 0dB→0, 30dB→70
                    score += min(70, dynamic_db * 2.33)
            except Exception:
                pass

        return min(100, score)

    def _calc_phrase_expressiveness(self, breath: BreathStabilityResult) -> float:
        """
        乐句处理子分 — 基于 phrase_coherence 和 artistic_fluctuation

        phrase_coherence (0-100): 连续映射, 0→0, 100→70
        artistic_fluctuation: true → +30, 有规律的起伏是艺术处理的标志
        """
        if breath is None:
            return 0.0

        score = 0.0

        if breath.phrase_coherence > 0:
            score += breath.phrase_coherence * 0.70  # 0→0, 100→70

        if breath.is_artistic_fluctuation:
            score += 30  # 艺术化起伏奖励

        # 长音数量反映乐句结构
        if breath.long_note_count > 0:
            score += min(10, breath.long_note_count * 2)

        return min(100, score)

    def _calc_pitch_variation_expressiveness(self, f0: Optional[np.ndarray]) -> float:
        """
        音高变化子分 — 基于 pitch CV

        pitch_cv: 音高变化的变异系数
        - 太低 (<0.03): 过于平直 → 10-20
        - 中等 (0.03-0.10): 自然表达 → 30-60
        - 较高 (0.10-0.20): 丰富变化 → 60-85
        - 太高 (>0.20): 可能失控 → 40-50

        文献: Canazza et al. (2014) — 适度音高变化是表现力的关键标志
        """
        if f0 is None or len(f0) < 20:
            return 0.0

        try:
            valid_f0 = f0[(~np.isnan(f0)) & (f0 > 65) & (f0 < 1047)]
            if len(valid_f0) < 20:
                return 0.0

            pitch_cv = float(np.std(valid_f0) / (np.mean(valid_f0) + 1e-10))

            # 双重折线映射: 低区上升, 中区平台, 高区下降
            if pitch_cv < 0.03:
                score = pitch_cv / 0.03 * 20  # 0→0, 0.03→20
            elif pitch_cv < 0.10:
                score = 20 + (pitch_cv - 0.03) / 0.07 * 50  # 0.03→20, 0.10→70
            elif pitch_cv < 0.20:
                score = 70 + (pitch_cv - 0.10) / 0.10 * 20  # 0.10→70, 0.20→90
            else:
                score = max(30, 90 - (pitch_cv - 0.20) * 80)  # 太高下降

            return min(100, max(0, score))

        except Exception:
            return 0.0
