"""
评分计算服务 v4.1 - 专业声乐评估体系（气息专项优化版）

核心原则：
1. 专业权重分配：音准30% + 节奏20% + 气息20% + 发声技术25% + 艺术表现15%
   （气息权重从10%提升至20%，解决低估问题）
2. 底线规则：连续跑调、脱离节拍一票否决
3. 精确量化：音分偏差、拍长归一化、专业气息评估、HNR、CPP
4. 唱法适配：流行、美声、民族、说唱
5. 正向加分为主、负向扣分为辅

v4.1 气息专项优化：
- 区分「艺术化起伏」vs「随机抖动」
- 区分「可控气声」vs「无效漏气」
- 评估弱唱气息支撑质量
- 正向加分机制：专业能力体现在分数上
"""
from dataclasses import dataclass, field
from typing import Dict, Optional, List
import numpy as np
import logging

from services.audio_features_service import (
    AudioFeaturesResult,
    PitchDeviationResult,
    RhythmAlignmentResult,
    BreathStabilityResult,
    VocalTechniqueResult
)

logger = logging.getLogger(__name__)


@dataclass
class PitchDiagnosis:
    """音准诊断详情"""
    score: float = 0.0
    mae_cents: float = 0.0
    level: str = ""
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class RhythmDiagnosis:
    """节奏诊断详情"""
    score: float = 0.0
    deviation_ratio: float = 0.0
    level: str = ""
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class BreathDiagnosis:
    """气息诊断详情 - v4.1 专业评估"""
    score: float = 0.0
    fluctuation: float = 0.0
    level: str = ""
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)

    # v4.1 新增：细分维度得分
    long_note_support: float = 0.0      # 长音气息支撑
    dynamic_control: float = 0.0        # 强弱动态控制
    breath_design: float = 0.0          # 气口设计
    breath_technique: float = 0.0       # 气声技巧

    # 专业能力标记
    is_artistic: bool = False           # 是否为艺术化处理
    has_controlled_breathiness: bool = False  # 是否有可控气声
    long_note_bonus: float = 0.0        # 长音加分
    soft_singing_bonus: float = 0.0     # 弱唱加分


@dataclass
class TechniqueDiagnosis:
    """发声技术诊断详情"""
    score: float = 0.0
    hnr: float = 0.0
    cpp: float = 0.0
    vibrato_quality: float = 0.0
    level: str = ""
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class ArtistryDiagnosis:
    """艺术表现诊断详情"""
    score: float = 0.0
    emotion_score: float = 0.0
    dynamics_score: float = 0.0
    level: str = ""
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class ScoreResultV4:
    """评分结果 v4.0"""
    # 五维评分
    pitch_score: float = 0.0
    rhythm_score: float = 0.0
    breath_score: float = 0.0
    technique_score: float = 0.0
    artistry_score: float = 0.0

    # 总分与等级
    total_score: float = 0.0
    level: str = ""
    grade: str = ""
    stars: str = ""
    color: str = ""

    # 详细诊断
    pitch_diagnosis: PitchDiagnosis = field(default_factory=PitchDiagnosis)
    rhythm_diagnosis: RhythmDiagnosis = field(default_factory=RhythmDiagnosis)
    breath_diagnosis: BreathDiagnosis = field(default_factory=BreathDiagnosis)
    technique_diagnosis: TechniqueDiagnosis = field(default_factory=TechniqueDiagnosis)
    artistry_diagnosis: ArtistryDiagnosis = field(default_factory=ArtistryDiagnosis)

    # 底线规则
    critical_issues: List[str] = field(default_factory=list)
    is_disqualified: bool = False

    # 兼容旧接口
    volume: float = 0.0
    pitch: float = 0.0
    rhythm: float = 0.0
    breath: float = 0.0
    emotion: float = 0.0
    total: float = 0.0
    penalties: Dict[str, float] = field(default_factory=dict)


