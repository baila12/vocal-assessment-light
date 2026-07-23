"""
FCPE Pitch Extractor — v7.1 Phase D

FCPE (Frame-level Contextual Pitch Estimation) 基频检测。
替换 YIN/PYIN, 精度更高 (96.79% RPA)。

文献: torchfcpe (2024) — https://github.com/CNChif/torchfcpe
"""

from __future__ import annotations
import logging
import numpy as np

from backend.infrastructure.audio.pyin_extractor import PitchResult, PitchExtractionError

logger = logging.getLogger(__name__)


class FCPEPitchExtractor:
    """
    FCPE 基频提取器 — v7.1 P0 集成。

    用法:
        extractor = FCPEPitchExtractor()
        result = extractor.extract(y, sr=16000)  # FCPE 要求 16kHz
    """

    FCPE_SAMPLE_RATE = 16000

    def __init__(
        self,
        fmin: float = 65.0,
        fmax: float = 1047.0,
        hop_length: int = 256,
    ) -> None:
        self._fmin = fmin
        self._fmax = fmax
        self._hop_length = hop_length

    def extract(self, y: np.ndarray, sr: int = 22050) -> PitchResult:
        """
        FCPE 基频提取。

        Args:
            y: 音频信号 (会自动重采样到 16kHz)
            sr: 原始采样率

        Returns:
            PitchResult
        """
        try:
            import torch
            import torchfcpe
        except ImportError:
            raise PitchExtractionError(
                "torchfcpe not installed. Install with: pip install torchfcpe"
            )

        if len(y) == 0:
            raise PitchExtractionError("Empty audio signal")

        # Resample to 16kHz (FCPE requirement)
        if sr != self.FCPE_SAMPLE_RATE:
            import librosa
            y = librosa.resample(y, orig_sr=sr, target_sr=self.FCPE_SAMPLE_RATE)
            sr_effective = self.FCPE_SAMPLE_RATE
        else:
            sr_effective = sr

        try:
            with torch.no_grad():
                device = 'cuda' if torch.cuda.is_available() else 'cpu'
                audio_tensor = torch.from_numpy(y).float().unsqueeze(0).to(device)
                model = torchfcpe.spawn_bundled_infer_model(device=device)
                f0_tensor = model.infer(audio_tensor, sr=sr_effective)
                f0 = f0_tensor.squeeze().cpu().numpy().astype(np.float32)

        except Exception as e:
            raise PitchExtractionError(f"FCPE extraction failed: {e}") from e

        # Clip and cleanup
        f0 = np.nan_to_num(f0, nan=0.0)
        f0 = np.clip(f0, 0, self._fmax)

        # Generate time axis (FCPE uses ~160 sample hop at 16kHz → ~10ms/frame)
        fcpe_hop = 160
        times = np.arange(len(f0)) * fcpe_hop / sr_effective

        # Estimate confidence (FCPE doesn't provide per-frame confidence)
        confidence = np.where(f0 > 0, 1.0, 0.0).astype(np.float32)
        detection_rate = float(np.mean(confidence))

        return PitchResult(
            f0=f0,
            times=times,
            confidence=confidence,
            detection_rate=round(detection_rate, 4),
            method="fcpe",
        )
