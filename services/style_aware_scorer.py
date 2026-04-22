"""
风格自适应评分系统 v3.0
根据音乐风格自动调整评分标准和权重
使用深度学习模型进行风格和情绪分类

v3.0 改进：
- 使用策略模式重构风格调整逻辑
- 消除 if-elif 分支
- 支持运行时动态注册新策略
"""

import numpy as np
import librosa
import logging
from typing import Dict, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class MusicStyle(Enum):
    """音乐风格枚举"""
    BALLAD = "ballad"        # 抒情/慢歌
    UPBEAT = "upbeat"        # 快歌/舞曲
    ROCK = "rock"            # 摇滚
    RB_JAZZ = "rb_jazz"      # R&B/爵士
    POP = "pop"              # 流行
    FOLK = "folk"            # 民谣


@dataclass
class StyleProfile:
    """风格配置档案"""
    style: MusicStyle
    style_cn: str                    # 中文名
    description: str                  # 描述

    # 评分权重
    pitch_weight: float              # 音准权重
    rhythm_weight: float             # 节奏权重
    breath_weight: float             # 气息权重
    technique_weight: float          # 技术权重
    artistry_weight: float           # 艺术权重

    # 评分阈值调整
    pitch_tolerance: float           # 音准容差（音分）
    rhythm_tolerance: float          # 节奏容差（拍长比例）

    # 特殊考虑
    allow_rubato: bool               # 允许自由速度
    allow_vibrato: bool              # 允许/期望颤音
    expect_high_energy: bool         # 期望高能量


# 预定义的风格配置
STYLE_PROFILES = {
    MusicStyle.BALLAD: StyleProfile(
        style=MusicStyle.BALLAD,
        style_cn="抒情/慢歌",
        description="注重音准、气息控制、情感表达",
        pitch_weight=0.30,
        rhythm_weight=0.15,      # 节奏权重降低，允许自由速度
        breath_weight=0.25,      # 气息权重提高
        technique_weight=0.15,
        artistry_weight=0.15,    # 艺术权重提高
        pitch_tolerance=15,      # 音准容差较小（抒情歌要求精准）
        rhythm_tolerance=0.40,   # 节奏容差最大（允许rubato）
        allow_rubato=True,       # 允许自由速度
        allow_vibrato=True,
        expect_high_energy=False
    ),

    MusicStyle.UPBEAT: StyleProfile(
        style=MusicStyle.UPBEAT,
        style_cn="快歌/舞曲",
        description="注重节奏感、气息支撑、律动",
        pitch_weight=0.22,
        rhythm_weight=0.32,      # 节奏权重最高
        breath_weight=0.20,
        technique_weight=0.16,
        artistry_weight=0.10,
        pitch_tolerance=28,      # 音准容差较大（快歌节奏优先）
        rhythm_tolerance=0.18,   # 节奏容差最小
        allow_rubato=False,
        allow_vibrato=True,
        expect_high_energy=True
    ),

    MusicStyle.ROCK: StyleProfile(
        style=MusicStyle.ROCK,
        style_cn="摇滚",
        description="注重节奏、力量感、爆发力",
        pitch_weight=0.18,
        rhythm_weight=0.25,
        breath_weight=0.20,
        technique_weight=0.22,   # 技术权重提高（力量感）
        artistry_weight=0.15,
        pitch_tolerance=35,      # 音准容差最大（摇滚允许更自由）
        rhythm_tolerance=0.22,
        allow_rubato=False,
        allow_vibrato=True,
        expect_high_energy=True
    ),

    MusicStyle.RB_JAZZ: StyleProfile(
        style=MusicStyle.RB_JAZZ,
        style_cn="R&B/爵士",
        description="注重即兴感、技巧、音色变化",
        pitch_weight=0.22,
        rhythm_weight=0.18,
        breath_weight=0.20,
        technique_weight=0.25,   # 技术权重高（即兴技巧）
        artistry_weight=0.15,
        pitch_tolerance=28,      # 音准容差（允许即兴变化）
        rhythm_tolerance=0.32,   # 节奏容差（允许swing/groove）
        allow_rubato=True,
        allow_vibrato=True,
        expect_high_energy=False
    ),

    MusicStyle.POP: StyleProfile(
        style=MusicStyle.POP,
        style_cn="流行",
        description="均衡评分，注重整体表现",
        pitch_weight=0.28,
        rhythm_weight=0.22,
        breath_weight=0.20,
        technique_weight=0.15,
        artistry_weight=0.15,
        pitch_tolerance=22,      # 中等音准容差
        rhythm_tolerance=0.25,
        allow_rubato=True,
        allow_vibrato=True,
        expect_high_energy=False
    ),

    MusicStyle.FOLK: StyleProfile(
        style=MusicStyle.FOLK,
        style_cn="民谣/抒情",
        description="注重情感表达、音准、气息",
        pitch_weight=0.26,
        rhythm_weight=0.18,
        breath_weight=0.22,
        technique_weight=0.14,
        artistry_weight=0.20,    # 艺术权重最高
        pitch_tolerance=20,      # 音准要求较高
        rhythm_tolerance=0.35,   # 节奏容差（叙事性自由）
        allow_rubato=True,
        allow_vibrato=True,
        expect_high_energy=False
    ),
}


