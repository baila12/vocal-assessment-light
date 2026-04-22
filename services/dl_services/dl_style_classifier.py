"""
深度学习音乐风格分类器
使用Hugging Face预训练模型进行音乐风格和情绪分类
"""

import numpy as np
import librosa
import logging
import os
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# 设置HF镜像
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'


class MusicGenre(Enum):
    """音乐风格枚举"""
    POP = "pop"
    ROCK = "rock"
    JAZZ = "jazz"
    CLASSICAL = "classical"
    FOLK = "folk"
    RB_SOUL = "rb_soul"
    HIPHOP = "hiphop"
    ELECTRONIC = "electronic"
    COUNTRY = "country"
    BLUES = "blues"
    UNKNOWN = "unknown"


class MusicMood(Enum):
    """音乐情绪枚举"""
    ROMANTIC = "romantic"
    HAPPY = "happy"
    SAD = "sad"
    ENERGETIC = "energetic"
    RELAXING = "relaxing"
    SENTIMENTAL = "sentimental"
    GLAMOROUS = "glamorous"
    UPLIFTING = "uplifting"
    DARK = "dark"
    EPIC = "epic"
    UNKNOWN = "unknown"


@dataclass
class StyleClassificationResult:
    """风格分类结果"""
    genre: MusicGenre                    # 音乐风格
    genre_confidence: float              # 风格置信度
    genre_probabilities: Dict[str, float]  # 风格概率分布

    mood: MusicMood                      # 主要情绪
    mood_confidence: float               # 情绪置信度
    mood_probabilities: Dict[str, float]  # 情绪概率分布

    method: str                          # 检测方法


