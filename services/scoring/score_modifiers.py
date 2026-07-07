"""
跨维度评修正模块 v6.2

基于声学特征之间的物理因果关系，在评分流程中施加跨维度修正。
所有修正均有文献支撑，修正幅度有上限以保持稳健性。

文献依据:
- de Krom (1993): HNR 多频带 CV → 声带闭合不一致性 → 气息不稳
- Baken & Orlikoff (2000): Jitter/shimmer 是声带健康的敏感指标
- Sundberg (1987): 频谱倾斜 → 气声 vs 漏气的声学区分
- Titze (1994): 气息支撑不足 → 音高波动增大
"""
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class CrossDimensionModifiers:
    """
    跨维度评分修正器 v6.2

    设计原则:
    1. 仅施加有物理因果关系的修正 (非统计相关)
    2. 单项修正幅度 ≤ 15%, 总修正 ≤ 25%
    3. 所有修正有文献依据
    4. 诊断信息透明 — 每个修正都记录到 diagnosis
    """

    # 修正上限 (总修正不超过原始分数的 ±25%)
    MAX_TOTAL_MODIFIER = 0.25
    # 单项修正上限
    MAX_SINGLE_MODIFIER = 0.15

    def apply_hnr_stability_to_breath(
        self,
        breath_score: float,
        hnr_stability: Optional[float],
    ) -> Tuple[float, Optional[str]]:
        """
        HNR 多频带稳定性 → 气息评分修正

        物理因果: 声带闭合的一致性是良好气息支撑的直接结果。
        当 HNR 在不同频带间波动大 (高 CV), 说明声带闭合时好时坏,
        这是气息支撑不足的声学表现。

        文献: de Krom (1993). "A cepstrum-based technique for HNR."
              — 多频带 HNR 的 CV 反映声门周期的不一致性

        Args:
            breath_score: 当前气息评分 (0-100)
            hnr_stability: 多频带 HNR 的变异系数 (0-1, None 表示未计算)

        Returns:
            (修正后气息评分, 诊断信息)
        """
        if hnr_stability is None:
            return breath_score, None

        # hnr_stability 是 CV 值: < 0.15 为稳定, 0.15-0.30 中等, > 0.30 不稳定
        # de Krom (1993) 指出 CV > 0.2 即可检测到声门周期不一致
        if hnr_stability <= 0.15:
            return breath_score, None

        # 线性惩罚: CV 0.15→0 惩罚, 0.40→15% 惩罚
        penalty_ratio = min(
            self.MAX_SINGLE_MODIFIER,
            (hnr_stability - 0.15) / 0.25 * self.MAX_SINGLE_MODIFIER
        )
        penalty = breath_score * penalty_ratio
        new_score = max(0, breath_score - penalty)

        diagnosis = (
            f"HNR频带稳定性低(CV={hnr_stability:.2f}), "
            f"声带闭合不一致 → 气息扣{penalty:.0f}分"
        )

        logger.debug(
            f"HNR→Breath modifier: {breath_score:.0f} → {new_score:.0f} "
            f"(CV={hnr_stability:.2f}, penalty={penalty:.0f})"
        )
        return new_score, diagnosis

    def apply_voicing_to_pitch_weight(
        self,
        pitch_score: float,
        detection_confidence: Optional[float],
        detection_rate: float,
    ) -> Tuple[float, Optional[str]]:
        """
        Voicing 检测置信度 → 音准可信度标记

        物理因果: 当 PYIN 对 voiced/unvoiced 判断不可靠时 (低自一致性),
        f0 序列的可靠性下降, 音准评分可信度降低。
        不直接修改分数, 而是降低音准维度在总分中的权重。

        文献: de Cheveigne & Kawahara (2002). "YIN, a fundamental frequency
              estimator." — voicing decision errors propagate to pitch metrics

        Args:
            pitch_score: 当前音准评分
            detection_confidence: voicing 检测置信度 (0-1, None 表示未计算)
            detection_rate: f0 检测率 (0-1)

        Returns:
            (修正后音准评分, 诊断信息)
        """
        if detection_confidence is None:
            return pitch_score, None

        # 低置信度标记 (不改分数, 在 ScoreService 层面降低权重)
        if detection_confidence < 0.6:
            diagnosis = (
                f"音准检测置信度低(voicing_confidence={detection_confidence:.0%}), "
                f"音准评分仅供参考"
            )
            return pitch_score, diagnosis

        return pitch_score, None

    def apply_spectral_tilt_to_breath(
        self,
        breath_technique_score: float,
        spectral_tilt: Optional[float],
        hnr: float,
    ) -> Tuple[float, Optional[str]]:
        """
        频谱倾斜 → 气声技巧评分修正

        物理因果: 频谱倾斜 (H1-H2 差异) 是区分「可控气声」和「无效漏气」的关键指标。
        - HNR 低 + 频谱倾斜平坦 (> -8 dB/octave): 气声是艺术选择 (不扣分)
        - HNR 低 + 频谱倾斜陡峭 (< -12 dB/octave): 可能是漏气 (适当扣分)
        - HNR 高 + 任何倾斜: 正常闭合 (不扣分)

        文献: Sundberg (1987). "The Science of the Singing Voice." Ch.2
              — 频谱倾斜是声门闭合程度的直接声学表现

        Args:
            breath_technique_score: 气声技巧子分 (0-100)
            spectral_tilt: 频谱倾斜 dB/octave (None 表示未计算)
            hnr: 谐波噪声比 (dB)

        Returns:
            (修正后气声技巧分, 诊断信息)
        """
        if spectral_tilt is None:
            return breath_technique_score, None

        # HNR 高 → 声带闭合良好, 不施加修正
        if hnr > 18:
            return breath_technique_score, None

        # HNR 低 + 频谱倾斜平坦: 艺术化气声
        if spectral_tilt > -10:
            return breath_technique_score, (
                f"低HNR({hnr:.0f}dB)伴频谱平坦(>{-10}dB/oct), "
                f"判定为艺术化气声而非漏气"
            )

        # HNR 低 + 频谱倾斜陡峭: 可能是无效漏气
        if spectral_tilt < -14:
            penalty_ratio = min(
                self.MAX_SINGLE_MODIFIER,
                abs(spectral_tilt + 14) / 10 * self.MAX_SINGLE_MODIFIER
            )
            penalty = breath_technique_score * penalty_ratio
            new_score = max(0, breath_technique_score - penalty)
            diagnosis = (
                f"低HNR({hnr:.0f}dB)伴陡峭频谱倾斜({spectral_tilt:.0f}dB/oct), "
                f"疑似无效漏气 → 气声技巧扣{penalty:.0f}分"
            )
            return new_score, diagnosis

        return breath_technique_score, None

    def apply_breath_pitch_coupling(
        self,
        pitch_wobble: float,
        hnr_stability: Optional[float],
    ) -> Tuple[float, Optional[str]]:
        """
        气息-音准耦合惩罚

        物理因果: 当气息支撑不足时, 音高会出现不稳定的波动 (pitch wobble)。
        如果同时满足 HNR 不稳定 (声带闭合问题) + 音高波动大 (pitch wobble),
        则非常可能是气息控制不足导致的综合问题。

        文献: Titze (1994). "Principles of Voice Production."
              — 气息压力与声带张力的耦合

        Args:
            pitch_wobble: 长音波动 (cents)
            hnr_stability: HNR 多频带 CV

        Returns:
            (耦合惩罚分 0-15, 诊断信息)
        """
        if hnr_stability is None:
            return 0, None

        # 两个条件同时满足才施加惩罚
        wobble_high = pitch_wobble > 40  # 音分
        hnr_unstable = hnr_stability > 0.20

        if not (wobble_high and hnr_unstable):
            return 0, None

        # 惩罚强度: 最大 15 分
        wobble_factor = min(1.0, (pitch_wobble - 40) / 60)  # 0-1
        hnr_factor = min(1.0, (hnr_stability - 0.20) / 0.30)  # 0-1
        penalty = min(15, 15 * wobble_factor * hnr_factor)

        diagnosis = (
            f"气息-音准耦合问题: 长音波动({pitch_wobble:.0f}音分) + "
            f"HNR不稳定(CV={hnr_stability:.2f}), "
            f"提示气息控制不足 → 总分扣{penalty:.0f}分"
        )

        return penalty, diagnosis

    def apply_jitter_shimmer_to_technique(
        self,
        technique_score: float,
        jitter_local: Optional[float] = None,
        shimmer_local: Optional[float] = None,
    ) -> Tuple[float, Optional[str]]:
        """
        Jitter/Shimmer → 发声技术评分修正 v6.2

        物理因果: Jitter 和 shimmer 是声带振动的微观不稳定性指标,
        直接反映发声技术的精细控制能力。
        - Jitter > 1.04%: 声带振动不规律 [Baken & Orlikoff 2000]
        - Shimmer > 3.81%: 声带闭合不完全 [Baken & Orlikoff 2000]
        - 用于区分"技术性气声"(可控)和"病理性漏气"(不可控)

        修正幅度: 最多 ±8% (conservative, 因为 Praat 对歌唱声的 jitter/shimmer
        可能有边界效应, 不像语音那样标准化)

        Args:
            technique_score: 当前技术评分 (0-100)
            jitter_local: Praat jitter local (%)
            shimmer_local: Praat shimmer local (%)

        Returns:
            (修正后技术评分, 诊断信息)
        """
        if jitter_local is None and shimmer_local is None:
            return technique_score, None

        total_penalty = 0.0
        diagnoses = []

        # Jitter 惩罚: > 1.04% 开始扣分 [Baken & Orlikoff 2000, Table 6-5]
        if jitter_local is not None and jitter_local > 0:
            if jitter_local > 2.0:
                # 严重不规则 — 2% 以上非常罕见
                penalty = min(8, (jitter_local - 1.04) * 4)
                total_penalty += penalty
                diagnoses.append(f"jitter偏高({jitter_local:.2f}%)")
            elif jitter_local > 1.04:
                # 超出正常范围
                penalty = min(5, (jitter_local - 1.04) * 3)
                total_penalty += penalty
                diagnoses.append(f"jitter略高({jitter_local:.2f}%)")

        # Shimmer 惩罚: > 3.81% 开始扣分 [Baken & Orlikoff 2000, Table 7-3]
        if shimmer_local is not None and shimmer_local > 0:
            if shimmer_local > 8.0:
                penalty = min(8, (shimmer_local - 3.81) * 1.0)
                total_penalty += penalty
                diagnoses.append(f"shimmer偏高({shimmer_local:.2f}%)")
            elif shimmer_local > 3.81:
                penalty = min(5, (shimmer_local - 3.81) * 0.8)
                total_penalty += penalty
                diagnoses.append(f"shimmer略高({shimmer_local:.2f}%)")

        if total_penalty > 0:
            new_score = max(0, technique_score - total_penalty)
            diagnosis = (
                f"声带振动稳定性不足: {', '.join(diagnoses)} "
                f"→ 技术扣{total_penalty:.0f}分"
            )
            return new_score, diagnosis

        return technique_score, None
