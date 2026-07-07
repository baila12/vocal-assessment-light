"""
音准评分器 v6.2

负责音准维度的评分计算和诊断生成。

v6.2 改进 (文献驱动):
- 多指标体系: MAE + RPA + RCA + gross_error + smoothness + octave_error
  替代 v5.14-v6.1 的单一 MAE 线性映射
- 指数衰减曲线: 替代线性分段映射, 更符合听觉感知 (Weber-Fechner 定律)
- 文献依据:
  - Wager et al. (2022). Modern singing quality assessment — 多指标融合
  - Cao et al. (2008). Automatic singing evaluation — RPA/RCA/gross_error
  - Tonality-based evaluation (Interspeech 2025) — 参考独立评分, r=0.611
"""
from typing import Tuple
import numpy as np
import logging

from services.audio_features_service import PitchDeviationResult
from services.scoring_config import PitchThresholds, EmpiricalThresholds
from services.scoring.types import PitchDiagnosis

logger = logging.getLogger(__name__)

# v6.2: 指数衰减 tau 参数 — MAE 敏感度
# tau=40: MAE 8→81.9, MAE 20→60.7, MAE 45→32.5, MAE 65→19.7, MAE 100→8.2
# 相较于线性分段 (MAE 8→100, 45→70, 65→45), 指数衰减更能拉开高低分差距
_MAE_TAU = 40.0


