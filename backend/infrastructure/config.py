"""
Pydantic Settings — 替代 config/default.py dataclass

ADR-5: 单一配置源，零硬编码回退。
通过环境变量 VAS_* 覆盖 (12-factor app)。
"""

from __future__ import annotations
from pathlib import Path
from typing import Set

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置 — frozen=True 防止运行时修改"""

    model_config = {
        "env_prefix": "VAS_",
        "frozen": True,
    }

    # ========== 项目路径 ==========
    project_root: Path = Path(__file__).parent.parent.parent

    # ========== 上传配置 ==========
    upload_folder: Path = Path(__file__).parent.parent.parent / "uploads"
    max_content_length: int = 50 * 1024 * 1024  # 50MB
    allowed_extensions: Set[str] = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac"}

    # ========== 历史记录配置 ==========
    history_file: Path = (
        Path(__file__).parent.parent.parent / "data" / "web_history.json"
    )
    history_max_records: int = 50

    # ========== 人声分离配置 ==========
    separated_dir: Path = (
        Path(__file__).parent.parent.parent / "web" / "static" / "separated"
    )

    # ========== 报告配置 ==========
    reports_dir: Path = (
        Path(__file__).parent.parent.parent / "web" / "static" / "reports"
    )

    # ========== 音频分析配置 ==========
    audio_sample_rate: int = 22050
    audio_hop_length: int = 512
    audio_frame_length: int = 2048

    # ========== 音高检测配置 ==========
    pitch_fmin: float = 65.0   # C2
    pitch_fmax: float = 1047.0  # C6

    def is_allowed_extension(self, filename: str) -> bool:
        """检查文件扩展名是否允许"""
        return Path(filename).suffix.lower() in self.allowed_extensions
