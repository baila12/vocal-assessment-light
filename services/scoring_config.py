"""
评分配置模块
集中管理所有评分相关的阈值和权重配置
支持依赖注入和运行时调整
"""
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
from pathlib import Path
import json
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PitchThresholds:
    """音准评分阈值配置"""
    excellent: float = 12.0    # 满分阈值（音分）- v5.0 放宽
    good: float = 35.0         # 良好阈值 - v5.0 放宽
    pass_threshold: float = 60.0  # 合格阈值 - v5.0 放宽

    def get_score(self, mae_cents: float) -> Tuple[float, str]:
        """
        根据MAE计算基础分数

        Args:
            mae_cents: 平均音分偏差

        Returns:
            (分数, 等级描述)
        """
        if mae_cents <= self.excellent:
            return 100.0, "专业级"
        elif mae_cents <= self.good:
            # 线性插值
            score = 100 - (mae_cents - self.excellent) / (self.good - self.excellent) * 10
            return score, "良好"
        elif mae_cents <= self.pass_threshold:
            score = 90 - (mae_cents - self.good) / (self.pass_threshold - self.good) * 20
            return score, "合格"
        else:
            score = max(0, 70 - (mae_cents - self.pass_threshold) * 0.85)
            return score, "待改进"


@dataclass(frozen=True)
class RhythmThresholds:
    """节奏评分阈值配置"""
    excellent: float = 0.12    # 满分阈值（拍长比例）- v5.0 放宽
    good: float = 0.25         # 良好阈值 - v5.0 放宽
    pass_threshold: float = 0.38  # 合格阈值 - v5.0 放宽

    def get_score(self, deviation_ratio: float) -> Tuple[float, str]:
        """根据偏差比例计算基础分数"""
        if deviation_ratio <= self.excellent:
            return 100.0, "专业级"
        elif deviation_ratio <= self.good:
            score = 100 - (deviation_ratio - self.excellent) / (self.good - self.excellent) * 10
            return score, "良好"
        elif deviation_ratio <= self.pass_threshold:
            score = 90 - (deviation_ratio - self.good) / (self.pass_threshold - self.good) * 20
            return score, "合格"
        else:
            score = max(0, 70 - (deviation_ratio - self.pass_threshold) * 120)
            return score, "待改进"


@dataclass(frozen=True)
class BreathThresholds:
    """气息评分阈值配置"""
    excellent: float = 0.18    # 满分阈值（波动系数）- v5.0 放宽
    good: float = 0.28         # 良好阈值 - v5.0 放宽
    pass_threshold: float = 0.40  # 合格阈值 - v5.0 放宽

    def get_score(self, fluctuation: float) -> Tuple[float, str]:
        """根据波动系数计算基础分数"""
        if fluctuation <= self.excellent:
            return 100.0, "专业级"
        elif fluctuation <= self.good:
            score = 85 + (self.good - fluctuation) / (self.good - self.excellent) * 15
            return score, "良好"
        elif fluctuation <= self.pass_threshold:
            score = 70 + (self.pass_threshold - fluctuation) / (self.pass_threshold - self.good) * 15
            return score, "合格"
        else:
            score = max(0, 70 - (fluctuation - self.pass_threshold) * 60)
            return score, "待改进"


@dataclass(frozen=True)
class CriticalRuleThresholds:
    """底线规则阈值配置"""
    consecutive_off_notes: int = 5      # 连续跑调阈值 - v5.0 提高
    off_beat_segments: int = 3          # 脱离节拍段阈值
    off_beat_ratio: float = 0.4         # 脱离节拍比例阈值 - v5.0 提高
    min_hnr: float = 3.0                # 最低HNR阈值

    def should_apply_pitch_penalty(self, consecutive_off: int) -> bool:
        """是否应用音准底线惩罚"""
        return consecutive_off >= self.consecutive_off_notes

    def should_apply_rhythm_penalty(self, off_beat_ratio: float) -> bool:
        """是否应用节奏底线惩罚"""
        return off_beat_ratio > self.off_beat_ratio

    def should_apply_quality_penalty(self, hnr: float) -> bool:
        """是否应用质量底线惩罚"""
        return hnr < self.min_hnr