class PitchScorer:
    """音准评分器 v6.2 — 多指标体系 + 指数衰减"""

    def __init__(self, thresholds: PitchThresholds, empirical: EmpiricalThresholds = None):
        self.thresholds = thresholds
        self.empirical = empirical or EmpiricalThresholds()

    def calculate(
        self,
        pitch_deviation: PitchDeviationResult
    ) -> Tuple[float, PitchDiagnosis]:
        """
        计算音准评分 v6.2

        多指标融合权重 v6.2:
          - MAE 指数衰减: 40% (曾 35%) — 最鲁棒的聚合指标
          - RPA (Raw Pitch Accuracy): 25%
          - RCA (Raw Chroma Accuracy): 10%
          - Gross error 惩罚: 15%
          - Smoothness: 5% (曾 10%) — YIN f0 帧间噪声大, 降低权重
          - Octave error 惩罚: 5%

        v6.2 权重校准依据:
          PYIN 对比测试显示 YIN 在 16kHz 下产生 3.5x 虚假帧间跳变
          (YIN 785 breaks vs PYIN 226). 帧间指标 (smoothness, breaks)
          受 f0 伪影污染, 降低权重; 聚合指标 (MAE, RPA) 鲁棒.
          文献: de Cheveigne & Kawahara (2002) — YIN 在低 SNR 下误差率升高

        各指标文献依据:
          - MAE: 最广泛使用的音准指标 (Wager 2022)
          - RPA/RCA: Cao et al. (2008) 多指标体系
          - Gross error: 严重跑调独立惩罚 (Sundberg 1987)
          - Smoothness: 音高一致性 (Canazza et al. 2014)
          - Octave error: 八度错误检测 (pitch-benchmark 评估)
        """
        diagnosis = PitchDiagnosis()
        mae = pitch_deviation.mae_cents

        # ── 1. MAE 指数衰减分 (40%) ──
        # 指数衰减: 低误差区缓慢衰减, 中高误差区加速衰减
        # 符合 Weber-Fechner 听觉感知定律
        mae_score = 100.0 * np.exp(-mae / _MAE_TAU)

        # ── 2. RPA — 原始音高准确率 (25%) ──
        # 帧内 |cents| < 50 半音的比例, 0-1 → 0-100
        # 文献: Cao et al. (2008)
        rpa = pitch_deviation.rpa if pitch_deviation.rpa > 0 else 0.0
        rpa_score = rpa * 100.0

        # ── 3. RCA — 原始半音准确率 (10%) ──
        # 八度折叠后的音高准确率, 忽略八度错误
        rca = pitch_deviation.rca if pitch_deviation.rca > 0 else 0.0
        rca_score = rca * 100.0

        # ── 4. Gross error 惩罚 (15%) ──
        # 严重跑调 (>200 音分) 的比例, 独立于 MAE 的惩罚维度
        # 文献: Sundberg (1987), gross error > 5% 即需关注
        gross_error_rate = pitch_deviation.gross_error_rate
        if gross_error_rate > 0.05:
            # 超过 5% 阈值: 线性惩罚
            gross_penalty = min(100, (gross_error_rate - 0.05) * 200)
            gross_score = 100.0 - gross_penalty
        else:
            gross_score = 100.0

        # ── 5. Smoothness — 音高一致性 (5% v6.2: YIN f0 帧间噪声大) ──
        # relative_smoothness = CV(adjacent f0 diffs), 1.0 为基线
        # 文献: Canazza et al. (2014), pitch smoothness → expressiveness
        smoothness = pitch_deviation.relative_smoothness
        if smoothness > 0:
            smoothness_score = max(0, 100.0 - (smoothness - 1.0) * 50.0)
        else:
            smoothness_score = 50.0  # 无数据时中性分

        # ── 6. Octave error 惩罚 (5%) ──
        octave_error_rate = pitch_deviation.octave_error_rate
        octave_score = max(0, 100.0 - octave_error_rate * 200.0)

        # ── 加权合成 v6.2 ──
        score = (
            mae_score * 0.40 +
            rpa_score * 0.25 +
            rca_score * 0.10 +
            gross_score * 0.15 +
            smoothness_score * 0.05 +
            octave_score * 0.05
        )

        # ── 检测率惩罚 (继承 v5.14-v6.1) ──
        if pitch_deviation.detection_rate < 0.5:
            penalty = (0.5 - pitch_deviation.detection_rate) * 30
            score -= penalty
            diagnosis.issues.append(
                f"音高检测率低({pitch_deviation.detection_rate*100:.0f}%)"
            )

        # ── 音高断层惩罚 v6.2: PYIN 校准 ──
        # YIN f0 噪声产生 3.5x 虚假断层 (785 YIN vs 226 PYIN, 同一音频)
        # 校准: YIN break_rate ÷ 3.5 ≈ 真实断层率
        # 文献: de Cheveigne & Kawahara (2002) — YIN 在低 SNR 下误差率升高
        _YIN_INFLATION = 3.5  # PYIN 校准因子
        if pitch_deviation.valid_frame_count > 0 and pitch_deviation.pitch_breaks > 0:
            est_pairs = pitch_deviation.valid_frame_count * max(pitch_deviation.detection_rate, 0.5)
            break_rate = pitch_deviation.pitch_breaks / max(est_pairs, 1)
            corrected_rate = break_rate / _YIN_INFLATION
            if corrected_rate > 0.05:  # >5% 真实断层率 → 惩罚
                penalty = min(15, (corrected_rate - 0.05) * 200)
                score -= penalty
                diagnosis.issues.append(
                    f"换声区存在{pitch_deviation.pitch_breaks}处音高断层"
                )

        # ── 长音波动惩罚 (继承) ──
        wobble_threshold = self.empirical.pitch_wobble_threshold
        if pitch_deviation.pitch_wobble > wobble_threshold:
            penalty = min(10, (pitch_deviation.pitch_wobble - wobble_threshold) * 0.3)
            score -= penalty
            diagnosis.issues.append(
                f"长音波动较大({pitch_deviation.pitch_wobble:.0f}音分)"
            )

        score = max(0, min(100, score))

        # ── 等级判定 ──
        if score >= 85:
            diagnosis.level = "专业级"
        elif score >= 70:
            diagnosis.level = "良好"
        elif score >= 50:
            diagnosis.level = "合格"
        else:
            diagnosis.level = "待改进"

        diagnosis.score = score
        diagnosis.mae_cents = mae

        # ── 多指标诊断信息 ──
        if gross_error_rate > 0.05:
            diagnosis.issues.append(
                f"严重跑调比例({gross_error_rate*100:.0f}%)偏高"
            )
        if pitch_deviation.octave_error_rate > 0.03:
            diagnosis.issues.append("存在八度错误")
        if smoothness > 2.5:
            diagnosis.issues.append(
                f"音高一致性偏低(smoothness={smoothness:.1f})"
            )
        if rpa < 0.7:
            diagnosis.issues.append(f"音高准确率偏低(RPA={rpa*100:.0f}%)")

        # ── 建议 ──
        if score < 60:
            diagnosis.suggestions.append("建议加强音准训练，注意听标准音高")
        if pitch_deviation.pitch_breaks > 0:
            diagnosis.suggestions.append("换声区过渡需要更平滑，可练习音阶过渡")
        if gross_error_rate > 0.10:
            diagnosis.suggestions.append("严重跑调比例高，建议放慢速度逐句练习")
        if smoothness > 3.0:
            diagnosis.suggestions.append("音高波动大，建议进行长音稳定性训练")

        return score, diagnosis
