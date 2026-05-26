"""
深度学习模型管理器
负责加载和运行深度学习模型进行音频分析
支持模型优先、规则化算法备用
"""

import os
import json
import numpy as np
import torch

# 模型配置路径
MODEL_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'models', 'model_config.json')


class ModelManager:
    """深度学习模型管理器"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.config = self._load_config()
        self.models = {}
        self._initialized = True

    def _load_config(self):
        """加载模型配置"""
        if os.path.exists(MODEL_CONFIG_PATH):
            with open(MODEL_CONFIG_PATH, 'r') as f:
                return json.load(f)
        return {}

    def load_demucs_model(self):
        """加载 Demucs 人声分离模型"""
        if 'demucs' in self.models:
            return self.models['demucs']

        try:
            from demucs import pretrained
            model = pretrained.get_model('htdemucs')
            model.eval()
            self.models['demucs'] = model
            print("[ModelManager] Demucs model loaded successfully")
            return model
        except Exception as e:
            print(f"[ModelManager] Failed to load Demucs: {e}")
            return None

    def load_emotion_model(self):
        """加载情绪识别模型"""
        if 'emotion' in self.models:
            return self.models['emotion']

        emotion_config = self.config.get('emotion', {})
        model_path = emotion_config.get('path', 'models/emotion/wav2vec2.ckpt')
        model_dir = os.path.dirname(model_path)

        # 方案1: 使用本地 wav2vec2 checkpoint + model.ckpt (完整模型)
        if os.path.exists(model_path):
            try:
                import torch
                from transformers import Wav2Vec2Model, Wav2Vec2Config

                # 使用默认配置 (离线)
                config = Wav2Vec2Config()

                # 创建模型
                wav2vec2 = Wav2Vec2Model(config)

                # 加载 wav2vec2 checkpoint
                checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)

                # 处理 state_dict 键名
                new_state_dict = {}
                for k, v in checkpoint.items():
                    # 移除 'model.' 前缀
                    new_key = k.replace('model.', '')
                    new_state_dict[new_key] = v

                # 加载权重
                wav2vec2.load_state_dict(new_state_dict, strict=False)
                wav2vec2.eval()

                # 创建分类头 (768 hidden dim -> 4 emotions)
                classifier = torch.nn.Linear(768, 4)

                # 尝试加载分类器权重 (model.ckpt)
                classifier_paths = [
                    os.path.join(model_dir, 'model.ckpt'),
                ]

                for classifier_path in classifier_paths:
                    if os.path.exists(classifier_path):
                        classifier_ckpt = torch.load(classifier_path, map_location='cpu', weights_only=False)
                        # 加载分类器权重: key='0.w.weight' -> classifier.weight
                        if '0.w.weight' in classifier_ckpt:
                            classifier.weight.data = classifier_ckpt['0.w.weight']
                            print(f"[ModelManager] Classifier weights loaded from {classifier_path}")
                            break
                else:
                    print(f"[ModelManager] Warning: model.ckpt not found, using random weights")

                classifier.eval()

                self.models['emotion'] = {
                    'wav2vec2': wav2vec2,
                    'classifier': classifier,
                    'type': 'local_wav2vec2',
                    'labels': ['neutral', 'angry', 'happy', 'sad']
                }
                print(f"[ModelManager] Local Wav2Vec2 model loaded from {model_path}")
                return self.models['emotion']

            except Exception as e:
                print(f"[ModelManager] Failed to load local Wav2Vec2: {e}")

        # 方案2: 使用 SpeechBrain 预训练模型 (需要网络)
        try:
            from speechbrain.pretrained import EncoderClassifier

            classifier = EncoderClassifier.from_hparams(
                source='speechbrain/emotion-recognition-wav2vec2-IEMOCAP',
                savedir='models/emotion'
            )

            self.models['emotion'] = {
                'classifier': classifier,
                'type': 'speechbrain',
                'labels': ['neutral', 'angry', 'happy', 'sad']
            }
            print("[ModelManager] SpeechBrain emotion model loaded")
            return self.models['emotion']

        except Exception as e:
            print(f"[ModelManager] SpeechBrain model unavailable: {str(e)[:50]}...")

        return None

    def separate_vocals(self, audio_data, sample_rate):
        """
        使用 Demucs 分离人声

        Args:
            audio_data: 音频数据 (numpy array)
            sample_rate: 采样率

        Returns:
            vocals: 人声部分
            accompaniment: 伴奏部分
        """
        model = self.load_demucs_model()

        if model is None:
            # 备用方案：简单的高通滤波
            print("[ModelManager] Using fallback vocal separation")
            from scipy import signal
            b, a = signal.butter(4, 200 / (sample_rate / 2), 'high')
            vocals = signal.filtfilt(b, a, audio_data)
            accompaniment = audio_data - vocals
            return vocals, accompaniment

        try:
            import torch
            from demucs.apply import apply_model

            # 转换为模型输入格式
            audio_tensor = torch.from_numpy(audio_data).float()
            if audio_tensor.dim() == 1:
                audio_tensor = audio_tensor.unsqueeze(0)

            # 应用模型
            with torch.no_grad():
                sources = apply_model(model, audio_tensor, progress=False)

            # Demucs 输出: [batch, sources, channels, time]
            # sources: drums, bass, other, vocals
            vocals = sources[0, 3, 0, :].numpy()  # vocals
            accompaniment = sources[0, :3, 0, :].sum(dim=0).numpy()  # drums + bass + other

            return vocals, accompaniment

        except Exception as e:
            print(f"[ModelManager] Demucs inference failed: {e}")
            # 备用方案
            return audio_data, np.zeros_like(audio_data)

    def analyze_emotion(self, audio_data, sample_rate):
        """
        使用深度学习模型分析情绪

        Args:
            audio_data: 音频数据
            sample_rate: 采样率

        Returns:
            dict: 情绪分析结果
        """
        model_info = self.load_emotion_model()

        if model_info is None:
            # 备用方案：启发式情绪分析
            return self._heuristic_emotion(audio_data, sample_rate)

        try:
            # 使用 wav2vec2 模型
            return self._wav2vec2_emotion(audio_data, sample_rate, model_info)
        except Exception as e:
            print(f"[ModelManager] Emotion model inference failed: {e}")

        # 备用方案
        return self._heuristic_emotion(audio_data, sample_rate)

    def _wav2vec2_emotion(self, audio_data, sample_rate, model_info):
        """使用 Wav2Vec2 进行情绪分析"""
        # 重采样到 16kHz (wav2vec2 要求)
        import librosa
        target_sr = 16000
        if sample_rate != target_sr:
            audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=target_sr)

        model_type = model_info.get('type')

        if model_type == 'speechbrain':
            return self._speechbrain_emotion(audio_data, model_info)
        elif model_type == 'transformers':
            return self._transformers_emotion(audio_data, model_info)
        elif model_type == 'local_wav2vec2':
            return self._local_wav2vec2_emotion(audio_data, model_info)
        elif model_type == 'checkpoint_only':
            # checkpoint 已加载但需要完整模型架构，使用启发式方法
            return self._heuristic_emotion(audio_data, target_sr)

        # 备用方案
        return self._heuristic_emotion(audio_data, target_sr)

    def _local_wav2vec2_emotion(self, audio_data, model_info):
        """使用本地 Wav2Vec2 模型进行情绪分析"""
        try:
            import torch
            import numpy as np

            wav2vec2 = model_info['wav2vec2']
            classifier = model_info['classifier']
            labels = model_info['labels']

            # 转换为 tensor
            audio_tensor = torch.from_numpy(audio_data).float()
            if audio_tensor.dim() == 1:
                audio_tensor = audio_tensor.unsqueeze(0)

            # Wav2Vec2 特征提取
            with torch.no_grad():
                # 归一化
                audio_tensor = (audio_tensor - audio_tensor.mean()) / (audio_tensor.std() + 1e-8)

                # 提取特征
                outputs = wav2vec2(audio_tensor)
                hidden_states = outputs.last_hidden_state  # [batch, seq_len, 768]

                # 全局平均池化
                pooled = hidden_states.mean(dim=1)  # [batch, 768]

                # 分类
                logits = classifier(pooled)
                scores = torch.softmax(logits, dim=-1).squeeze().tolist()
                predicted_idx = torch.argmax(logits, dim=-1).item()

            # 构建情绪字典
            emotions = {}
            for i, label in enumerate(labels):
                emotions[label] = scores[i] if i < len(scores) else 0.0

            dominant = labels[predicted_idx] if predicted_idx < len(labels) else 'neutral'
            confidence = scores[predicted_idx] if predicted_idx < len(scores) else 0.0

            return {
                'emotions': emotions,
                'dominant': dominant,
                'confidence': confidence,
                'method': 'local_wav2vec2'
            }
        except Exception as e:
            print(f"[ModelManager] Local Wav2Vec2 inference error: {e}")
            return self._heuristic_emotion(audio_data, 16000)

    def _speechbrain_emotion(self, audio_data, model_info):
        """使用 SpeechBrain 模型进行情绪分析"""
        try:
            import torch

            classifier = model_info['classifier']
            labels = model_info['labels']

            # SpeechBrain 推理
            with torch.no_grad():
                # 转换为 tensor
                audio_tensor = torch.from_numpy(audio_data).float()
                if audio_tensor.dim() == 1:
                    audio_tensor = audio_tensor.unsqueeze(0)

                # 分类
                prediction = classifier.classify_batch(audio_tensor)
                predicted_idx = prediction[0].item() if hasattr(prediction[0], 'item') else int(prediction[0])
                scores = torch.softmax(prediction[1], dim=-1).squeeze().tolist()

            # 构建情绪字典
            emotions = {}
            emotion_map = {'neu': 'neutral', 'ang': 'angry', 'hap': 'happy', 'sad': 'sad'}
            for i, label in enumerate(labels):
                key = emotion_map.get(label, label)
                emotions[key] = scores[i] if i < len(scores) else 0.0

            dominant = emotion_map.get(labels[predicted_idx], labels[predicted_idx])
            confidence = scores[predicted_idx] if predicted_idx < len(scores) else 0.0

            return {
                'emotions': emotions,
                'dominant': dominant,
                'confidence': confidence,
                'method': 'speechbrain_wav2vec2'
            }
        except Exception as e:
            print(f"[ModelManager] SpeechBrain inference error: {e}")
            return self._heuristic_emotion(audio_data, 16000)

    def _transformers_emotion(self, audio_data, model_info):
        """使用 HuggingFace Transformers 模型进行情绪分析"""
        try:
            import torch

            model = model_info['model']
            processor = model_info['processor']
            labels = model_info['labels']

            # 预处理
            inputs = processor(audio_data, sampling_rate=16000, return_tensors="pt", padding=True)

            # 推理
            with torch.no_grad():
                logits = model(**inputs).logits
                scores = torch.softmax(logits, dim=-1).squeeze().tolist()
                predicted_idx = torch.argmax(logits, dim=-1).item()

            # 构建情绪字典
            emotions = {}
            emotion_map = {'neutral': 'neutral', 'angry': 'angry', 'happy': 'happy', 'sad': 'sad'}
            for i, label in enumerate(labels):
                key = emotion_map.get(label, label)
                emotions[key] = scores[i] if i < len(scores) else 0.0

            dominant = emotion_map.get(labels[predicted_idx], labels[predicted_idx])
            confidence = scores[predicted_idx] if predicted_idx < len(scores) else 0.0

            return {
                'emotions': emotions,
                'dominant': dominant,
                'confidence': confidence,
                'method': 'transformers_wav2vec2'
            }
        except Exception as e:
            print(f"[ModelManager] Transformers inference error: {e}")
            return self._heuristic_emotion(audio_data, 16000)

    def _heuristic_emotion(self, audio_data, sample_rate):
        """启发式情绪分析（备用方案）"""
        import librosa

        rms_feature = librosa.feature.rms(y=audio_data)[0]
        energy_mean = np.mean(rms_feature)
        energy_std = np.std(rms_feature)

        spectral_centroids = librosa.feature.spectral_centroid(y=audio_data, sr=sample_rate)[0]
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

        dominant_emotion = max(emotions, key=emotions.get)
        emotion_confidence = emotions[dominant_emotion]

        return {
            'emotions': emotions,
            'dominant': dominant_emotion,
            'confidence': emotion_confidence,
            'method': 'heuristic'
        }


# 全局模型管理器实例
model_manager = ModelManager()


def get_model_manager():
    """获取模型管理器实例"""
    return model_manager


def analyze_with_models(audio_data, sample_rate, use_vocal_separation=False):
    """
    使用深度学习模型进行完整分析

    Args:
        audio_data: 音频数据
        sample_rate: 采样率
        use_vocal_separation: 是否使用人声分离

    Returns:
        dict: 分析结果
    """
    import librosa

    manager = get_model_manager()

    # 可选：人声分离
    if use_vocal_separation:
        vocals, accompaniment = manager.separate_vocals(audio_data, sample_rate)
        analysis_audio = vocals
    else:
        analysis_audio = audio_data

    # 情绪分析（优先使用模型）
    emotion_result = manager.analyze_emotion(analysis_audio, sample_rate)

    return {
        'emotion': emotion_result,
        'used_vocal_separation': use_vocal_separation
    }


if __name__ == "__main__":
    # 测试模型加载
    print("Testing Model Manager...")

    manager = get_model_manager()

    # 测试 Demucs
    print("\n[1] Testing Demucs...")
    demucs = manager.load_demucs_model()
    if demucs:
        print("    Demucs model loaded successfully!")
    else:
        print("    Demucs model not available")

    # 测试情绪模型
    print("\n[2] Testing Emotion Model...")
    emotion_model = manager.load_emotion_model()
    if emotion_model:
        print("    Emotion model loaded successfully!")
    else:
        print("    Emotion model not available")

    print("\nModel Manager test complete!")
