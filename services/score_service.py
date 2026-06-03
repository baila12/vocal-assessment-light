"""
评分计算服务 v5.2 - 模块化重构版

核心原则：
1. 风格自适应：根据音乐风格自动调整评分权重和标准
2. 深度学习增强：整合SingMOS等模型的MOS预测
3. 专业权重分配：根据风格动态调整各维度权重
4. 底线规则：连续跑调、脱离节拍一票否决
5. 精确量化：音分偏差、拍长归一化、专业气息评估、HNR、CPP
6. 正向加分为主、负向扣分为辅

v5.2 改进：
- 模块化重构：各维度评分器独立为单独模块
- 单一职责：ScoreServiceV4 作为协调器，委托具体评分给各评分器
"""
from typing import Dict, Optional
import numpy as np
import logging

from services.audio_features_service import AudioFeaturesResult
from services.style_aware_scorer import StyleProfile
from services.scoring_config import ScoringConfig, default_scoring_config
from services.scoring import (
    ScoreResultV4,
    PitchScorer,
    RhythmScorer,
    BreathScorer,
    TechniqueScorer,
    ArtistryScorer,
    CriticalRulesHandler
)

logger = logging.getLogger(__name__)


class ScoreServiceV4:
    """
    评分计算服务 v5.2（模块化重构版）

    采用专业声乐评估体系：
    - 音准 30% + 节奏 20% + 气息 20% + 发声技术 20% + 艺术表现 10%
    - 底线规则：连续跑调、脱离节拍一票否决
    - 气息专项优化：区分艺术化起伏、可控气声，正向加分机制
    - 深度学习增强：整合SingMOS MOS预测

    v5.2 改进：
    - 模块化：各维度评分委托给独立评分器
    - 可测试：各评分器可独立单元测试
    """

    # 等级划分 v5.10 — 匹配新的分数分布
    LEVELS = {
        (88, 100): ("专业级", "★★★", "#22c55e"),
        (78, 88):  ("优秀",   "★★☆", "#3b82f6"),
        (62, 78):  ("良好",   "★★",  "#10b981"),
        (45, 62):  ("中等",   "★☆",  "#f59e0b"),
        (25, 45):  ("及格",   "★",   "#f97316"),
        (0, 25):   ("待改进", "☆",   "#ef4444"),
    }

    def __init__(
        self,
        singing_style: str = 'pop',
        scoring_config: Optional[ScoringConfig] = None
    ):
        """
        初始化评分服务

        Args:
            singing_style: 唱法类型 (pop/classical/folk/rap)
            scoring_config: 评分配置（可选，支持依赖注入）
        """
        self.singing_style = singing_style
        self._config = scoring_config or default_scoring_config
        self.weights = self._adjust_weights_for_style(singing_style)

        # 初始化各维度评分器
        self._pitch_scorer = PitchScorer(self._config.pitch, self._config.empirical)
        self._rhythm_scorer = RhythmScorer(self._config.rhythm, self._config.empirical)
        self._breath_scorer = BreathScorer(self._config.breath)
        self._technique_scorer = TechniqueScorer(
            self._config.technique, singing_style, self._config.empirical
        )
        self._artistry_scorer = ArtistryScorer()
        self._critical_handler = CriticalRulesHandler(self._config.critical)

    @property
    def config(self) -> ScoringConfig:
        """获取当前配置"""
        return self._config

    def set_config(self, config: ScoringConfig) -> None:
        """
        设置新配置（支持运行时切换）

        Args:
            config: 新的评分配置
        """
        self._config = config
        # 更新各评分器的配置
        self._pitch_scorer = PitchScorer(config.pitch, config.empirical)
        self._rhythm_scorer = RhythmScorer(config.rhythm, config.empirical)
        self._breath_scorer = BreathScorer(config.breath)
        self._technique_scorer = TechniqueScorer(config.technique, self.singing_style, config.empirical)
        self._critical_handler = CriticalRulesHandler(config.critical)
        logger.info(f"Scoring config updated: pitch.excellent={config.pitch.excellent}")

    # 兼容旧代码的属性访问
    @property
    def PITCH_EXCELLENT(self) -> float:
        return self._config.pitch.excellent

    @property
    def PITCH_GOOD(self) -> float:
        return self._config.pitch.good

    @property
    def PITCH_PASS(self) -> float:
        return self._config.pitch.pass_threshold

    @property
    def RHYTHM_EXCELLENT(self) -> float:
        return self._config.rhythm.excellent

    @property
    def RHYTHM_GOOD(self) -> float:
        return self._config.rhythm.good

    @property
    def RHYTHM_PASS(self) -> float:
        return self._config.rhythm.pass_threshold

    @property
    def BREATH_EXCELLENT(self) -> float:
        return self._config.breath.excellent

    @property
    def BREATH_GOOD(self) -> float:
        return self._config.breath.good

    @property
    def BREATH_PASS(self) -> float:
        return self._config.breath.pass_threshold

    @property
    def CONSECUTIVE_OFF_THRESHOLD(self) -> int:
        return self._config.critical.consecutive_off_notes

    @property
    def OFF_BEAT_THRESHOLD(self) -> int:
        return self._config.critical.off_beat_segments

    @property
    def OFF_BEAT_RATIO_THRESHOLD(self) -> float:
        return self._config.critical.off_beat_ratio

    def _adjust_weights_for_style(self, style: str) -> Dict[str, float]:
        """根据唱法调整权重（确保总和为100%）"""
        return self._config.weights.get_adjusted_weights(style)

    def calculate(
        self,
        features: AudioFeaturesResult,
        emotion_confidence: float = 0.5,
        emotions: Dict[str, float] = None,
        voice_quality_score: float = 100.0,
        style_profile: StyleProfile = None,
        music_mood: str = None,
        dl_mos_score: float = 0.0,
        dl_mos_normalized: float = 0.0,
        dl_method: str = "none",
        dl_confidence: float = 0.0,
        scoring_config: 'ScoringConfig' = None,
        user_filepath: str = None,
        reference_path: str = None,
        # v5.14: 原始音频特征 (供 ArtistryScorer 直接计算)
        audio_data: np.ndarray = None,
        f0: np.ndarray = None,
        sample_rate: int = 22050
    ) -> ScoreResultV4:
        """
        计算五维评分 v5.10 - DTW参考评分增强

        Args:
            features: 音频特征提取结果
            emotion_confidence: 情感识别置信度
            emotions: 情感分布
            voice_quality_score: 人声质量分数
            style_profile: 风格配置档案（可选，用于风格自适应评分）
            music_mood: 音乐情绪类型（可选，用于艺术表现评分）
            dl_mos_score: 深度学习预测的MOS分数(1-5)
            dl_mos_normalized: 归一化的MOS分数(0-100)
            dl_method: 使用的DL方法
            dl_confidence: DL置信度
            scoring_config: 评分配置（可选，用于快速/专业模式切换）
            user_filepath: 用户音频文件路径（用于DTW参考对比）
            reference_path: 参考音频文件路径（用于DTW参考对比）

        Returns:
            ScoreResultV4: 评分结果
        """
        # 如果提供了配置，临时切换
        original_config = self._config
        if scoring_config:
            self.set_config(scoring_config)

        result = ScoreResultV4()
        result.critical_issues = []

        # 存储DL评估结果
        result.dl_mos_score = dl_mos_score
        result.dl_mos_normalized = dl_mos_normalized
        result.dl_method = dl_method
        result.dl_confidence = dl_confidence

        # 如果提供了风格配置，使用风格自适应权重
        if style_profile:
            self.weights = {
                'pitch': style_profile.pitch_weight,
                'rhythm': style_profile.rhythm_weight,
                'breath': style_profile.breath_weight,
                'technique': style_profile.technique_weight,
                'artistry': style_profile.artistry_weight
            }
            # 归一化
            total_weight = sum(self.weights.values())
            if total_weight > 0:
                self.weights = {k: v / total_weight for k, v in self.weights.items()}

        # 初始化风格自适应评分器
        style_scorer = None
        if style_profile:
            from services.style_aware_scorer import StyleAwareScorer
            style_scorer = StyleAwareScorer()

        # 1. 音准评分
        pitch_score, pitch_diagnosis = self._pitch_scorer.calculate(
            features.pitch_deviation
        )
        if style_scorer:
            pitch_score = style_scorer.adjust_pitch_score(pitch_score, style_profile)
        result.pitch_score = pitch_score
        result.pitch_diagnosis = pitch_diagnosis

        # 2. 节奏评分
        rhythm_score, rhythm_diagnosis = self._rhythm_scorer.calculate(
            features.rhythm_alignment
        )
        if style_scorer:
            rhythm_score = style_scorer.adjust_rhythm_score(rhythm_score, style_profile)
        result.rhythm_score = rhythm_score
        result.rhythm_diagnosis = rhythm_diagnosis

        # 3. 气息评分
        breath_score, breath_diagnosis = self._breath_scorer.calculate(
            features.breath_stability
        )
        if style_scorer:
            breath_score = style_scorer.adjust_breath_score(breath_score, style_profile)
        result.breath_score = breath_score
        result.breath_diagnosis = breath_diagnosis

        # 4. 发声技术评分
        technique_score, technique_diagnosis = self._technique_scorer.calculate(
            features.hnr, features.cpp, features.vocal_technique,
            is_mixed_audio=features.is_mixed_audio,
            mixed_audio_confidence=features.mixed_audio_confidence
        )
        if style_scorer:
            technique_score = style_scorer.adjust_technique_score(
                technique_score, style_profile
            )
        result.technique_score = technique_score
        result.technique_diagnosis = technique_diagnosis

        # 5. 艺术表现评分 v5.14 — 从四个可靠维度加权合成 + 声学调制
        artistry_score, artistry_diagnosis = self._artistry_scorer.calculate(
            technique=features.vocal_technique,
            breath=features.breath_stability,
            emotion_confidence=emotion_confidence,
            emotions=emotions,
            audio_data=audio_data,
            f0=f0,
            sr=sample_rate,
            pitch_score=pitch_score,
            rhythm_score=rhythm_score,
            breath_score=breath_score,
            technique_score=technique_score
        )
        if style_scorer:
            artistry_score = style_scorer.adjust_artistry_score(
                artistry_score, style_profile, music_mood
            )
        result.artistry_score = artistry_score
        result.artistry_diagnosis = artistry_diagnosis

        # 5b. v5.10 DTW参考对比评分（可选）
        if reference_path and user_filepath:
            self._apply_dtw_reference(
                result, user_filepath, reference_path, self.singing_style
            )
            # 更新局部变量（result 中的分数可能已被 DTW 融合调整）
            pitch_score = result.pitch_score
            rhythm_score = result.rhythm_score

        # 6. 计算加权总分
        total = (
            pitch_score * self.weights['pitch'] +
            rhythm_score * self.weights['rhythm'] +
            breath_score * self.weights['breath'] +
            technique_score * self.weights['technique'] +
            artistry_score * self.weights['artistry']
        )

        # 7. v5.1 深度学习融合
        total = self._apply_dl_fusion(
            total, dl_mos_normalized, dl_confidence
        )

        # 8. 人声质量惩罚 v5.10 — 三层分级惩罚
        if voice_quality_score < 30:
            # 极差质量：惩罚+上限
            total = min(total, 40)
            result.critical_issues.append("人声质量极差，总分上限40分")
        elif voice_quality_score < 65:
            if voice_quality_score < 50:
                quality_penalty = (50 - voice_quality_score) / 50 * 35  # vq=30→14, vq=50→0
            else:
                quality_penalty = (65 - voice_quality_score) / 15 * 6   # vq=50→6, vq=65→0
            total = max(0, total - quality_penalty)
            if quality_penalty > 1:
                result.critical_issues.append(f"人声质量不足，扣{quality_penalty:.1f}分")

        result.total_score = round(total, 1)

        # 9. 应用底线规则
        self._critical_handler.apply(result, features)

        # 9.5 多维度联合极差惩罚 v5.10
        # 当多个维度同时低于阈值，说明整体演唱质量极差，加重惩罚
        poor_dimensions = sum([
            1 if result.pitch_score < 40 else 0,
            1 if result.rhythm_score < 40 else 0,
            1 if result.breath_score < 40 else 0,
            1 if result.technique_score < 40 else 0,
        ])
        if poor_dimensions >= 4:
            result.total_score = min(result.total_score, 40)
            result.critical_issues.append("四维度以上表现均不理想，总分上限40分")
        elif poor_dimensions >= 3:
            result.total_score = min(result.total_score, 55)
            result.critical_issues.append("多项维度表现不佳，总分上限55分")

        # 10. 确定等级
        result.level, result.grade, result.stars, result.color = self._get_level_info(
            result.total_score
        )

        # 11. 兼容旧接口
        result.pitch = result.pitch_score
        result.rhythm = result.rhythm_score
        result.breath = result.breath_score
        result.technique = result.technique_score
        result.emotion = result.artistry_score
        result.volume = result.breath_score
        result.total = result.total_score

        # 12. 恢复原始配置（如果临时切换过）
        if scoring_config:
            self._config = original_config
            self._pitch_scorer = PitchScorer(original_config.pitch, original_config.empirical)
            self._rhythm_scorer = RhythmScorer(original_config.rhythm, original_config.empirical)
            self._breath_scorer = BreathScorer(original_config.breath)
            self._technique_scorer = TechniqueScorer(original_config.technique, self.singing_style, original_config.empirical)
            self._critical_handler = CriticalRulesHandler(original_config.critical)

        return result

    def _apply_dl_fusion(
        self,
        total: float,
        dl_mos_normalized: float,
        dl_confidence: float
    ) -> float:
        """
        应用深度学习融合 v5.12

        WARNING: SingMOS校准映射未经实验验证。
        模型训练目标: 评估合成歌声(TTS singing)的自然度
        实际使用场景: 评估真人演唱质量
        这是跨域应用，融合权重已保守设置为15%。

        Args:
            total: 传统计算的总分
            dl_mos_normalized: 归一化的MOS分数
            dl_confidence: DL置信度

        Returns:
            融合后的总分
        """
        dl_config = self._config
        if not (dl_config.dl_enabled and dl_mos_normalized > 0 and
                dl_confidence > dl_config.dl_min_confidence):
            return total

        # v5.12: DL融合权重从0.4降到0.15，降低跨域误差影响
        dl_weight = min(0.15, dl_confidence * 0.25)  # 从0.4降到0.15
        traditional_weight = 1 - dl_weight

        # 融合总分
        total = total * traditional_weight + dl_mos_normalized * dl_weight

        # 确保融合后分数合理（避免低估）
        if dl_mos_normalized > total:
            boost = (dl_mos_normalized - total) * 0.15  # v5.12: 0.3→0.15
            total = min(100, total + boost)

        return total

    def _apply_dtw_reference(
        self,
        result: ScoreResultV4,
        user_filepath: str,
        reference_path: str,
        singing_style: str
    ) -> None:
        """
        应用DTW参考对比评分 v5.10

        将DTW对齐引擎的音准和节奏评分以50%权重融合到绝对评分中，
        解决"无法区分唱得差和歌曲难"的问题。

        Args:
            result: 当前评分结果（会被原地修改）
            user_filepath: 用户音频路径
            reference_path: 参考音频路径
            singing_style: 唱法类型
        """
        try:
            from services.comparison import ComparisonService

            comparison = ComparisonService(style=singing_style)
            dtw_result = comparison.compare_audio_files(
                reference_path, user_filepath, style=singing_style
            )

            if not dtw_result.get('success'):
                logger.warning(f"DTW comparison failed, keeping absolute scores")
                return

            dtw_pitch = dtw_result['dimensions']['pitch']['score']
            dtw_rhythm = dtw_result['dimensions']['rhythm']['score']
            dtw_confidence = dtw_result.get('confidence', 0.5)

            # 融合：DTW分数 50% + 绝对分数 50%，按DTW置信度加权
            dtw_weight = 0.3 + dtw_confidence * 0.4  # 30%-70% 权重范围

            old_pitch = result.pitch_score
            old_rhythm = result.rhythm_score

            result.pitch_score = round(old_pitch * (1 - dtw_weight) + dtw_pitch * dtw_weight, 1)
            result.rhythm_score = round(old_rhythm * (1 - dtw_weight) + dtw_rhythm * dtw_weight, 1)

            # 记录DTW信息到诊断
            result.pitch_diagnosis.issues.append(
                f"DTW参考对比: {dtw_pitch:.0f}分 (置信度{dtw_confidence:.0%})"
            )
            result.rhythm_diagnosis.issues.append(
                f"DTW参考对比: {dtw_rhythm:.0f}分 (置信度{dtw_confidence:.0%})"
            )

            logger.info(
                f"DTW参考融合: 音准 {old_pitch:.0f}→{result.pitch_score:.0f}, "
                f"节奏 {old_rhythm:.0f}→{result.rhythm_score:.0f} "
                f"(DTW权重={dtw_weight:.0%}, 置信度={dtw_confidence:.0%})"
            )

        except Exception as e:
            logger.warning(f"DTW reference scoring failed: {e}, keeping absolute scores")


    def _get_level_info(self, total_score: float) -> tuple:
        """根据总分获取等级信息 v5.12: 修复边界情况 score>=100 和 score<0"""
        if total_score >= 100:
            return "专业级", "S", "★★★", "#22c55e"
        if total_score < 0:
            return "无效", "?", "☆☆☆☆☆", "#888888"
        for (low, high), (level, stars, color) in self.LEVELS.items():
            if low <= total_score < high:
                grade = level[0] if level != "待改进" else "D"
                return level, grade, stars, color
        # 不应到达这里，但作为最终回退
        return "待改进", "D", "☆", "#ef4444"


# 保持向后兼容
ScoreResult = ScoreResultV4
ScoreService = ScoreServiceV4