class DLStyleClassifier:
    """
    深度学习音乐风格分类器

    使用两个模型：
    1. GenreVim (DistilHuBERT) - 17种音乐风格分类
    2. Music Moods (Wav2Vec2) - 14种情绪分类
    """

    # GenreVim模型标签映射
    GENREVIM_LABELS = [
        'Trap', 'Rock', 'Reagge', 'R&B, Soul', 'Pop', 'Metal', 'Latin',
        'Jazz', 'House', 'Hardstyle', 'Future Bass', 'Folk', 'Dubstep',
        'Drum & Bass', 'Country', 'Classical', 'Blues'
    ]

    # GenreVim到内部枚举的映射
    GENREVIM_TO_GENRE = {
        'Pop': MusicGenre.POP,
        'Rock': MusicGenre.ROCK,
        'Jazz': MusicGenre.JAZZ,
        'Classical': MusicGenre.CLASSICAL,
        'Folk': MusicGenre.FOLK,
        'R&B, Soul': MusicGenre.RB_SOUL,
        'Trap': MusicGenre.HIPHOP,
        'House': MusicGenre.ELECTRONIC,
        'Future Bass': MusicGenre.ELECTRONIC,
        'Dubstep': MusicGenre.ELECTRONIC,
        'Drum & Bass': MusicGenre.ELECTRONIC,
        'Hardstyle': MusicGenre.ELECTRONIC,
        'Country': MusicGenre.COUNTRY,
        'Blues': MusicGenre.BLUES,
        'Metal': MusicGenre.ROCK,
        'Latin': MusicGenre.POP,
        'Reagge': MusicGenre.POP,
    }

    # Music Moods模型标签
    MOOD_LABELS = [
        'angry', 'dark', 'energetic', 'epic', 'euphoric', 'happy',
        'mysterious', 'relaxing', 'romantic', 'sad', 'scary',
        'glamorous', 'uplifting', 'sentimental'
    ]

    # 情绪标签到内部枚举的映射
    MOOD_TO_ENUM = {
        'romantic': MusicMood.ROMANTIC,
        'happy': MusicMood.HAPPY,
        'sad': MusicMood.SAD,
        'energetic': MusicMood.ENERGETIC,
        'euphoric': MusicMood.ENERGETIC,
        'relaxing': MusicMood.RELAXING,
        'sentimental': MusicMood.SENTIMENTAL,
        'glamorous': MusicMood.GLAMOROUS,
        'uplifting': MusicMood.UPLIFTING,
        'dark': MusicMood.DARK,
        'epic': MusicMood.EPIC,
        'angry': MusicMood.DARK,
        'mysterious': MusicMood.DARK,
        'scary': MusicMood.DARK,
    }

    def __init__(self):
        self._genre_model = None
        self._genre_extractor = None
        self._mood_model = None
        self._mood_extractor = None
        self._model_available = False

        # 尝试加载模型
        self._load_models()

    def _load_models(self):
        """加载预训练模型"""
        try:
            import torch
            from transformers import AutoModelForAudioClassification, AutoFeatureExtractor

            # 加载GenreVim风格分类模型
            logger.info("[DLStyleClassifier] Loading GenreVim model...")
            self._genre_model = AutoModelForAudioClassification.from_pretrained(
                'MarekCech/GenreVim-Music-Classification-DistilHuBERT'
            )
            self._genre_extractor = AutoFeatureExtractor.from_pretrained(
                'MarekCech/GenreVim-Music-Classification-DistilHuBERT'
            )

            # 加载Music Moods情绪分类模型
            logger.info("[DLStyleClassifier] Loading Music Moods model...")
            self._mood_model = AutoModelForAudioClassification.from_pretrained(
                'StanislavKo28/music_moods_classification'
            )
            self._mood_extractor = AutoFeatureExtractor.from_pretrained(
                'StanislavKo28/music_moods_classification'
            )

            self._model_available = True
            logger.info("[DLStyleClassifier] All models loaded successfully")

        except Exception as e:
            logger.warning(f"[DLStyleClassifier] Failed to load models: {e}")
            self._model_available = False

    def classify(self, audio_path: str, sr: int = 16000) -> StyleClassificationResult:
        """
        分类音乐风格和情绪

        Args:
            audio_path: 音频文件路径
            sr: 采样率

        Returns:
            StyleClassificationResult: 分类结果
        """
        # 加载音频
        try:
            y, sr = librosa.load(audio_path, sr=sr, mono=True)
        except Exception as e:
            logger.error(f"[DLStyleClassifier] Failed to load audio: {e}")
            return self._default_result()

        if self._model_available:
            return self._classify_dl(y, sr)
        else:
            return self._classify_heuristic(y, sr)

    def _classify_dl(self, y: np.ndarray, sr: int) -> StyleClassificationResult:
        """使用深度学习模型分类"""
        try:
            import torch

            # 1. 风格分类
            genre_probs = self._classify_genre(y, sr)
            best_genre_label = max(genre_probs.keys(), key=lambda k: genre_probs[k])
            best_genre = self.GENREVIM_TO_GENRE.get(best_genre_label, MusicGenre.POP)
            genre_confidence = genre_probs[best_genre_label]

            # 2. 情绪分类
            mood_probs = self._classify_mood(y, sr)
            best_mood_label = max(mood_probs.keys(), key=lambda k: mood_probs[k])
            best_mood = self.MOOD_TO_ENUM.get(best_mood_label, MusicMood.UNKNOWN)
            mood_confidence = mood_probs[best_mood_label]

            return StyleClassificationResult(
                genre=best_genre,
                genre_confidence=genre_confidence,
                genre_probabilities=genre_probs,
                mood=best_mood,
                mood_confidence=mood_confidence,
                mood_probabilities=mood_probs,
                method='dl'
            )

        except Exception as e:
            logger.error(f"[DLStyleClassifier] DL classification failed: {e}")
            return self._classify_heuristic(y, sr)

    def _classify_genre(self, y: np.ndarray, sr: int) -> Dict[str, float]:
        """风格分类"""
        import torch

        inputs = self._genre_extractor(y, sampling_rate=sr, return_tensors='pt')

        with torch.no_grad():
            logits = self._genre_model(**inputs).logits

        probs = torch.softmax(logits, dim=-1)[0]

        result = {}
        for i, label in enumerate(self.GENREVIM_LABELS):
            result[label] = float(probs[i].item())

        return result

    def _classify_mood(self, y: np.ndarray, sr: int) -> Dict[str, float]:
        """情绪分类"""
        import torch

        inputs = self._mood_extractor(y, sampling_rate=sr, return_tensors='pt')

        with torch.no_grad():
            logits = self._mood_model(**inputs).logits

        probs = torch.softmax(logits, dim=-1)[0]

        result = {}
        for i, label in enumerate(self.MOOD_LABELS):
            result[label] = float(probs[i].item())

        return result

    def _classify_heuristic(self, y: np.ndarray, sr: int) -> StyleClassificationResult:
        """启发式分类（降级方案）"""
        # 基于节奏和能量简单分类
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        tempo = float(np.atleast_1d(tempo)[0])

        rms = librosa.feature.rms(y=y)[0]
        energy = np.mean(rms)

        if tempo < 80:
            genre = MusicGenre.FOLK
            mood = MusicMood.SENTIMENTAL
        elif tempo > 140:
            genre = MusicGenre.ELECTRONIC
            mood = MusicMood.ENERGETIC
        elif energy > 0.15:
            genre = MusicGenre.ROCK
            mood = MusicMood.ENERGETIC
        else:
            genre = MusicGenre.POP
            mood = MusicMood.RELAXING

        return StyleClassificationResult(
            genre=genre,
            genre_confidence=0.5,
            genre_probabilities={genre.value: 0.5},
            mood=mood,
            mood_confidence=0.5,
            mood_probabilities={mood.value: 0.5},
            method='heuristic'
        )

    def _default_result(self) -> StyleClassificationResult:
        """返回默认结果"""
        return StyleClassificationResult(
            genre=MusicGenre.UNKNOWN,
            genre_confidence=0.0,
            genre_probabilities={},
            mood=MusicMood.UNKNOWN,
            mood_confidence=0.0,
            mood_probabilities={},
            method='error'
        )

    def get_style_description(self, genre: MusicGenre, mood: MusicMood) -> str:
        """获取风格描述"""
        genre_desc = {
            MusicGenre.POP: "流行",
            MusicGenre.ROCK: "摇滚",
            MusicGenre.JAZZ: "爵士",
            MusicGenre.CLASSICAL: "古典",
            MusicGenre.FOLK: "民谣/抒情",
            MusicGenre.RB_SOUL: "R&B/灵魂乐",
            MusicGenre.HIPHOP: "嘻哈",
            MusicGenre.ELECTRONIC: "电子",
            MusicGenre.COUNTRY: "乡村",
            MusicGenre.BLUES: "蓝调",
            MusicGenre.UNKNOWN: "未知"
        }

        mood_desc = {
            MusicMood.ROMANTIC: "浪漫",
            MusicMood.HAPPY: "欢快",
            MusicMood.SAD: "忧伤",
            MusicMood.ENERGETIC: "活力",
            MusicMood.RELAXING: "放松",
            MusicMood.SENTIMENTAL: "感性",
            MusicMood.GLAMOROUS: "华丽",
            MusicMood.UPLIFTING: "振奋",
            MusicMood.DARK: "深沉",
            MusicMood.EPIC: "史诗",
            MusicMood.UNKNOWN: ""
        }

        return f"{genre_desc.get(genre, '未知')} - {mood_desc.get(mood, '')}"