@dataclass(frozen=True)
class TechniqueThresholds:
    """技术评分阈值配置"""
    hnr_weight: float = 0.4             # HNR权重
    cpp_weight: float = 0.3             # CPP权重
    technique_weight: float = 0.3       # 技巧完成度权重

    # HNR阈值（按唱法）
    hnr_classical_excellent: float = 20.0
    hnr_pop_excellent: float = 15.0
    hnr_pop_soft_min: float = 5.0       # 气声唱法最低HNR

    # CPP阈值
    cpp_classical_excellent: float = 2.0
    cpp_pop_excellent: float = 1.0

    # 混合音频HNR修正系数 — 经验值，未经实验验证
    hnr_mixed_correction: float = 1.5


@dataclass(frozen=True)
class EmpiricalThresholds:
    """
    经验阈值配置 v5.12

    所有硬编码魔法数字集中管理，标注来源。标注规范:
    [理论依据] - 基于声乐教学标准
    [实验校准] - 基于测试文件的初步校准, 需50+样本验证
    [经验估计] - 无理论/实验依据, 主观判断, 急需校准
    [论文参考] - 参考学术论文阈值设定
    """

    # === 音准特征 ===
    pitch_break_cents: float = 200.0       # [经验估计] 音高断层阈值(音分)
    pitch_wobble_threshold: float = 30.0   # [经验估计] 长音波动惩罚阈值

    # === 节奏特征 ===
    rhythm_irregularity_threshold: float = 0.5    # [经验估计] onset不规则度惩罚阈值, v5.11: 0.3->0.5
    onset_off_beat_multiplier: float = 0.5         # [经验估计] onset偏移判定倍率

    # === CV映射断点 (rhythm.py _cv_to_deviation) ===
    cv_regular: float = 0.3       # [经验估计] 非常规律CV阈值
    cv_normal: float = 0.5        # [经验估计] 正常CV阈值
    cv_moderate: float = 0.8      # [经验估计] 中等CV阈值
    cv_irregular: float = 1.2     # [经验估计] 不规则CV阈值

    # === 气息特征 ===
    breath_baseline_score: float = 40.0            # [经验估计] v5.12: 60->40 各子维度基线分
    breath_soft_threshold_ratio: float = 0.6       # [经验估计] 弱唱判定阈值(RMS均值比例)
    breath_long_note_baseline: float = 40.0        # [经验估计] v5.12: 长音支撑基线分
    breath_dynamic_baseline: float = 40.0          # [经验估计] v5.12: 动态控制基线分
    breath_design_baseline: float = 40.0           # [经验估计] v5.12: 气口设计基线分
    breath_technique_baseline: float = 40.0        # [经验估计] v5.12: 气声技巧基线分
    breath_long_note_max_bonus: float = 15.0       # [经验估计] 长音加分上限
    breath_clean_breath_max_bonus: float = 10.0    # [经验估计] 清洁换气加分上限

    # === 技巧特征 ===
    technique_baseline_score: float = 50.0          # [经验估计] 技巧综合基线分
    vibrato_fft_window_ratio: float = 4.0           # [经验估计] 颤音FFT窗口大小/总长度的最大比例

    # === 艺术表现子维度上限 ===
    artistry_vibrato_max: float = 90.0              # [经验估计] v5.12: 颤音子分上限
    artistry_dynamic_max: float = 90.0              # [经验估计] v5.12: 动态子分上限
    artistry_diversity_max: float = 85.0            # [经验估计] v5.12: 多样性子分上限
    artistry_breath_express_max: float = 85.0       # [经验估计] v5.12: 气息表现子分上限

    # === 声学特征 ===
    hnr_mixed_correction: float = 1.5               # [经验估计] 混合音频HNR修正系数


