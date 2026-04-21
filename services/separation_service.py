"""
人声分离服务

使用 Demucs 模型进行音源分离，支持：
- 人声/伴奏分离
- 多音轨分离（鼓、贝斯、其他）
"""

import os
import subprocess
import shutil
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)


@dataclass
class SeparationResult:
    """分离结果 DTO"""
    success: bool
    vocals_path: Optional[str] = None      # 人声路径
    accompaniment_path: Optional[str] = None  # 伴奏路径
    drums_path: Optional[str] = None       # 鼓声路径
    bass_path: Optional[str] = None        # 贝斯路径
    other_path: Optional[str] = None       # 其他音轨路径
    duration: float = 0.0                  # 音频时长
    model_used: str = ""                   # 使用的模型
    error_message: Optional[str] = None


class SeparationService:
    """
    人声分离服务

    使用 Demucs 进行音源分离，支持多种模型：
    - htdemucs: 高质量分离（默认）
    - htdemucs_ft: 快速分离
    - mdx: MDX 模型
    """

    SUPPORTED_MODELS = ['htdemucs', 'htdemucs_ft', 'mdx', 'mdx_extra']
    DEFAULT_MODEL = 'htdemucs_ft'  # 默认使用快速模型

    def __init__(self, output_dir: Path):
        """
        初始化分离服务

        Args:
            output_dir: 输出目录路径
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def separate(
        self,
        audio_path: str,
        model: str = None,
        two_stems: str = 'vocals',
        output_format: str = 'mp3'
    ) -> SeparationResult:
        """
        执行音源分离

        Args:
            audio_path: 输入音频文件路径
            model: 使用的模型名称
            two_stems: 两轨分离模式 ('vocals' 或 None)
            output_format: 输出格式 ('mp3' 或 'wav')

        Returns:
            SeparationResult: 分离结果
        """
        if model is None:
            model = self.DEFAULT_MODEL

        if model not in self.SUPPORTED_MODELS:
            return SeparationResult(
                success=False,
                error_message=f"不支持的模型: {model}。支持的模型: {self.SUPPORTED_MODELS}"
            )

        audio_path = Path(audio_path)
        if not audio_path.exists():
            return SeparationResult(
                success=False,
                error_message=f"音频文件不存在: {audio_path}"
            )

        # 创建输出目录
        file_id = audio_path.stem
        output_path = self.output_dir / file_id

        try:
            # 构建 demucs 命令
            cmd = self._build_command(
                audio_path=str(audio_path),
                output_dir=str(self.output_dir),
                model=model,
                two_stems=two_stems,
                output_format=output_format
            )

            logger.info(f"执行分离命令: {' '.join(cmd)}")

            # 执行分离
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10分钟超时
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                logger.error(f"分离失败: {error_msg}")
                return SeparationResult(
                    success=False,
                    error_message=f"分离失败: {error_msg[:500]}"
                )

            # 查找输出文件
            separated_files = self._find_separated_files(output_path, model, two_stems)

            if not separated_files:
                return SeparationResult(
                    success=False,
                    error_message="分离完成但未找到输出文件"
                )

            # 获取音频时长
            duration = self._get_audio_duration(audio_path)

            # 构建结果
            return SeparationResult(
                success=True,
                vocals_path=separated_files.get('vocals'),
                accompaniment_path=separated_files.get('no_vocals') or separated_files.get('other'),
                drums_path=separated_files.get('drums'),
                bass_path=separated_files.get('bass'),
                other_path=separated_files.get('other'),
                duration=duration,
                model_used=model
            )

        except subprocess.TimeoutExpired:
            return SeparationResult(
                success=False,
                error_message="分离超时（超过10分钟）"
            )
        except Exception as e:
            logger.exception("分离过程发生错误")
            return SeparationResult(
                success=False,
                error_message=str(e)
            )

    def _build_command(
        self,
        audio_path: str,
        output_dir: str,
        model: str,
        two_stems: Optional[str],
        output_format: str
    ) -> List[str]:
        """构建 demucs 命令"""
        cmd = [
            'demucs',
            '-n', model,
            '-o', output_dir,
            '--filename', '{stem}.{ext}',
        ]

        # 两轨分离模式（人声/伴奏）
        if two_stems:
            cmd.extend(['--two-stems', two_stems])

        # 输出格式
        if output_format == 'mp3':
            cmd.extend(['--mp3'])

        cmd.append(audio_path)
        return cmd

    def _find_separated_files(
        self,
        output_path: Path,
        model: str,
        two_stems: Optional[str]
    ) -> Dict[str, str]:
        """
        查找分离后的文件

        Demucs 输出结构：
        output_dir/model_name/audio_name/stem_name.ext
        """
        files = {}

        # 查找模型输出目录
        model_dir = output_path.parent / model / output_path.name
        if not model_dir.exists():
            # 尝试直接在 output_path 下查找
            model_dir = output_path

        if not model_dir.exists():
            return files

        # 支持的扩展名
        extensions = ['.mp3', '.wav']

        # 查找各音轨文件
        for ext in extensions:
            for stem_file in model_dir.glob(f'*{ext}'):
                stem_name = stem_file.stem
                # 转换为相对路径（用于 Web 访问）
                relative_path = str(stem_file.relative_to(self.output_dir.parent))
                files[stem_name] = f'/static/separated/{stem_file.relative_to(self.output_dir)}'

        return files

    def _get_audio_duration(self, audio_path: Path) -> float:
        """获取音频时长"""
        try:
            import librosa
            duration = librosa.get_duration(path=str(audio_path))
            return round(duration, 2)
        except Exception:
            return 0.0

    def cleanup(self, file_id: str) -> bool:
        """
        清理分离文件

        Args:
            file_id: 文件标识符

        Returns:
            是否成功清理
        """
        try:
            target_dir = self.output_dir / file_id
            if target_dir.exists():
                shutil.rmtree(target_dir)
            return True
        except Exception as e:
            logger.error(f"清理失败: {e}")
            return False

    def get_available_models(self) -> List[Dict[str, str]]:
        """
        获取可用模型列表

        Returns:
            模型信息列表
        """
        return [
            {
                'name': 'htdemucs_ft',
                'description': '快速分离模型（推荐）',
                'speed': 'fast',
                'quality': 'good'
            },
            {
                'name': 'htdemucs',
                'description': '高质量分离模型',
                'speed': 'slow',
                'quality': 'best'
            },
            {
                'name': 'mdx',
                'description': 'MDX 模型',
                'speed': 'medium',
                'quality': 'good'
            },
            {
                'name': 'mdx_extra',
                'description': 'MDX 增强模型',
                'speed': 'slow',
                'quality': 'best'
            }
        ]
