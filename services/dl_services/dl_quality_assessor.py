"""
深度学习质量评估服务 v2.1
使用预训练模型进行歌声质量评估

模型：
1. SingMOS - 歌声MOS预测（专业歌声评估）
2. Wav2Vec2-MOS - 语音质量评估

v2.0 改进：
- 集成 MOSModelManager 支持模型热切换和降级
- 健康检查机制
- 失败重试和优雅降级

v2.1 修复：
- 兼容 torchaudio 2.x (移除已废弃的 set_audio_backend API)
"""

import os
import sys

# 设置HF镜像 (必须在导入 transformers 之前)
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

# ============================================
# 兼容性补丁: torchaudio 2.x 移除了 set_audio_backend 和 sox_effects
# v5.12: 仅在 sox_effects 不可用时应用补丁，避免覆盖已有实现（如Demucs依赖）
# ============================================
def _apply_torchaudio_compat_patch():
    """仅在 sox_effects 不可用时应用 torchaudio 兼容性补丁"""
    import torchaudio

    # 检查是否已有 sox_effects（可能是其他库注册的）
    if hasattr(torchaudio, 'sox_effects'):
        return  # 已存在，不覆盖

    # 尝试正常导入
    try:
        from torchaudio import sox_effects  # noqa: F401
        return  # 导入成功，不需要补丁
    except ImportError:
        pass  # 需要补丁

    # 仅在必要时应用补丁
    import types
    sox_effects_module = types.ModuleType('torchaudio.sox_effects')

    def apply_effects_tensor(wav, sample_rate, effects, channels_first=True):
        """兼容函数：直接返回原始音频，不应用效果"""
        return wav, sample_rate

    def apply_effects_file(file_path, effects, normalize=True, channels_first=True, format=None):
        """兼容函数：使用 soundfile 加载音频"""
        import soundfile as sf
        wav, sr = sf.read(file_path, dtype='float32')
        if len(wav.shape) == 1:
            wav = wav.reshape(1, -1)
        return wav, sr

    sox_effects_module.apply_effects_tensor = apply_effects_tensor
    sox_effects_module.apply_effects_file = apply_effects_file
    sys.modules['torchaudio.sox_effects'] = sox_effects_module
    torchaudio.sox_effects = sox_effects_module

    # 添加 set_audio_backend
    if not hasattr(torchaudio, 'set_audio_backend'):
        torchaudio.set_audio_backend = lambda backend: None

_apply_torchaudio_compat_patch()

import numpy as np
import librosa
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DLQualityResult:
    """深度学习质量评估结果"""
    # MOS分数 (1-5)
    mos_score: float = 0.0
    mos_normalized: float = 0.0  # 归一化到0-100

    # 多维度评分
    naturalness: float = 0.0      # 自然度
    clarity: float = 0.0          # 清晰度
    timbre_quality: float = 0.0   # 音色质量

    # 置信度
    confidence: float = 0.0

    # 方法
    method: str = 'none'