@dataclass(frozen=True)
class WeightsConfig:
    """评分权重配置"""
    pitch: float = 0.28
    rhythm: float = 0.20
    breath: float = 0.20
    technique: float = 0.18
    artistry: float = 0.14

    # 气息细分权重
    breath_long_note: float = 0.40
    breath_dynamic: float = 0.25
    breath_design: float = 0.20
    breath_technique: float = 0.15

    def to_dict(self) -> Dict[str, float]:
        """转换为字典"""
        return {
            'pitch': self.pitch,
            'rhythm': self.rhythm,
            'breath': self.breath,
            'technique': self.technique,
            'artistry': self.artistry
        }

    def get_adjusted_weights(self, style: str = 'pop') -> Dict[str, float]:
        """根据风格获取调整后的权重"""
        base_weights = self.to_dict()

        if style == 'rap':
            return {
                'pitch': 0.20,
                'rhythm': 0.35,
                'breath': 0.15,
                'technique': 0.20,
                'artistry': 0.10
            }
        elif style == 'classical':
            return {
                'pitch': 0.25,
                'rhythm': 0.15,
                'breath': 0.15,
                'technique': 0.30,
                'artistry': 0.15
            }
        elif style == 'folk':
            return {
                'pitch': 0.25,
                'rhythm': 0.18,
                'breath': 0.17,
                'technique': 0.20,
                'artistry': 0.20
            }

        return base_weights