class ScoreServiceV4:
    """
    评分计算服务 v4.1（气息专项优化版）

    采用专业声乐评估体系：
    - 音准 30% + 节奏 20% + 气息 20% + 发声技术 25% + 艺术表现 15%
    - 底线规则：连续跑调、脱离节拍一票否决
    - 气息专项优化：区分艺术化起伏、可控气声，正向加分机制
    """

    # 专业权重分配（v4.1 气息权重提升，总和=100%）
    WEIGHTS = {
        'pitch': 0.30,      # 音准 30%
        'rhythm': 0.20,     # 节奏 20%
        'breath': 0.20,     # 气息 20%
        'technique': 0.20,  # 发声技术 20%
        'artistry': 0.10    # 艺术表现 10%
    }

    # 评分阈值
    PITCH_EXCELLENT = 10    # 满分阈值（音分）
    PITCH_GOOD = 30         # 良好阈值
    PITCH_PASS = 50         # 合格阈值

    RHYTHM_EXCELLENT = 0.1  # 满分阈值（拍长比例）
    RHYTHM_GOOD = 0.2       # 良好阈值
    RHYTHM_PASS = 0.3       # 合格阈值

    BREATH_EXCELLENT = 0.15  # 满分阈值（波动系数）
    BREATH_GOOD = 0.25       # 良好阈值
    BREATH_PASS = 0.35       # 合格阈值

    # 底线规则阈值
    CONSECUTIVE_OFF_THRESHOLD = 3  # 连续跑调阈值
    OFF_BEAT_THRESHOLD = 2         # 脱离节拍段阈值

    # 等级划分
    LEVELS = {
        (90, 100): ("专业级", "★★★", "#22c55e"),
        (80, 90): ("优秀", "★★☆", "#3b82f6"),
        (70, 80): ("良好", "★★", "#10b981"),
        (60, 70): ("中等", "★☆", "#f59e0b"),
        (50, 60): ("及格", "★", "#f97316"),
        (0, 50): ("待改进", "☆", "#ef4444")
    }

    def __init__(self, singing_style: str = 'pop'):
        """
        初始化评分服务

        Args:
            singing_style: 唱法类型 (pop/classical/folk/rap)
        """
        self.singing_style = singing_style
        self.weights = self._adjust_weights_for_style(singing_style)

    def _adjust_weights_for_style(self, style: str) -> Dict[str, float]:
        """根据唱法调整权重（确保总和为100%）"""
        if style == 'rap':
            # 说唱：节奏权重提高
            return {
                'pitch': 0.20,
                'rhythm': 0.35,
                'breath': 0.15,
                'technique': 0.20,
                'artistry': 0.10
            }
        elif style == 'classical':
            # 美声：发声技术和艺术表现权重提高
            return {
                'pitch': 0.25,
                'rhythm': 0.15,
                'breath': 0.15,
                'technique': 0.30,
                'artistry': 0.15
            }
        elif style == 'folk':
            # 民族：艺术表现权重提高
            return {
                'pitch': 0.25,
                'rhythm': 0.18,
                'breath': 0.17,
                'technique': 0.20,
                'artistry': 0.20
            }
        else:
            # 流行（默认）
            return self.WEIGHTS.copy()

    def calculate(
        self,
        features: AudioFeaturesResult,
        emotion_confidence: float = 0.5,
        emotions: Dict[str, float] = None,
        voice_quality_score: float = 100.0
    ) -> ScoreResultV4:
        """
        计算五维评分

        Args:
            features: 音频特征提取结果
            emotion_confidence: 情感识别置信度
            emotions: 情感分布
            voice_quality_score: 人声质量分数

        Returns:
            ScoreResultV4: 评分结果
        """
        result = ScoreResultV4()
        result.critical_issues = []

        # 1. 音准评分
        pitch_score, pitch_diagnosis = self._calculate_pitch_score(
            features.pitch_deviation
        )
        result.pitch_score = pitch_score
        result.pitch_diagnosis = pitch_diagnosis

        # 2. 节奏评分
        rhythm_score, rhythm_diagnosis = self._calculate_rhythm_score(
            features.rhythm_alignment
        )
        result.rhythm_score = rhythm_score
        result.rhythm_diagnosis = rhythm_diagnosis

        # 3. 气息评分
        breath_score, breath_diagnosis = self._calculate_breath_score(
            features.breath_stability
        )
        result.breath_score = breath_score
        result.breath_diagnosis = breath_diagnosis

        # 4. 发声技术评分
        technique_score, technique_diagnosis = self._calculate_technique_score(
            features.hnr, features.cpp, features.vocal_technique
        )
        result.technique_score = technique_score
        result.technique_diagnosis = technique_diagnosis

        # 5. 艺术表现评分
        artistry_score, artistry_diagnosis = self._calculate_artistry_score(
            emotion_confidence, emotions, features.vocal_technique
        )
        result.artistry_score = artistry_score
        result.artistry_diagnosis = artistry_diagnosis

        # 6. 计算加权总分
        total = (
            pitch_score * self.weights['pitch'] +
            rhythm_score * self.weights['rhythm'] +
            breath_score * self.weights['breath'] +
            technique_score * self.weights['technique'] +
            artistry_score * self.weights['artistry']
        )

        # 7. 人声质量惩罚
        if voice_quality_score < 60:
            quality_penalty = (60 - voice_quality_score) / 60 * 40
            total = max(0, total - quality_penalty)
            result.critical_issues.append(f"人声质量不足，扣{quality_penalty:.1f}分")

        result.total_score = round(total, 1)

        # 8. 应用底线规则（在总分计算后应用）
        self._apply_critical_rules(result, features)

        # 9. 确定等级（使用底线规则后的总分）
        result.level, result.grade, result.stars, result.color = self._get_level_info(result.total_score)

        # 10. 兼容旧接口
        result.pitch = result.pitch_score
        result.rhythm = result.rhythm_score
        result.breath = result.breath_score
        result.technique = result.technique_score
        result.emotion = result.artistry_score
        result.volume = result.breath_score  # 兼容映射
        result.total = result.total_score

        return result

    def _calculate_pitch_score(
        self,
        pitch_deviation: PitchDeviationResult
    ) -> tuple:
        """
        音准评分

        专业标准：
        - 满分：MAE_c ≤ 10 音分（人耳几乎不可辨）
        - 良好：MAE_c ≤ 30 音分
        - 合格：MAE_c ≤ 50 音分
        - 底线：连续3个以上音符跑调超半音，扣20分
        """
        diagnosis = PitchDiagnosis()
        mae = pitch_deviation.mae_cents

        # 基础分计算
        if mae <= self.PITCH_EXCELLENT:
            score = 100
            diagnosis.level = "专业级"
        elif mae <= self.PITCH_GOOD:
            # 线性插值
            score = 100 - (mae - self.PITCH_EXCELLENT) / (self.PITCH_GOOD - self.PITCH_EXCELLENT) * 10
            diagnosis.level = "良好"
        elif mae <= self.PITCH_PASS:
            score = 90 - (mae - self.PITCH_GOOD) / (self.PITCH_PASS - self.PITCH_GOOD) * 20
            diagnosis.level = "合格"
        else:
            score = max(0, 70 - (mae - self.PITCH_PASS) * 0.5)
            diagnosis.level = "待改进"

        # 检测率惩罚
        if pitch_deviation.detection_rate < 0.5:
            penalty = (0.5 - pitch_deviation.detection_rate) * 30
            score -= penalty
            diagnosis.issues.append(f"音高检测率低({pitch_deviation.detection_rate*100:.0f}%)")

        # 音高断层惩罚
        if pitch_deviation.pitch_breaks > 3:
            penalty = min(15, pitch_deviation.pitch_breaks * 2)
            score -= penalty
            diagnosis.issues.append(f"换声区存在{pitch_deviation.pitch_breaks}处音高断层")

        # 长音波动惩罚
        if pitch_deviation.pitch_wobble > 30:
            penalty = min(10, (pitch_deviation.pitch_wobble - 30) * 0.3)
            score -= penalty
            diagnosis.issues.append(f"长音波动较大({pitch_deviation.pitch_wobble:.0f}音分)")

        score = max(0, min(100, score))

        # 诊断信息
        diagnosis.score = score
        diagnosis.mae_cents = mae

        if mae > self.PITCH_PASS:
            diagnosis.suggestions.append("建议加强音准训练，注意听标准音高")
        if pitch_deviation.pitch_breaks > 0:
            diagnosis.suggestions.append("换声区过渡需要更平滑，可练习音阶过渡")

        return score, diagnosis

    def _calculate_rhythm_score(
        self,
        rhythm_alignment: RhythmAlignmentResult
    ) -> tuple:
        """
        节奏评分

        专业标准：
        - 满分：偏差 ≤ 10% 拍长
        - 良好：偏差 ≤ 20% 拍长
        - 合格：偏差 ≤ 30% 拍长
        - 底线：完全脱离节拍，上限60分
        """
        diagnosis = RhythmDiagnosis()
        deviation = rhythm_alignment.avg_deviation_ratio

        # 基础分计算
        if deviation <= self.RHYTHM_EXCELLENT:
            score = 100
            diagnosis.level = "专业级"
        elif deviation <= self.RHYTHM_GOOD:
            score = 100 - (deviation - self.RHYTHM_EXCELLENT) / (self.RHYTHM_GOOD - self.RHYTHM_EXCELLENT) * 10
            diagnosis.level = "良好"
        elif deviation <= self.RHYTHM_PASS:
            score = 90 - (deviation - self.RHYTHM_GOOD) / (self.RHYTHM_PASS - self.RHYTHM_GOOD) * 20
            diagnosis.level = "合格"
        else:
            score = max(0, 70 - (deviation - self.RHYTHM_PASS) * 100)
            diagnosis.level = "待改进"

        # 节奏不规则度惩罚
        if rhythm_alignment.irregularity > 0.3:
            penalty = min(15, rhythm_alignment.irregularity * 30)
            score -= penalty
            diagnosis.issues.append(f"节奏不规则度较高({rhythm_alignment.irregularity*100:.0f}%)")

        # 节拍密度异常
        bps = rhythm_alignment.beats_per_second
        if bps > 0 and (bps < 0.5 or bps > 5):
            diagnosis.issues.append(f"节拍密度异常({bps:.1f} beats/s)")

        score = max(0, min(100, score))

        diagnosis.score = score
        diagnosis.deviation_ratio = deviation

        if deviation > self.RHYTHM_PASS:
            diagnosis.suggestions.append("建议配合节拍器练习，加强节奏感")

        return score, diagnosis

    def _calculate_breath_score(
        self,
        breath_stability: BreathStabilityResult
    ) -> tuple:
        """
        气息评分 v4.1 - 专业气息评估体系

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
        diagnosis = BreathDiagnosis()

        # 使用专业气息综合得分
        professional_score = breath_stability.professional_breath_score

        # 如果专业得分有效，使用它
        if professional_score > 0:
            score = professional_score
        else:
            # 兼容旧逻辑
            fluctuation = breath_stability.rms_fluctuation

            # 基础分计算（改为60分基础分）
            if fluctuation <= self.BREATH_EXCELLENT:
                score = 100
                diagnosis.level = "专业级"
            elif fluctuation <= self.BREATH_GOOD:
                score = 85 + (self.BREATH_GOOD - fluctuation) / (self.BREATH_GOOD - self.BREATH_EXCELLENT) * 15
                diagnosis.level = "良好"
            elif fluctuation <= self.BREATH_PASS:
                score = 70 + (self.BREATH_PASS - fluctuation) / (self.BREATH_PASS - self.BREATH_GOOD) * 15
                diagnosis.level = "合格"
            else:
                score = max(50, 70 - (fluctuation - self.BREATH_PASS) * 50)
                diagnosis.level = "待改进"

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
            diagnosis.issues.append("检测到艺术化的强弱起伏处理")

        # 长音评估
        if breath_stability.long_note_count > 0:
            if breath_stability.long_note_support_score > 80:
                diagnosis.issues.append(f"长音气息支撑优秀({breath_stability.long_note_count}处)")
                diagnosis.long_note_bonus = 5
            elif breath_stability.long_note_support_score > 60:
                diagnosis.issues.append(f"长音气息支撑良好({breath_stability.long_note_count}处)")
        else:
            # 没有长音不扣分，只是没有加分
            pass

        # 弱唱评估
        if breath_stability.soft_segment_count > 0:
            if breath_stability.soft_singing_quality > 70:
                diagnosis.issues.append("弱唱气息控制优秀")
                diagnosis.soft_singing_bonus = 5
            elif breath_stability.soft_singing_quality > 50:
                diagnosis.issues.append("弱唱气息控制良好")

        # 气口设计评估
        if breath_stability.clean_breath_count > 0:
            diagnosis.issues.append(f"无痕换气{breath_stability.clean_breath_count}处")

        # 气声技巧评估
        if breath_stability.controlled_breathiness > 50:
            diagnosis.issues.append("气声技巧运用得当")
        elif breath_stability.uncontrolled_leak > 30:
            diagnosis.issues.append("存在无效漏气")
            diagnosis.suggestions.append("建议加强声带闭合训练，减少漏气")

        # 动态范围评估
        if breath_stability.dynamic_range > 30:
            diagnosis.issues.append(f"动态范围宽广({breath_stability.dynamic_range:.0f}dB)")

        # 严重问题（仅严重问题才扣分）
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

    def _calculate_technique_score(
        self,
        hnr: float,
        cpp: float,
        technique: VocalTechniqueResult
    ) -> tuple:
        """
        发声技术评分

        组成部分：
        - HNR (声带闭合): 40%
        - CPP (声带闭合质量): 30%
        - 技巧完成度: 30%
        """
        diagnosis = TechniqueDiagnosis()

        # HNR 评分 - 根据唱法调整标准
        # 注意：轻柔唱法/气声唱法的HNR天然较低（6-12dB是正常的）
        # 参考：
        # - 美声: 18-25dB (完全闭合)
        # - 流行实声: 12-18dB
        # - 流行轻柔/气声: 6-12dB (这是艺术选择，不是技术问题)
        if self.singing_style == 'classical':
            # 美声：HNR > 20dB 满分
            hnr_score = min(100, hnr / 20 * 100)
        elif self.singing_style == 'folk':
            # 民族：HNR 15-20dB 满分
            if hnr >= 18:
                hnr_score = 100
            elif hnr >= 12:
                hnr_score = 70 + (hnr - 12) * 5
            else:
                hnr_score = max(40, hnr / 12 * 70)
        else:
            # 流行：需要区分唱法类型
            # 如果技巧分高，说明唱法是可控的，不应因HNR低而惩罚
            if technique.technique_score >= 70:
                # 高技巧得分，HNR低可能是艺术选择（气声唱法）
                if hnr >= 12:
                    hnr_score = 100
                elif hnr >= 8:
                    # 轻柔唱法的正常范围
                    hnr_score = 75 + (hnr - 8) * 6.25
                elif hnr >= 5:
                    # 气声唱法的正常范围
                    hnr_score = 60 + (hnr - 5) * 5
                else:
                    hnr_score = max(40, hnr / 5 * 60)
            else:
                # 低技巧分，可能是真正的技术问题
                if hnr >= 15:
                    hnr_score = 100
                elif hnr >= 10:
                    hnr_score = 80 + (hnr - 10) * 4
                else:
                    hnr_score = max(30, hnr / 10 * 80)

        # CPP 评分 - 根据唱法调整标准
        # CPP反映声带闭合质量，但流行唱法（尤其是轻柔唱法）CPP天然较低
        # 参考：
        # - 美声: CPP > 2.0 为优秀
        # - 流行实声: CPP > 1.0 为优秀
        # - 流行轻柔/气声: CPP > 0.3 为正常
        if self.singing_style == 'classical':
            if cpp >= 2.0:
                cpp_score = 100
            elif cpp >= 1.0:
                cpp_score = 70 + (cpp - 1.0) * 30
            else:
                cpp_score = max(40, cpp / 1.0 * 70)
        else:
            # 流行/民族：如果技巧分高，CPP低可能是艺术选择
            if technique.technique_score >= 70:
                if cpp >= 0.5:
                    cpp_score = 85
                elif cpp >= 0.2:
                    cpp_score = 70 + (cpp - 0.2) * 50
                else:
                    cpp_score = max(50, 50 + cpp * 100)
            else:
                if cpp >= 1.0:
                    cpp_score = 100
                elif cpp >= 0.5:
                    cpp_score = 70 + (cpp - 0.5) * 60
                else:
                    cpp_score = max(30, cpp / 0.5 * 70)

        # 技巧完成度
        technique_score = technique.technique_score

        # 加权平均
        score = hnr_score * 0.4 + cpp_score * 0.3 + technique_score * 0.3

        # 诊断
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
                diagnosis.issues.append(f"颤音规范性有待提高")

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

    def _calculate_artistry_score(
        self,
        emotion_confidence: float,
        emotions: Dict[str, float],
        technique: VocalTechniqueResult
    ) -> tuple:
        """
        艺术表现评分

        组成部分：
        - 情感饱满度: 60%
        - 技巧运用: 40%

        注意：emotion_confidence 是模型返回的最大情感概率（通常0.2-0.5），
        不能直接作为情感得分。需要结合情感多样性和技巧运用综合评估。
        """
        diagnosis = ArtistryDiagnosis()

        # 情感评分 - 基于情感多样性和强度
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
        else:
            # 没有情感数据，使用置信度作为基础
            emotion_score = max(50, emotion_confidence * 100)

        emotion_score = max(0, min(100, emotion_score))

        # 技巧运用评分
        dynamics_score = 50
        if technique.vibrato_count > 0:
            dynamics_score += min(20, technique.vibrato_count * 2)
        if technique.slide_count > 0:
            dynamics_score += min(15, technique.slide_count * 3)
        if technique.falsetto_segments > 0:
            dynamics_score += min(15, technique.falsetto_segments * 3)

        dynamics_score = max(0, min(100, dynamics_score))

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

    def _apply_critical_rules(
        self,
        result: ScoreResultV4,
        features: AudioFeaturesResult
    ):
        """
        应用底线规则

        规则：
        1. 连续5个以上音符跑调超半音 → 扣20分
        2. 严重脱离节拍(≥5段) → 上限70分
        3. 严重漏气/破音 → 不合格
        """
        # 规则1：连续跑调（阈值从3提高到5，避免误判）
        if features.pitch_deviation.consecutive_off_notes >= 5:
            result.total_score = max(0, result.total_score - 20)
            result.critical_issues.append(
                f"连续{features.pitch_deviation.consecutive_off_notes}个音符跑调，扣20分"
            )
            result.is_disqualified = True

        # 规则2：脱离节拍（阈值从2提高到5，流行歌曲切分音是正常的）
        if features.rhythm_alignment.off_beat_segments >= 5:
            result.total_score = min(result.total_score, 70)
            result.critical_issues.append("严重脱离节拍，总分上限70分")
            result.is_disqualified = True

        # 规则3：严重漏气
        if features.hnr < 3:
            result.total_score = min(result.total_score, 50)
            result.critical_issues.append("HNR过低（严重漏气），总分上限50分")
            result.is_disqualified = True

    def _get_level_info(self, total_score: float) -> tuple:
        """根据总分获取等级信息"""
        for (low, high), (level, stars, color) in self.LEVELS.items():
            if low <= total_score < high:
                grade = level[0] if level != "待改进" else "D"
                return level, grade, stars, color

        return "待改进", "D", "☆", "#ef4444"


# 保持向后兼容
ScoreResult = ScoreResultV4
ScoreService = ScoreServiceV4