class SingMOSPredictor:
    """
    SingMOS 歌声MOS预测器

    使用预训练的wav2vec2模型预测歌声质量
    MOS范围: 1-5，越高越好
    """

    def __init__(self):
        self._model = None
        self._model_available = False
        self._load_model()

    def _load_model(self):
        """加载SingMOS模型"""
        try:
            import torch

            # 使用torch.hub加载SingMOS模型
            logger.info("[SingMOS] Loading model via torch.hub...")
            self._model = torch.hub.load(
                "South-Twilight/SingMOS:v1.1.2",
                "singmos_pro",
                trust_repo=True,
                verbose=False
            )
            self._model.eval()
            self._model_available = True
            logger.info("[SingMOS] Model loaded successfully")

        except Exception as e:
            logger.warning(f"[SingMOS] Failed to load model: {e}")
            self._model_available = False

    def predict(self, audio_path: str, sr: int = 16000) -> DLQualityResult:
        """
        预测歌声MOS分数

        Args:
            audio_path: 音频文件路径
            sr: 采样率

        Returns:
            DLQualityResult: 评估结果
        """
        if not self._model_available:
            return DLQualityResult(method='unavailable')

        try:
            import torch

            # 加载音频
            wave, orig_sr = librosa.load(audio_path, sr=None, mono=True)

            # 重采样到16kHz
            if orig_sr != sr:
                wave = librosa.resample(wave, orig_sr=orig_sr, target_sr=sr)

            # 转换为tensor - 需要 [B, T] 格式 (根据 SingMOS README)
            wave_tensor = torch.from_numpy(wave).unsqueeze(0).float()  # [1, T]
            length = torch.tensor([wave_tensor.shape[1]], dtype=torch.long)  # [1]

            # 预测MOS
            with torch.no_grad():
                mos = self._model(wave_tensor, length)

            mos_score = float(mos[0].item())

            # 归一化到0-100
            # SingMOS 实际输出范围约为 1.0-2.5 (而非理论上的 1-5)
            # 根据测试：高质量歌声约 1.6-1.7，噪声约 1.1，需要校准
            # 使用映射: raw_mos 1.1-1.8 -> standard_mos 2.0-4.5
            # 这样 1.65 的原始分数映射到约 3.8 的标准分数 (良好)
            if mos_score < 1.1:
                mos_score = 1.1
            elif mos_score > 1.8:
                # 高于 1.8 的情况，映射到优秀/专业级
                standard_mos = 4.5 + (mos_score - 1.8) * 1.0  # 1.8->4.5, 2.0->4.7
            else:
                # 线性映射: 1.1-1.8 -> 2.0-4.5
                standard_mos = 2.0 + (mos_score - 1.1) * (2.5 / 0.7)

            # 标准MOS 1-5 映射到 0-100
            mos_normalized = (standard_mos - 1.0) / 4.0 * 100

            return DLQualityResult(
                mos_score=standard_mos,  # 返回校准后的标准MOS
                mos_normalized=max(0, min(100, mos_normalized)),
                naturalness=mos_normalized * 0.9,  # 自然度与MOS相关
                clarity=mos_normalized * 0.85,
                timbre_quality=mos_normalized * 0.8,
                confidence=min(1.0, standard_mos / 3.5),  # MOS>3.5时置信度高
                method='singmos'
            )

        except Exception as e:
            logger.warning(f"[SingMOS] Prediction failed: {e}")
            return DLQualityResult(method='error')


class DLQualityAssessor:
    """
    v5.12: Simplified to SingMOS only.
    wvmos removed (evaluates telecom voice quality, not singing).
    """

    def __init__(self, use_singmos: bool = True):
        self._singmos = None
        self._manager = None
        try:
            from services.dl_services.model_manager import get_mos_model_manager
            self._manager = get_mos_model_manager()
            logger.info("[DLQualityAssessor] Using MOSModelManager")
        except Exception as e:
            logger.warning(f"[DLQualityAssessor] MOSModelManager not available: {e}")
        if use_singmos:
            try:
                self._singmos = SingMOSPredictor()
                if self._singmos._model_available and self._manager:
                    self._manager.register('singmos', self._singmos, priority=1)
            except Exception as e:
                logger.warning(f"[DLQualityAssessor] SingMOS init failed: {e}")

    @property
    def is_available(self) -> bool:
        """Check if SingMOS is available."""
        return self._singmos is not None and self._singmos._model_available

    def assess(self, audio_path: str) -> DLQualityResult:
        """
        v5.12: SingMOS-only quality assessment.
        wvmos removed (evaluates telecom voice quality, not singing).
        DL fusion weight reduced to 15% in score_service.py.
        """
        if self._manager:
            try:
                result = self._manager.assess_with_fallback(audio_path)
                if isinstance(result, DLQualityResult):
                    return result
                return DLQualityResult(
                    mos_score=getattr(result, 'mos_score', 3.0),
                    mos_normalized=getattr(result, 'mos_normalized', 50.0),
                    confidence=getattr(result, 'confidence', 0.3),
                    method=getattr(result, 'method', 'manager')
                )
            except Exception as e:
                logger.warning(f"[DLQualityAssessor] Manager assess failed: {e}")

        if self._singmos and self._singmos._model_available:
            result = self._singmos.predict(audio_path)
            if result.method == 'singmos':
                return result

        return DLQualityResult(method='none')

    def get_quality_level(self, mos: float) -> Tuple[str, str]:
        """
        根据MOS分数获取质量等级

        Args:
            mos: MOS分数 (1-5)

        Returns:
            (等级名称, 颜色)
        """
        if mos >= 4.5:
            return "专业级", "#22c55e"
        elif mos >= 4.0:
            return "优秀", "#3b82f6"
        elif mos >= 3.5:
            return "良好", "#10b981"
        elif mos >= 3.0:
            return "中等", "#f59e0b"
        elif mos >= 2.5:
            return "及格", "#f97316"
        else:
            return "待改进", "#ef4444"


def create_dl_assessor() -> DLQualityAssessor:
    """v5.12: Create DL assessor (SingMOS only, wvmos removed)."""
    return DLQualityAssessor(use_singmos=True)
