"""
PYINPitchExtractor — v7.1 Phase C

基频提取适配器。封装 librosa.pyin + TorchCREPE fallback。

文献: Mauch & Dixon (2014) — PYIN algorithm
"""

from __future__ import annotations
import logging
from dataclasses import dataclass

import numpy as np
import librosa

logger = logging.getLogger(__name__)

# 人声频率范围 (C2-C6)
VOICE_FMIN = 65.0
VOICE_FMAX = 1047.0


@dataclass(frozen=True)
class PitchResult:
    """基频提取结果 (不可变)"""
    f0: np.ndarray          # 基频 Hz, shape (n_frames,)
    times: np.ndarray       # 时间轴 s, shape (n_frames,)
    confidence: np.ndarray  # PYIN confidence, shape (n_frames,)
    detection_rate: float   # 0-1, 检测到的帧占比
    method: str = "pyin"    # pyin | torchcrepe | fcpe


class PitchExtractionError(Exception):
    """基频提取失败"""
    pass


class PYINPitchExtractor:
    """
    PYIN 基频提取器 — DDD infrastructure 适配器。

    用法:
        extractor = PYINPitchExtractor()
        result = extractor.extract(y, sr=22050)
    """

    def __init__(
        self,
        fmin: float = VOICE_FMIN,
        fmax: float = VOICE_FMAX,
        hop_length: int = 256,
    ) -> None:
        self._fmin = fmin
        self._fmax = fmax
        self._hop_length = hop_length

    def extract(
        self,
        y: np.ndarray,
        sr: int = 22050,
        enable_torchcrepe_fallback: bool = False,
    ) -> PitchResult:
        """
        提取基频。

        Args:
            y: 音频信号
            sr: 采样率
            enable_torchcrepe_fallback: 是否启用 TorchCREPE fallback

        Returns:
            PitchResult 包含 f0, times, confidence, detection_rate
        """
        if len(y) == 0:
            raise PitchExtractionError("Empty audio signal")

        # 1. PYIN 基频提取
        try:
            f0, voiced_flag, voiced_prob = librosa.pyin(
                y,
                fmin=self._fmin,
                fmax=self._fmax,
                sr=sr,
                hop_length=self._hop_length,
            )
        except Exception as e:
            raise PitchExtractionError(f"PYIN extraction failed: {e}") from e

        # NaN → 0
        f0 = np.nan_to_num(f0, nan=0.0).astype(np.float32)
        times = librosa.times_like(f0, sr=sr, hop_length=self._hop_length)
        confidence = np.nan_to_num(voiced_prob, nan=0.0).astype(np.float32)

        detection_rate = float(np.mean(confidence > 0.5))

        # 2. TorchCREPE fallback (低检测率时)
        method = "pyin"
        if enable_torchcrepe_fallback and detection_rate < 0.5:
            try:
                f0, method = self._try_torchcrepe(y, sr, f0)
            except Exception as e:
                logger.debug("TorchCREPE fallback failed: %s", e)

        # 3. Clip to vocal range
        f0 = np.clip(f0, 0, self._fmax)

        return PitchResult(
            f0=f0,
            times=times,
            confidence=confidence,
            detection_rate=round(detection_rate, 4),
            method=method,
        )

    def _try_torchcrepe(
        self, y: np.ndarray, sr: int, fallback_f0: np.ndarray
    ) -> tuple[np.ndarray, str]:
        """尝试 TorchCREPE"""
        try:
            import torchcrepe
            import torch

            audio_tensor = torch.from_numpy(y).float().unsqueeze(0)
            with torch.no_grad():
                f0_tensor, confidence = torchcrepe.predict(
                    audio_tensor,
                    sr,
                    hop_length=self._hop_length,
                    fmin=self._fmin,
                    fmax=self._fmax,
                    decoder=torchcrepe.decode.weighted_argmax,
                )
            f0 = f0_tensor.squeeze().numpy().astype(np.float32)
            # Pad/trim to match PYIN length
            if len(f0) < len(fallback_f0):
                f0 = np.pad(f0, (0, len(fallback_f0) - len(f0)))
            else:
                f0 = f0[:len(fallback_f0)]
            logger.info("TorchCREPE fallback: replaced PYIN (detection_rate < 0.5)")
            return f0, "torchcrepe"
        except ImportError:
            raise
        except Exception as e:
            raise PitchExtractionError(f"TorchCREPE failed: {e}") from e