@dataclass
class ScoringConfig:
    """
    评分总配置（可变，支持运行时调整）

    使用示例：
        config = ScoringConfig()

        # 运行时调整
        config.pitch = PitchThresholds(excellent=15, good=40, pass_threshold=70)

        # 从文件加载
        config.load_from_file("scoring_config.json")
    """
    pitch: PitchThresholds = field(default_factory=PitchThresholds)
    rhythm: RhythmThresholds = field(default_factory=RhythmThresholds)
    breath: BreathThresholds = field(default_factory=BreathThresholds)
    critical: CriticalRuleThresholds = field(default_factory=CriticalRuleThresholds)
    technique: TechniqueThresholds = field(default_factory=TechniqueThresholds)
    weights: WeightsConfig = field(default_factory=WeightsConfig)
    empirical: EmpiricalThresholds = field(default_factory=EmpiricalThresholds)

    # DL融合配置
    dl_enabled: bool = True
    dl_min_confidence: float = 0.3
    dl_max_weight: float = 0.4
    dl_boost_factor: float = 0.3

    def load_from_file(self, filepath: Path) -> bool:
        """
        从JSON文件加载配置

        Args:
            filepath: 配置文件路径

        Returns:
            是否加载成功
        """
        try:
            if not filepath.exists():
                logger.warning(f"Config file not found: {filepath}")
                return False

            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 更新各阈值
            if 'pitch' in data:
                self.pitch = PitchThresholds(**data['pitch'])
            if 'rhythm' in data:
                self.rhythm = RhythmThresholds(**data['rhythm'])
            if 'breath' in data:
                self.breath = BreathThresholds(**data['breath'])
            if 'technique' in data:
                self.technique = TechniqueThresholds(**data['technique'])
            if 'critical' in data:
                self.critical = CriticalRuleThresholds(**data['critical'])
            if 'weights' in data:
                self.weights = WeightsConfig(**data['weights'])
            if 'dl' in data:
                dl_config = data['dl']
                self.dl_enabled = dl_config.get('enabled', True)
                self.dl_min_confidence = dl_config.get('min_confidence', 0.3)
                self.dl_max_weight = dl_config.get('max_weight', 0.4)
                self.dl_boost_factor = dl_config.get('boost_factor', 0.3)

            logger.info(f"Scoring config loaded from {filepath}")
            return True

        except (json.JSONDecodeError, KeyError, TypeError, IOError) as e:
            logger.error(f"Failed to load scoring config: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error loading scoring config: {e}")
            return False

    def save_to_file(self, filepath: Path) -> bool:
        """
        保存配置到JSON文件

        Args:
            filepath: 配置文件路径

        Returns:
            是否保存成功
        """
        try:
            data = {
                'pitch': {
                    'excellent': self.pitch.excellent,
                    'good': self.pitch.good,
                    'pass_threshold': self.pitch.pass_threshold
                },
                'rhythm': {
                    'excellent': self.rhythm.excellent,
                    'good': self.rhythm.good,
                    'pass_threshold': self.rhythm.pass_threshold
                },
                'breath': {
                    'excellent': self.breath.excellent,
                    'good': self.breath.good,
                    'pass_threshold': self.breath.pass_threshold
                },
                'technique': {
                    'hnr_weight': self.technique.hnr_weight,
                    'cpp_weight': self.technique.cpp_weight,
                    'technique_weight': self.technique.technique_weight,
                    'hnr_classical_excellent': self.technique.hnr_classical_excellent,
                    'hnr_pop_excellent': self.technique.hnr_pop_excellent,
                    'hnr_pop_soft_min': self.technique.hnr_pop_soft_min,
                    'cpp_classical_excellent': self.technique.cpp_classical_excellent,
                    'cpp_pop_excellent': self.technique.cpp_pop_excellent
                },
                'critical': {
                    'consecutive_off_notes': self.critical.consecutive_off_notes,
                    'off_beat_segments': self.critical.off_beat_segments,
                    'off_beat_ratio': self.critical.off_beat_ratio,
                    'min_hnr': self.critical.min_hnr
                },
                'weights': self.weights.to_dict(),
                'dl': {
                    'enabled': self.dl_enabled,
                    'min_confidence': self.dl_min_confidence,
                    'max_weight': self.dl_max_weight,
                    'boost_factor': self.dl_boost_factor
                }
            }

            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Scoring config saved to {filepath}")
            return True

        except (json.JSONDecodeError, IOError, OSError) as e:
            logger.error(f"Failed to save scoring config: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error saving scoring config: {e}")
            return False

    def create_relaxed_config(self) -> 'ScoringConfig':
        """
        创建更宽松的配置（用于专业演唱评估）

        Returns:
            新的宽松配置实例
        """
        return ScoringConfig(
            pitch=PitchThresholds(excellent=15, good=40, pass_threshold=70),
            rhythm=RhythmThresholds(excellent=0.15, good=0.30, pass_threshold=0.45),
            breath=BreathThresholds(excellent=0.22, good=0.35, pass_threshold=0.50),
            critical=CriticalRuleThresholds(
                consecutive_off_notes=6,
                off_beat_segments=4,
                off_beat_ratio=0.5,
                min_hnr=2.5
            ),
            weights=self.weights,
            dl_enabled=self.dl_enabled,
            dl_min_confidence=self.dl_min_confidence,
            dl_max_weight=self.dl_max_weight,
            dl_boost_factor=self.dl_boost_factor
        )

    def create_strict_config(self) -> 'ScoringConfig':
        """
        创建更严格的配置（用于初学者评估）

        Returns:
            新的严格配置实例
        """
        return ScoringConfig(
            pitch=PitchThresholds(excellent=8, good=25, pass_threshold=45),
            rhythm=RhythmThresholds(excellent=0.08, good=0.18, pass_threshold=0.30),
            breath=BreathThresholds(excellent=0.12, good=0.22, pass_threshold=0.35),
            critical=CriticalRuleThresholds(
                consecutive_off_notes=3,
                off_beat_segments=2,
                off_beat_ratio=0.3,
                min_hnr=4.0
            ),
            weights=self.weights,
            dl_enabled=self.dl_enabled,
            dl_min_confidence=self.dl_min_confidence,
            dl_max_weight=self.dl_max_weight * 0.5,
            dl_boost_factor=self.dl_boost_factor * 0.5
        )


# 默认配置实例
default_scoring_config = ScoringConfig()
