"""
情绪识别分析器

支持SpeechBrain和Transformers模型的情绪识别
"""
import threading
from pathlib import Path
from typing import Dict, Any, Optional, Protocol
import numpy as np
import librosa
import torch
import logging

logger = logging.getLogger(__name__)

# 情绪标签
EMOTION_LABELS = ['neu', 'ang', 'hap', 'sad']
EMOTION_MODEL_PATH = str(Path(__file__).parent.parent.parent / "models" / "emotion")


class EmotionResultProtocol(Protocol):
    """情绪识别结果协议"""
    dominant: str
    confidence: float
    scores: Dict[str, float]


class EmotionAnalyzer:
    """
    情绪识别分析器

    支持:
    - SpeechBrain 预训练模型
    - HuggingFace Transformers 模型
    - 启发式后备方法
    """

    def __init__(self):
        self._classifier: Optional[Dict[str, Any]] = None
        self._loaded = False
        self._lock = threading.Lock()

    def load_model(self) -> bool:
        """
        加载情绪识别模型

        Returns:
            是否加载成功
        """
        if self._loaded:
            return True

        with self._lock:
            if self._loaded:
                return True

            # 尝试SpeechBrain模型
            if self._try_load_speechbrain():
                self._loaded = True
                return True

            # 尝试HuggingFace模型
            if self._try_load_transformers():
                self._loaded = True
                return True

            logger.warning("情绪模型加载失败，将使用启发式方法")
            return False

    def _try_load_speechbrain(self) -> bool:
        """尝试加载SpeechBrain模型"""
        try:
            from speechbrain.pretrained.interfaces import EncoderClassifier

            classifier = EncoderClassifier.from_hparams(
                source="speechbrain/emotion-recognition-wav2vec2-IEMOCAP",
                savedir="pretrained_models/emotion"
            )

            self._classifier = {
                'type': 'speechbrain',
                'classifier': classifier,
                'labels': EMOTION_LABELS
            }
            logger.info("情绪模型加载完成（SpeechBrain）")
            return True

        except Exception as e:
            logger.warning(f"SpeechBrain模型加载失败: {e}")
            return False

    def _try_load_transformers(self) -> bool:
        """尝试加载HuggingFace Transformers模型"""
        try:
            from transformers import AutoModelForAudioClassification, AutoFeatureExtractor

            model_name = "ehcalabres/wav2vec2-lg-xlsr-en-speech-emotion-recognition"
            self._classifier = {
                'type': 'transformers',
                'model': AutoModelForAudioClassification.from_pretrained(model_name),
                'feature_extractor': AutoFeatureExtractor.from_pretrained(model_name)
            }
            logger.info("情绪模型加载完成（HuggingFace）")
            return True

        except Exception as e:
            logger.warning(f"Transformers模型加载失败: {e}")
            return False

    def analyze(self, audio: np.ndarray, sample_rate: int) -> Dict[str, Any]:
        """
        分析音频情绪

        Args:
            audio: 音频数据
            sample_rate: 采样率

        Returns:
            情绪分析结果
        """
        if self._classifier is None:
            self.load_model()

        if self._classifier is not None:
            try:
                return self._analyze_with_model(audio, sample_rate)
            except Exception as e:
                logger.error(f"模型推理失败: {e}")

        return self._heuristic_analysis(audio, sample_rate)

    def _analyze_with_model(self, audio: np.ndarray, sample_rate: int) -> Dict[str, Any]:
        """使用模型进行情绪分析"""
        model_type = self._classifier.get('type', 'transformers')
        target_sr = 16000

        # 重采样
        if sample_rate != target_sr:
            audio = librosa.resample(audio, orig_sr=sample_rate, target_sr=target_sr)

        # 确保长度足够
        min_length = target_sr
        if len(audio) < min_length:
            audio = np.pad(audio, (0, min_length - len(audio)))

        if model_type == 'speechbrain':
            return self._analyze_speechbrain(audio)
        else:
            return self._analyze_transformers(audio, target_sr)

    def _analyze_speechbrain(self, audio: np.ndarray) -> Dict[str, Any]:
        """SpeechBrain模型分析"""
        sb_classifier = self._classifier.get('classifier')
        out_prob, score, index, text_lab = sb_classifier.classify_batch(audio)

        labels = self._classifier.get('labels', EMOTION_LABELS)
        probs = out_prob.squeeze().cpu().numpy() if hasattr(out_prob, 'squeeze') else out_prob[0]

        emotion_scores = {}
        for i, label in enumerate(labels):
            emotion_scores[label] = float(probs[i]) if i < len(probs) else 0.0

        label_map = {'neu': 'neutral', 'ang': 'angry', 'hap': 'happy', 'sad': 'sad'}
        mapped_scores = {label_map.get(k, k): v for k, v in emotion_scores.items()}

        predicted_label = text_lab[0] if isinstance(text_lab, (list, tuple)) else str(text_lab)
        dominant = label_map.get(predicted_label, 'neutral')
        confidence = float(score[0]) if isinstance(score, (list, tuple, np.ndarray)) else float(score)

        return {
            'dominant': dominant,
            'confidence': confidence,
            'scores': mapped_scores
        }

    def _analyze_transformers(self, audio: np.ndarray, sample_rate: int) -> Dict[str, Any]:
        """Transformers模型分析"""
        model = self._classifier['model']
        feature_extractor = self._classifier['feature_extractor']

        inputs = feature_extractor(
            audio,
            sampling_rate=sample_rate,
            return_tensors="pt",
            padding=True
        )

        with torch.no_grad():
            outputs = model(**inputs)
            logits = outputs.logits

        predicted_id = torch.argmax(logits, dim=-1).item()
        probs = torch.softmax(logits, dim=-1).squeeze().tolist()

        emotion_labels = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
        predicted_id = max(0, min(predicted_id, len(emotion_labels) - 1))

        emotion_scores = {}
        for i, label in enumerate(emotion_labels):
            if isinstance(probs, list) and i < len(probs):
                emotion_scores[label] = float(probs[i])
            else:
                emotion_scores[label] = 0.0

        dominant = emotion_labels[predicted_id]
        confidence = emotion_scores.get(dominant, 0.5)

        mapped_scores = {
            'neutral': emotion_scores.get('neutral', 0.0),
            'angry': emotion_scores.get('angry', 0.0),
            'happy': emotion_scores.get('happy', 0.0),
            'sad': emotion_scores.get('sad', 0.0)
        }

        return {
            'dominant': dominant if dominant in ['neutral', 'angry', 'happy', 'sad'] else 'neutral',
            'confidence': confidence,
            'scores': mapped_scores
        }

    def _heuristic_analysis(self, audio: np.ndarray, sample_rate: int) -> Dict[str, Any]:
        """启发式情绪分析（后备方案）"""
        rms = librosa.feature.rms(y=audio)[0]
        energy_mean = np.mean(rms)
        energy_std = np.std(rms)

        spectral_centroids = librosa.feature.spectral_centroid(y=audio, sr=sample_rate)[0]
        brightness = np.mean(spectral_centroids)

        energy_score = min(1.0, energy_mean / 0.1)
        brightness_score = min(1.0, brightness / 3000)
        variation_score = min(1.0, energy_std / 0.05)

        emotions = {
            'happy': energy_score * 0.4 + brightness_score * 0.4 + variation_score * 0.2,
            'sad': (1 - energy_score) * 0.5 + (1 - brightness_score) * 0.3 + (1 - variation_score) * 0.2,
            'angry': energy_score * 0.5 + variation_score * 0.5,
            'neutral': 0.3 + (1 - variation_score) * 0.4,
            'surprised': variation_score * 0.6 + energy_score * 0.4
        }

        dominant = max(emotions, key=emotions.get)
        return {
            'dominant': dominant,
            'confidence': emotions[dominant],
            'scores': emotions
        }

    @property
    def is_loaded(self) -> bool:
        return self._loaded


# 全局实例
_emotion_analyzer: Optional[EmotionAnalyzer] = None
_analyzer_lock = threading.Lock()


def get_emotion_analyzer() -> EmotionAnalyzer:
    """获取全局情绪分析器实例（单例）"""
    global _emotion_analyzer
    if _emotion_analyzer is None:
        with _analyzer_lock:
            if _emotion_analyzer is None:
                _emotion_analyzer = EmotionAnalyzer()
    return _emotion_analyzer
