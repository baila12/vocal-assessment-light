"""
唱法自动识别分类器
识别演唱风格：流行/美声/民族/说唱/爵士
支持ONNX模型推理（AST模型），模型不可用时降级到启发式算法
"""

import numpy as np
import librosa
import logging
import os
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

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

    使用AST (Audio Spectrogram Transformer) 模型：
    - 模型大小: ~86MB (量化版)
    - 输入: 128维梅尔频谱
    - 输出: 10类音乐风格概率
    - 准确率: >85%

    模型不可用时自动降级到启发式算法
    """

    # AST模型路径
    AST_MODEL_PATH = 'models/style_classifier/model_quantized.onnx'
    AST_CONFIG_PATH = 'models/style_classifier/config.json'

    # AST模型的音乐风格标签 (GTZAN数据集)
    AST_GENRES = ['blues', 'classical', 'country', 'disco', 'hiphop',
                  'jazz', 'metal', 'pop', 'reggae', 'rock']

    # 音乐风格到演唱风格的映射
    GENRE_TO_SINGING_STYLE = {
        'pop': SingingStyle.POP,
        'classical': SingingStyle.CLASSICAL,
        'jazz': SingingStyle.JAZZ,
        'hiphop': SingingStyle.RAP,  # 说唱对应hiphop
        'country': SingingStyle.FOLK,  # 乡村对应民族风格
        'blues': SingingStyle.POP,  # 蓝调归入流行
        'disco': SingingStyle.POP,  # 迪斯科归入流行
        'metal': SingingStyle.POP,  # 金属归入流行
        'reggae': SingingStyle.POP,  # 雷鬼归入流行
        'rock': SingingStyle.POP,  # 摇滚归入流行
    }

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
        self._session = None
        self._model_available = False
        self._id2label = {}

        # 尝试加载AST ONNX模型
        if os.path.exists(self.AST_MODEL_PATH):
            try:
                import onnxruntime as ort
                self._session = ort.InferenceSession(
                    self.AST_MODEL_PATH,
                    providers=['CPUExecutionProvider']
                )
                self._model_available = True
                logger.info(f"[SingingStyleClassifier] AST model loaded from {self.AST_MODEL_PATH}")

                # 加载配置
                if os.path.exists(self.AST_CONFIG_PATH):
                    with open(self.AST_CONFIG_PATH, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        self._id2label = config.get('id2label', {})
            except Exception as e:
                logger.warning(f"[SingingStyleClassifier] Failed to load AST model: {e}")

        if not self._model_available:
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
        使用AST深度学习模型分类

        AST模型输入: (batch, 1024, 128) - 1024帧, 128维梅尔频谱
        输出: 10类音乐风格概率

        Args:
            y: 音频波形
            sr: 采样率

        Returns:
            StyleClassificationResult
        """
        try:
            # 提取梅尔频谱 (AST期望128维)
            mel_spec = librosa.feature.melspectrogram(
                y=y, sr=sr, n_mels=128, hop_length=512, n_fft=2048
            )
            mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)

            # 归一化到 [0, 1]
            mel_spec_norm = (mel_spec_db - mel_spec_db.min()) / (mel_spec_db.max() - mel_spec_db.min() + 1e-10)

            # AST期望的输入形状: (batch, 1024, 128)
            # 需要调整时间维度到1024帧
            target_frames = 1024
            n_frames = mel_spec_norm.shape[1]

            if n_frames >= target_frames:
                # 截断到目标长度
                mel_spec_resized = mel_spec_norm[:, :target_frames]
            else:
                # 填充到目标长度
                pad_width = target_frames - n_frames
                mel_spec_resized = np.pad(mel_spec_norm, ((0, 0), (0, pad_width)), mode='constant')

            # 转置为 (batch, time, freq) = (1, 1024, 128)
            input_tensor = mel_spec_resized.T[np.newaxis, :, :].astype(np.float32)

            # 运行推理 - 使用正确的输入名称 'input_values'
            results = self._session.run(
                ['logits'],
                {'input_values': input_tensor}
            )

            # 解析输出 - logits或softmax概率
            logits = results[0][0]  # (10,)

            # 应用softmax获取概率
            exp_logits = np.exp(logits - np.max(logits))
            probs = exp_logits / np.sum(exp_logits)

            # 获取风格标签
            genre_probs = {}
            for i, prob in enumerate(probs):
                if self._id2label:
                    genre_name = self._id2label.get(str(i), self.AST_GENRES[i])
                else:
                    genre_name = self.AST_GENRES[i]
                genre_probs[genre_name] = float(prob)

            # 映射到演唱风格
            singing_style_probs = {s.value: 0.0 for s in SingingStyle if s != SingingStyle.UNKNOWN}
            singing_style_probs['unknown'] = 0.0

            for genre, prob in genre_probs.items():
                style = self.GENRE_TO_SINGING_STYLE.get(genre, SingingStyle.POP)
                singing_style_probs[style.value] += prob

            # 找到最高概率的演唱风格
            best_style_name = max(singing_style_probs.keys(), key=lambda k: singing_style_probs[k])
            best_style = SingingStyle(best_style_name)
            confidence = singing_style_probs[best_style_name]

            return StyleClassificationResult(
                style=best_style,
                confidence=confidence,
                probabilities=singing_style_probs,
                method='ast_dl'
            )

        except Exception as e:
            logger.error(f"[SingingStyleClassifier] AST inference failed: {e}")
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