class StyleAnalyzer:
    """音乐风格分析器 - 使用深度学习模型"""

    def __init__(self, use_dl: bool = True):
        self._dl_classifier = None
        self._use_dl = use_dl

        if use_dl:
            try:
                from services.dl_services.dl_style_classifier import DLStyleClassifier
                self._dl_classifier = DLStyleClassifier()
                logger.info("[StyleAnalyzer] Using DL classifier")
            except Exception as e:
                logger.warning(f"[StyleAnalyzer] Failed to load DL classifier: {e}")
                self._use_dl = False

    def analyze(self, audio_path: str, sr: int = 16000) -> Tuple[MusicStyle, Dict[str, float]]:
        """
        分析音乐风格

        Args:
            audio_path: 音频文件路径
            sr: 采样率

        Returns:
            (风格, 特征字典)
        """
        if self._use_dl and self._dl_classifier:
            return self._analyze_dl(audio_path)
        else:
            # 降级到启发式方法
            import librosa
            y, sr = librosa.load(audio_path, sr=sr, mono=True)
            features = self._extract_features(y, sr)
            style = self._classify_style(features)
            return style, features

    def _analyze_dl(self, audio_path: str) -> Tuple[MusicStyle, Dict[str, float]]:
        """使用深度学习模型分析"""
        result = self._dl_classifier.classify(audio_path)

        # 将DL分类结果映射到内部风格
        genre_to_style = {
            'pop': MusicStyle.POP,
            'folk': MusicStyle.FOLK,
            'rock': MusicStyle.ROCK,
            'rb_soul': MusicStyle.RB_JAZZ,
            'jazz': MusicStyle.RB_JAZZ,
            'classical': MusicStyle.BALLAD,
            'electronic': MusicStyle.UPBEAT,
            'hiphop': MusicStyle.UPBEAT,
            'country': MusicStyle.FOLK,
            'blues': MusicStyle.RB_JAZZ,
            'unknown': MusicStyle.POP
        }

        style = genre_to_style.get(result.genre.value, MusicStyle.POP)

        features = {
            'genre': result.genre.value,
            'genre_confidence': result.genre_confidence,
            'mood': result.mood.value,
            'mood_confidence': result.mood_confidence,
            'method': result.method
        }

        return style, features

    def _extract_features(self, y: np.ndarray, sr: int) -> Dict[str, float]:
        """提取风格判别特征（启发式降级方案）"""
        features = {}

        try:
            # 1. 节奏特征
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            features['tempo'] = float(np.atleast_1d(tempo)[0])

            # 2. 能量特征
            rms = librosa.feature.rms(y=y)[0]
            features['energy_mean'] = float(np.mean(rms))
            features['dynamic_range'] = float(np.max(rms) - np.min(rms))

        except Exception as e:
            logger.warning(f"[StyleAnalyzer] Feature extraction failed: {e}")

        return features

    def _classify_style(self, features: Dict[str, float]) -> MusicStyle:
        """根据特征分类音乐风格（启发式降级方案）"""
        tempo = features.get('tempo', 120)
        dynamic_range = features.get('dynamic_range', 0.2)

        if tempo < 80:
            return MusicStyle.BALLAD
        elif tempo > 140:
            return MusicStyle.UPBEAT
        elif dynamic_range > 0.3:
            return MusicStyle.ROCK
        else:
            return MusicStyle.POP

    def get_style_profile(self, style: MusicStyle) -> StyleProfile:
        """
        获取风格配置档案

        v3.0 改进：优先从外部配置文件加载，支持热更新
        """
        # 尝试从外部配置加载
        try:
            from services.style_config_loader import StyleConfigLoader
            return StyleConfigLoader.load(style)
        except Exception as e:
            logger.warning(f"Failed to load from config file: {e}, using built-in defaults")
            # 降级到内置配置
            return STYLE_PROFILES.get(style, STYLE_PROFILES[MusicStyle.POP])


