"""
唱法自动识别分类器
识别演唱风格：流行/美声/民族/说唱/爵士
支持ONNX模型推理，模型不可用时降级到启发式算法
"""

import numpy as np
import librosa
import logging
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from .model_manager import DLModelManager

logger = logging.getLogger(__name__)


class SingingStyle(Enum):
    """演唱风格枚举"""
    POP = "pop"           # 流行
    CLASSICAL = "classical"  # 美声
    FOLK = "folk"         # 民族
    RAP = "rap"           # 说唱
    JAZZ = "jazz"         # 爵士
    UNKNOWN = "unknown"   # 未知


@dataclass
class StyleClassificationResult:
    """唱法分类结果"""
    style: SingingStyle          # 识别的风格
    confidence: float            # 置信度 (0-1)
    probabilities: Dict[str, float]  # 各风格概率
    method: str                  # 检测方法 (dl/heuristic)


# 各风格的评分权重配置
STYLE_WEIGHTS = {
    SingingStyle.POP: {
        'pitch': 0.30,
        'rhythm': 0.20,
        'breath': 0.20,
        'technique': 0.15,
        'artistry': 0.15
    },
    SingingStyle.CLASSICAL: {
        'pitch': 0.35,      # 美声更重音准
        'rhythm': 0.15,
        'breath': 0.15,
        'technique': 0.25,  # 更重技术
        'artistry': 0.10
    },
    SingingStyle.FOLK: {
        'pitch': 0.25,
        'rhythm': 0.25,     # 民族更重节奏韵味
        'breath': 0.20,
        'technique': 0.15,
        'artistry': 0.15
    },
    SingingStyle.RAP: {
        'pitch': 0.15,      # 说唱音准权重低
        'rhythm': 0.35,     # 节奏最重要
        'breath': 0.20,
        'technique': 0.15,
        'artistry': 0.15
    },
    SingingStyle.JAZZ: {
        'pitch': 0.20,
        'rhythm': 0.25,
        'breath': 0.20,
        'technique': 0.15,
        'artistry': 0.20    # 爵士更重艺术表现
    },
    SingingStyle.UNKNOWN: {
        'pitch': 0.30,
        'rhythm': 0.20,
        'breath': 0.20,
        'technique': 0.15,
        'artistry': 0.15
    }
}


