"""
DemucsSeparator — v7.1 Phase C

人声分离适配器。封装 Demucs htdemucs_ft 模型。

文献: Rouard, Massa, Defossez (2023) — Hybrid Transformer Demucs
"""

from __future__ import annotations
import logging
import os
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SeparationResult:
    """人声分离结果 (不可变)"""
    vocals_path: str
    accompaniment_path: str
    model: str
    device: str  # cuda | cpu
    success: bool = True


class SeparationError(Exception):
    """人声分离失败"""
    pass


class DemucsSeparator:
    """
    Demucs 人声分离器 — DDD infrastructure 适配器。

    用法:
        separator = DemucsSeparator()
        result = separator.separate("/path/to/audio.mp3")
    """

    DEFAULT_MODEL = "htdemucs_ft"
    TWO_STEMS_MODEL = "htdemucs"

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        output_dir: str | Path | None = None,
    ) -> None:
        self._model = model
        self._output_dir = Path(output_dir) if output_dir else None

    def separate(
        self,
        filepath: str | Path,
        two_stems: str = "vocals",
        device: str | None = None,
    ) -> SeparationResult:
        """
        分离人声。

        Args:
            filepath: 音频文件路径
            two_stems: 分离目标 ("vocals" | "drums" | "bass" | "other")
            device: 计算设备 (auto-detect if None)

        Returns:
            SeparationResult
        """
        import torch

        filepath = Path(filepath)
        if not filepath.exists():
            raise SeparationError(f"File not found: {filepath}")

        # GPU 检测
        if device is None:
            if torch.cuda.is_available():
                device = "cuda"
            else:
                device = "cpu"
                logger.info("CUDA not available, using CPU (slower)")

        try:
            from demucs import separate

            # Demucs separates into its default output dir
            output_base = self._output_dir or filepath.parent / "separated"
            output_base.mkdir(parents=True, exist_ok=True)

            # Run separation
            separate.main([
                "--two-stems", two_stems,
                "-n", self._model,
                "--device", device,
                "-o", str(output_base),
                str(filepath),
            ])

            # Demucs outputs to: output_dir/model_name/filename/vocals.wav
            model_dir = output_base / self._model
            song_dir = model_dir / filepath.stem

            vocals_path = song_dir / f"{two_stems}.wav"
            no_vocals_path = song_dir / f"no_{two_stems}.wav"

            if not vocals_path.exists():
                # Try alternate naming
                alt_dir = song_dir if song_dir.exists() else model_dir
                candidates = list(alt_dir.glob(f"**/{two_stems}.*"))
                if candidates:
                    vocals_path = candidates[0]
                else:
                    raise SeparationError(
                        f"Demucs completed but vocals not found. Expected: {vocals_path}"
                    )

            return SeparationResult(
                vocals_path=str(vocals_path),
                accompaniment_path=str(no_vocals_path) if no_vocals_path.exists() else "",
                model=self._model,
                device=device,
                success=True,
            )

        except ImportError:
            raise SeparationError(
                "demucs not installed. Install with: pip install demucs"
            )
        except Exception as e:
            raise SeparationError(f"Separation failed: {e}") from e

    @staticmethod
    def detect_gpu() -> str:
        """检测 GPU 可用性"""
        try:
            import torch
            if torch.cuda.is_available():
                return f"cuda:{torch.cuda.get_device_name(0)}"
            return "cpu"
        except ImportError:
            return "cpu (torch not installed)"
