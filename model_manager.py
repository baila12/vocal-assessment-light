"""
Deep learning model manager.
Manages Demucs vocal separation. v5.12: Wav2Vec2 emotion model removed.
"""
import os
import json
import numpy as np
import torch

MODEL_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'models', 'model_config.json')


class ModelManager:
    """DL model manager (singleton)"""

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
        if os.path.exists(MODEL_CONFIG_PATH):
            with open(MODEL_CONFIG_PATH, 'r') as f:
                return json.load(f)
        return {}

    def load_demucs_model(self):
        """Load Demucs vocal separation model."""
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

    def separate_vocals(self, audio_data, sample_rate):
        """Separate vocals using Demucs."""
        model = self.load_demucs_model()
        if model is None:
            from scipy import signal
            b, a = signal.butter(4, 200 / (sample_rate / 2), 'high')
            vocals = signal.filtfilt(b, a, audio_data)
            accompaniment = audio_data - vocals
            return vocals, accompaniment
        try:
            from demucs.apply import apply_model
            audio_tensor = torch.from_numpy(audio_data).float()
            if audio_tensor.dim() == 1:
                audio_tensor = audio_tensor.unsqueeze(0)
            with torch.no_grad():
                sources = apply_model(model, audio_tensor, progress=False)
            vocals = sources[0, 3, 0, :].numpy()
            accompaniment = sources[0, :3, 0, :].sum(dim=0).numpy()
            return vocals, accompaniment
        except Exception as e:
            print(f"[ModelManager] Demucs inference failed: {e}")
            return audio_data, np.zeros_like(audio_data)

    def analyze_emotion(self, audio_data, sample_rate):
        """
        v5.12: Heuristic emotion analysis only.
        Wav2Vec2 model removed (IEMOCAP English speech -> Chinese singing = 3x domain mismatch).
        """
        return self._heuristic_emotion(audio_data, sample_rate)

    def _heuristic_emotion(self, audio_data, sample_rate):
        """Heuristic emotion analysis based on acoustic features."""
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
        dominant = max(emotions, key=emotions.get)
        return {
            'emotions': emotions,
            'dominant': dominant,
            'confidence': emotions[dominant],
            'method': 'heuristic'
        }


model_manager = ModelManager()


def get_model_manager():
    return model_manager


def analyze_with_models(audio_data, sample_rate, use_vocal_separation=False):
    """Complete analysis using DL models."""
    manager = get_model_manager()
    if use_vocal_separation:
        vocals, _ = manager.separate_vocals(audio_data, sample_rate)
        analysis_audio = vocals
    else:
        analysis_audio = audio_data
    emotion_result = manager.analyze_emotion(analysis_audio, sample_rate)
    return {'emotion': emotion_result, 'used_vocal_separation': use_vocal_separation}


if __name__ == "__main__":
    print("Testing Model Manager...")
    manager = get_model_manager()
    print("\n[1] Testing Demucs...")
    demucs = manager.load_demucs_model()
    if demucs:
        print("    Demucs model loaded successfully!")
    else:
        print("    Demucs model not available")
    print("\n[v5.12] Wav2Vec2 emotion model removed. Using heuristic analysis.")
    print("Model Manager test complete!")