class StyleAwareScorer:
    """
    风格自适应评分器 v3.0

    根据音乐风格自动调整评分标准和权重
    使用策略模式实现五维评分风格适配

    改进：
    - 使用 StyleAdjustmentRegistry 策略注册表
    - 消除冗长的 if-elif 分支
    - 支持运行时动态注册新策略
    """

    # 基准音准容差（音分）
    BASE_PITCH_TOLERANCE = 20.0

    # 基准节奏容差（拍长比例）
    BASE_RHYTHM_TOLERANCE = 0.25

    def __init__(self):
        self.style_analyzer = StyleAnalyzer()
        # 导入策略注册表
        from services.style_adjustment_strategies import (
            StyleAdjustmentRegistry,
            calculate_mood_bonus
        )
        self._registry = StyleAdjustmentRegistry
        self._calculate_mood_bonus = calculate_mood_bonus

    def analyze_style(self, y: np.ndarray, sr: int) -> Tuple[StyleProfile, Dict[str, float]]:
        """
        分析音乐风格并返回配置档案

        Args:
            y: 音频波形
            sr: 采样率

        Returns:
            (风格配置, 特征字典)
        """
        style, features = self.style_analyzer.analyze(y, sr)
        profile = self.style_analyzer.get_style_profile(style)
        return profile, features

    def adjust_score(self, dimension: str, score: float, profile: StyleProfile) -> float:
        """
        通用调整入口 - 使用策略注册表

        Args:
            dimension: 维度名称 (pitch/rhythm/breath/technique/artistry)
            score: 基础分数
            profile: 风格配置

        Returns:
            调整后的分数
        """
        # 获取风格名称（从枚举值）
        style_name = profile.style.value if hasattr(profile.style, 'value') else str(profile.style)

        # 从注册表获取调整策略
        adjuster = self._registry.get_adjustment(dimension, style_name)

        # 应用调整
        adjusted = adjuster(score, profile)

        return min(100, max(0, adjusted))

    def adjust_pitch_score(self, base_score: float, profile: StyleProfile) -> float:
        """
        根据风格调整音准评分 v3.0

        使用策略模式替代原有 if-elif 分支
        """
        return self.adjust_score('pitch', base_score, profile)

    def adjust_rhythm_score(self, base_score: float, profile: StyleProfile) -> float:
        """
        根据风格调整节奏评分 v3.0

        使用策略模式替代原有 if-elif 分支
        """
        return self.adjust_score('rhythm', base_score, profile)

    def adjust_breath_score(self, base_score: float, profile: StyleProfile) -> float:
        """
        根据风格调整气息评分 v3.0

        使用策略模式替代原有 if-elif 分支
        """
        return self.adjust_score('breath', base_score, profile)

    def adjust_technique_score(self, base_score: float, profile: StyleProfile) -> float:
        """
        根据风格调整技术评分 v3.0

        使用策略模式替代原有 if-elif 分支
        """
        return self.adjust_score('technique', base_score, profile)

    def adjust_artistry_score(
        self,
        base_score: float,
        profile: StyleProfile,
        mood: str = None
    ) -> float:
        """
        根据风格调整艺术表现评分 v3.0

        使用策略模式替代原有 if-elif 分支
        支持情绪匹配加分
        """
        # 获取风格名称
        style_name = profile.style.value if hasattr(profile.style, 'value') else str(profile.style)

        # 从注册表获取调整策略
        adjusted = self.adjust_score('artistry', base_score, profile)

        # 根据情绪匹配度额外加分
        if mood:
            mood_bonus = self._calculate_mood_bonus(style_name, mood)
            adjusted += mood_bonus

        return min(100, max(0, adjusted))

    def get_adjusted_weights(self, profile: StyleProfile) -> Dict[str, float]:
        """
        获取调整后的评分权重

        Returns:
            权重字典，确保总和为1.0
        """
        weights = {
            'pitch': profile.pitch_weight,
            'rhythm': profile.rhythm_weight,
            'breath': profile.breath_weight,
            'technique': profile.technique_weight,
            'artistry': profile.artistry_weight
        }

        # 归一化确保总和为1.0
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}

        return weights

    def calculate_style_aware_score(
        self,
        pitch_score: float,
        rhythm_score: float,
        breath_score: float,
        technique_score: float,
        artistry_score: float,
        profile: StyleProfile,
        mood: str = None
    ) -> Tuple[float, Dict[str, float]]:
        """
        计算风格自适应的总分 v2.0

        Args:
            各维度原始分数
            profile: 风格配置
            mood: 情绪类型（可选）

        Returns:
            (总分, 调整后的各维度分数)
        """
        # 调整各维度分数
        adjusted_pitch = self.adjust_pitch_score(pitch_score, profile)
        adjusted_rhythm = self.adjust_rhythm_score(rhythm_score, profile)
        adjusted_breath = self.adjust_breath_score(breath_score, profile)
        adjusted_technique = self.adjust_technique_score(technique_score, profile)
        adjusted_artistry = self.adjust_artistry_score(artistry_score, profile, mood)

        adjusted_scores = {
            'pitch': adjusted_pitch,
            'rhythm': adjusted_rhythm,
            'breath': adjusted_breath,
            'technique': adjusted_technique,
            'artistry': adjusted_artistry
        }

        # 获取权重
        weights = self.get_adjusted_weights(profile)

        # 计算加权总分
        total = sum(adjusted_scores[k] * weights[k] for k in weights)

        return total, adjusted_scores

    def get_style_adjustment_summary(
        self,
        base_scores: Dict[str, float],
        profile: StyleProfile,
        mood: str = None
    ) -> Dict:
        """
        获取风格调整摘要

        Args:
            base_scores: 各维度基础分数
            profile: 风格配置
            mood: 情绪类型

        Returns:
            调整摘要字典
        """
        adjusted_pitch = self.adjust_pitch_score(base_scores.get('pitch', 0), profile)
        adjusted_rhythm = self.adjust_rhythm_score(base_scores.get('rhythm', 0), profile)
        adjusted_breath = self.adjust_breath_score(base_scores.get('breath', 0), profile)
        adjusted_technique = self.adjust_technique_score(base_scores.get('technique', 0), profile)
        adjusted_artistry = self.adjust_artistry_score(base_scores.get('artistry', 0), profile, mood)

        return {
            'style': profile.style.value,
            'style_cn': profile.style_cn,
            'adjustments': {
                'pitch': {
                    'base': base_scores.get('pitch', 0),
                    'adjusted': adjusted_pitch,
                    'delta': adjusted_pitch - base_scores.get('pitch', 0)
                },
                'rhythm': {
                    'base': base_scores.get('rhythm', 0),
                    'adjusted': adjusted_rhythm,
                    'delta': adjusted_rhythm - base_scores.get('rhythm', 0)
                },
                'breath': {
                    'base': base_scores.get('breath', 0),
                    'adjusted': adjusted_breath,
                    'delta': adjusted_breath - base_scores.get('breath', 0)
                },
                'technique': {
                    'base': base_scores.get('technique', 0),
                    'adjusted': adjusted_technique,
                    'delta': adjusted_technique - base_scores.get('technique', 0)
                },
                'artistry': {
                    'base': base_scores.get('artistry', 0),
                    'adjusted': adjusted_artistry,
                    'delta': adjusted_artistry - base_scores.get('artistry', 0)
                }
            },
            'weights': self.get_adjusted_weights(profile)
        }