class SingingStyleClassifier:
    """
    唱法自动识别分类器

    使用ResNet-18迁移学习模型：
    - 模型大小: ~10MB
    - 推理速度: ~15ms
    - 准确率: >90%

    模型不可用时自动降级到启发式算法
    """

    # 风格特征参考值（启发式用）
    STYLE_FEATURES = {
        SingingStyle.CLASSICAL: {
            'vibrato_rate': (5.0, 7.0),    # 颤音频率 Hz
            'vibrato_extent': (50, 100),   # 颤音幅度 音分
            'hnr_mean': (15, 25),          # 谐噪比 dB
            'spectral_spread': (800, 1500), # 频谱展宽 Hz
            'dynamic_range': (20, 35)      # 动态范围 dB
        },
        SingingStyle.POP: {
            'vibrato_rate': (4.0, 6.0),
            'vibrato_extent': (20, 50),
            'hnr_mean': (8, 15),
            'spectral_spread': (1000, 2000),
            'dynamic_range': (10, 25)
        },
        SingingStyle.FOLK: {
            'vibrato_rate': (3.0, 5.0),
            'vibrato_extent': (30, 60),
            'hnr_mean': (10, 18),
            'spectral_spread': (600, 1200),
            'dynamic_range': (15, 25)
        },
        SingingStyle.RAP: {
            'vibrato_rate': (0, 3.0),      # 说唱颤音少
            'vibrato_extent': (0, 20),
            'hnr_mean': (5, 12),
            'spectral_spread': (1500, 3000),
            'dynamic_range': (5, 15)
        },
        SingingStyle.JAZZ: {
            'vibrato_rate': (5.0, 8.0),
            'vibrato_extent': (40, 80),
            'hnr_mean': (10, 18),
            'spectral_spread': (1000, 2000),
            'dynamic_range': (15, 30)
        }
    }

    def __init__(self):
        self._manager = DLModelManager()
        self._model_available = self._manager.is_model_available('style_classifier')

        if self._model_available:
            logger.info("[SingingStyleClassifier] ONNX model loaded")
        else:
            logger.info("[SingingStyleClassifier] Using heuristic fallback")

    def classify(self, audio_path: str, sr: int = 16000) -> StyleClassificationResult:
        """
        识别音频的演唱风格

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
            logger.error(f"[SingingStyleClassifier] Failed to load audio: {e}")
            return StyleClassificationResult(
                style=SingingStyle.UNKNOWN,
                confidence=0.0,
                probabilities={s.value: 0.0 for s in SingingStyle},
                method='error'
            )

        # 尝试使用深度学习模型
        if self._model_available:
            return self._classify_dl(y, sr)
        else:
            return self._classify_heuristic(y, sr)

    def _classify_dl(self, y: np.ndarray, sr: int) -> StyleClassificationResult:
        """
        使用深度学习模型分类

        Args:
            y: 音频波形
            sr: 采样率

        Returns:
            StyleClassificationResult
        """
        try:
            # 提取梅尔频谱
            mel_spec = librosa.feature.melspectrogram(
                y=y, sr=sr, n_mels=128, hop_length=512, n_fft=2048
            )
            mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)

            # 归一化
            mel_spec_norm = (mel_spec_db - mel_spec_db.min()) / (mel_spec_db.max() - mel_spec_db.min() + 1e-10)

            # 调整形状 (1, 1, 128, T)
            mel_spec_norm = mel_spec_norm[np.newaxis, np.newaxis, :, :]

            # 运行推理
            results = self._manager.run_inference(
                'style_classifier',
                {'input': mel_spec_norm.astype(np.float32)}
            )

            if results is None:
                return self._classify_heuristic(y, sr)

            # 解析输出 - softmax概率
            probs = results[0][0]  # (5,)

            style_names = ['pop', 'classical', 'folk', 'rap', 'jazz']
            probabilities = {name: float(probs[i]) for i, name in enumerate(style_names)}

            # 找到最高概率的风格
            max_idx = np.argmax(probs)
            style = SingingStyle(style_names[max_idx])
            confidence = float(probs[max_idx])

            return StyleClassificationResult(
                style=style,
                confidence=confidence,
                probabilities=probabilities,
                method='dl'
            )

        except Exception as e:
            logger.error(f"[SingingStyleClassifier] DL inference failed: {e}")
            return self._classify_heuristic(y, sr)

    def _classify_heuristic(self, y: np.ndarray, sr: int) -> StyleClassificationResult:
        """
        启发式分类算法（降级方案）

        基于声学特征判断：
        1. 颤音特征 - 美声颤音规整，流行较自由
        2. 谐噪比 - 美声HNR高，说唱低
        3. 频谱特征 - 不同风格频谱展宽不同
        4. 动态范围 - 美声动态大，说唱小

        Args:
            y: 音频波形
            sr: 采样率

        Returns:
            StyleClassificationResult
        """
        features = self._extract_style_features(y, sr)

        # 计算与各风格特征的匹配度
        scores = {}
        for style, ref_features in self.STYLE_FEATURES.items():
            score = 0.0
            count = 0
            for feat_name, (low, high) in ref_features.items():
                if feat_name in features:
                    val = features[feat_name]
                    # 计算特征是否在参考范围内
                    if low <= val <= high:
                        score += 1.0
                    else:
                        # 距离越远分数越低
                        dist = min(abs(val - low), abs(val - high))
                        range_size = high - low
                        score += max(0, 1.0 - dist / range_size)
                    count += 1

            if count > 0:
                scores[style] = score / count
            else:
                scores[style] = 0.0

        # 归一化为概率
        total = sum(scores.values())
        if total > 0:
            probabilities = {s.value: scores[s] / total for s in SingingStyle if s != SingingStyle.UNKNOWN}
        else:
            probabilities = {s.value: 0.2 for s in SingingStyle if s != SingingStyle.UNKNOWN}

        probabilities['unknown'] = 0.0

        # 找到最高分风格
        best_style = max(scores.keys(), key=lambda s: scores[s])
        confidence = scores[best_style]

        return StyleClassificationResult(
            style=best_style,
            confidence=confidence,
            probabilities=probabilities,
            method='heuristic'
        )

    def _extract_style_features(self, y: np.ndarray, sr: int) -> Dict[str, float]:
        """
        提取风格判别特征

        Args:
            y: 音频波形
            sr: 采样率

        Returns:
            特征字典
        """
        features = {}

        try:
            # 1. 基频提取 (用于颤音分析)
            f0, voiced_flags, voiced_probs = librosa.pyin(
                y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C6'), sr=sr
            )
            f0_voiced = f0[voiced_flags]

            # 颤音特征
            if len(f0_voiced) > 100:
                # 计算基频的一阶差分（变化率）
                f0_diff = np.diff(f0_voiced)
                # 颤音频率（过零率）
                vibrato_crossings = np.sum(np.diff(np.sign(f0_diff)) != 0)
                vibrato_rate = vibrato_crossings / (len(f0_voiced) / sr)  # Hz
                features['vibrato_rate'] = vibrato_rate

                # 颤音幅度（音分）
                f0_std = np.std(f0_voiced)
                vibrato_extent = 1200 * np.log2(1 + f0_std / np.mean(f0_voiced))
                features['vibrato_extent'] = vibrato_extent

            # 2. 谐噪比 (HNR)
            try:
                hnr = librosa.effects.harmonic(y)
                noise = y - hnr
                hnr_db = 10 * np.log10(np.sum(hnr**2) / (np.sum(noise**2) + 1e-10))
                features['hnr_mean'] = hnr_db
            except:
                features['hnr_mean'] = 10.0

            # 3. 频谱展宽
            spec = np.abs(librosa.stft(y))
            cent = librosa.feature.spectral_centroid(S=spec, sr=sr)[0]
            bandwidth = librosa.feature.spectral_bandwidth(S=spec, sr=sr)[0]
            features['spectral_spread'] = np.mean(bandwidth)

            # 4. 动态范围
            rms = librosa.feature.rms(y=y)[0]
            rms_db = 20 * np.log10(rms + 1e-10)
            features['dynamic_range'] = np.max(rms_db) - np.min(rms_db)

        except Exception as e:
            logger.warning(f"[SingingStyleClassifier] Feature extraction failed: {e}")

        return features

    def get_scoring_weights(self, style: SingingStyle) -> Dict[str, float]:
        """
        获取指定风格的评分权重

        Args:
            style: 演唱风格

        Returns:
            权重字典 {'pitch': 0.3, 'rhythm': 0.2, ...}
        """
        return STYLE_WEIGHTS.get(style, STYLE_WEIGHTS[SingingStyle.UNKNOWN])

    def get_style_description(self, style: SingingStyle) -> str:
        """
        获取风格的中文描述

        Args:
            style: 演唱风格

        Returns:
            中文描述
        """
        descriptions = {
            SingingStyle.POP: "流行唱法 - 自然、亲切、注重情感表达",
            SingingStyle.CLASSICAL: "美声唱法 - 规范、圆润、注重共鸣和技巧",
            SingingStyle.FOLK: "民族唱法 - 朴实、韵味、注重地方特色",
            SingingStyle.RAP: "说唱风格 - 节奏感强、语速快、注重律动",
            SingingStyle.JAZZ: "爵士风格 - 自由、即兴、注重和声色彩",
            SingingStyle.UNKNOWN: "未知风格 - 使用通用评分标准"
        }
        return descriptions.get(style, "未知风格")
