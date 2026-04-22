"""
风格配置加载器
从外部 YAML 文件加载风格配置，支持热更新
"""
import yaml
import logging
import threading
from typing import Dict, Optional, List
from pathlib import Path
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class MusicStyle(Enum):
    """音乐风格枚举"""
    BALLAD = "ballad"
    UPBEAT = "upbeat"
    ROCK = "rock"
    RB_JAZZ = "rb_jazz"
    POP = "pop"
    FOLK = "folk"


@dataclass
class StyleProfile:
    """风格配置档案"""
    style: MusicStyle
    style_cn: str
    description: str

    # 评分权重
    pitch_weight: float
    rhythm_weight: float
    breath_weight: float
    technique_weight: float
    artistry_weight: float

    # 评分阈值调整
    pitch_tolerance: float
    rhythm_tolerance: float

    # 特殊考虑
    allow_rubato: bool
    allow_vibrato: bool
    expect_high_energy: bool


class StyleConfigLoader:
    """
    风格配置加载器 - 支持从配置文件动态加载

    功能：
    1. 从 YAML 文件加载风格配置
    2. 配置缓存
    3. 热重载
    4. 配置验证
    """

    _cache: Dict[MusicStyle, StyleProfile] = {}
    _mood_matching: Dict[str, Dict] = {}
    _config_path: Path = Path("config/styles.yaml")
    _loaded: bool = False
    _lock: threading.Lock = threading.Lock()  # 线程安全锁

    @classmethod
    def set_config_path(cls, path: Path) -> None:
        """
        设置配置文件路径

        Args:
            path: 配置文件路径
        """
        cls._config_path = path
        cls._loaded = False
        cls._cache.clear()

    @classmethod
    def load(cls, style: MusicStyle) -> StyleProfile:
        """
        加载风格配置（带缓存）

        Args:
            style: 音乐风格

        Returns:
            风格配置档案
        """
        if not cls._loaded:
            with cls._lock:
                # 双重检查锁定模式
                if not cls._loaded:
                    cls._load_all()

        return cls._cache.get(style, cls._default_profile(style))

    @classmethod
    def get_mood_matching(cls) -> Dict[str, Dict]:
        """
        获取情绪匹配配置

        Returns:
            情绪匹配配置字典
        """
        if not cls._loaded:
            with cls._lock:
                if not cls._loaded:
                    cls._load_all()

        return cls._mood_matching

    @classmethod
    def _load_all(cls) -> None:
        """从配置文件加载所有风格"""
        if not cls._config_path.exists():
            logger.warning(f"Config file not found: {cls._config_path}, using defaults")
            cls._cache = cls._default_profiles()
            cls._loaded = True
            return

        try:
            with open(cls._config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            profiles = {}
            for style_key, style_config in config.get('styles', {}).items():
                try:
                    style_enum = MusicStyle(style_key)
                    profiles[style_enum] = StyleProfile(
                        style=style_enum,
                        style_cn=style_config['style_cn'],
                        description=style_config['description'],
                        pitch_weight=style_config['weights']['pitch'],
                        rhythm_weight=style_config['weights']['rhythm'],
                        breath_weight=style_config['weights']['breath'],
                        technique_weight=style_config['weights']['technique'],
                        artistry_weight=style_config['weights']['artistry'],
                        pitch_tolerance=style_config['thresholds']['pitch_tolerance'],
                        rhythm_tolerance=style_config['thresholds']['rhythm_tolerance'],
                        allow_rubato=style_config['flags']['allow_rubato'],
                        allow_vibrato=style_config['flags']['allow_vibrato'],
                        expect_high_energy=style_config['flags']['expect_high_energy']
                    )
                except (KeyError, ValueError) as e:
                    logger.warning(f"Invalid style config for {style_key}: {e}")

            cls._cache = profiles
            cls._mood_matching = config.get('mood_matching', {})
            cls._loaded = True

            logger.info(f"Loaded {len(profiles)} style profiles from {cls._config_path}")

        except Exception as e:
            logger.error(f"Failed to load style config: {e}")
            cls._cache = cls._default_profiles()
            cls._loaded = True

    @classmethod
    def reload(cls) -> None:
        """热重载配置"""
        with cls._lock:
            cls._loaded = False
            cls._cache.clear()
            cls._load_all()
        logger.info("Style configurations reloaded")

    @classmethod
    def _default_profiles(cls) -> Dict[MusicStyle, StyleProfile]:
        """默认风格配置（当配置文件不存在时使用）"""
        return {
            MusicStyle.BALLAD: StyleProfile(
                style=MusicStyle.BALLAD,
                style_cn="抒情/慢歌",
                description="注重音准、气息控制、情感表达",
                pitch_weight=0.30,
                rhythm_weight=0.15,
                breath_weight=0.25,
                technique_weight=0.15,
                artistry_weight=0.15,
                pitch_tolerance=15,
                rhythm_tolerance=0.40,
                allow_rubato=True,
                allow_vibrato=True,
                expect_high_energy=False
            ),
            MusicStyle.UPBEAT: StyleProfile(
                style=MusicStyle.UPBEAT,
                style_cn="快歌/舞曲",
                description="注重节奏感、气息支撑、律动",
                pitch_weight=0.22,
                rhythm_weight=0.32,
                breath_weight=0.20,
                technique_weight=0.16,
                artistry_weight=0.10,
                pitch_tolerance=28,
                rhythm_tolerance=0.18,
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
                technique_weight=0.22,
                artistry_weight=0.15,
                pitch_tolerance=35,
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
                technique_weight=0.25,
                artistry_weight=0.15,
                pitch_tolerance=28,
                rhythm_tolerance=0.32,
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
                pitch_tolerance=22,
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
                artistry_weight=0.20,
                pitch_tolerance=20,
                rhythm_tolerance=0.35,
                allow_rubato=True,
                allow_vibrato=True,
                expect_high_energy=False
            ),
        }

    @classmethod
    def _default_profile(cls, style: MusicStyle) -> StyleProfile:
        """获取单个风格的默认配置"""
        defaults = cls._default_profiles()
        return defaults.get(style, defaults[MusicStyle.POP])

    @classmethod
    def get_all_profiles(cls) -> Dict[MusicStyle, StyleProfile]:
        """
        获取所有风格配置

        Returns:
            所有风格配置字典
        """
        if not cls._loaded:
            cls._load_all()

        return cls._cache.copy()

    @classmethod
    def validate_config(cls) -> List[str]:
        """
        验证配置有效性

        Returns:
            错误信息列表（空列表表示有效）
        """
        errors = []

        if not cls._loaded:
            cls._load_all()

        for style, profile in cls._cache.items():
            # 检查权重总和
            weight_sum = (
                profile.pitch_weight +
                profile.rhythm_weight +
                profile.breath_weight +
                profile.technique_weight +
                profile.artistry_weight
            )
            if abs(weight_sum - 1.0) > 0.01:
                errors.append(
                    f"Style {style.value}: weights sum to {weight_sum:.2f}, should be 1.0"
                )

            # 检查阈值范围
            if profile.pitch_tolerance <= 0:
                errors.append(f"Style {style.value}: pitch_tolerance must be positive")
            if profile.rhythm_tolerance <= 0:
                errors.append(f"Style {style.value}: rhythm_tolerance must be positive")

        return errors


# 便捷函数
def get_style_profile(style: MusicStyle) -> StyleProfile:
    """获取风格配置"""
    return StyleConfigLoader.load(style)


def get_all_style_profiles() -> Dict[MusicStyle, StyleProfile]:
    """获取所有风格配置"""
    return StyleConfigLoader.get_all_profiles()


def reload_style_config() -> None:
    """热重载风格配置"""
    StyleConfigLoader.reload()
