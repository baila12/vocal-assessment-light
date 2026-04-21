"""
音频特征可视化服务
使用 Matplotlib 生成三特征可视化图片

设计原则：
- 单一职责：只负责可视化生成
- 无状态：纯函数，便于测试
- 可配置：参数可外部化
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple
import hashlib
import traceback
from urllib.parse import quote

import librosa
import librosa.display
import numpy as np
import matplotlib
matplotlib.use('Agg')  # 非交互式后端，适合服务器端
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from config import Config


@dataclass
class VisualizationResult:
    """可视化结果 DTO"""
    success: bool
    spectrogram_path: Optional[str] = None
    pitch_trajectory_path: Optional[str] = None
    energy_path: Optional[str] = None
    combined_path: Optional[str] = None
    error: Optional[str] = None


class VisualizationService:
    """
    音频特征可视化服务

    职责：
    - 生成 Log-Mel 频谱图
    - 生成基音轨迹图
    - 生成短时能量图
    - 生成组合图（三合一）

    不负责：
    - 音频特征计算（由 AudioService 负责）
    """

    # 可视化参数（与用户示例对齐）
    N_MELS = 64           # 梅尔带数量
    N_FFT = 2048          # FFT 窗口大小
    HOP_LENGTH = 512      # 帧移
    VMIN = -80            # dB 最小值
    VMAX = 0              # dB 最大值
    COLORMAP = 'magma'    # 颜色映射

    # 基音范围
    FMIN = librosa.note_to_hz('C2')  # ~65 Hz
    FMAX = librosa.note_to_hz('C6')  # ~1047 Hz

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self._output_dir = self.config.PROJECT_ROOT / 'web' / 'static' / 'plots'
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def generate_feature_plots(
        self,
        audio_data: np.ndarray,
        sample_rate: int,
        file_id: Optional[str] = None
    ) -> VisualizationResult:
        """
        生成三特征可视化图片

        Args:
            audio_data: 音频数据
            sample_rate: 采样率
            file_id: 文件标识（用于生成唯一文件名）

        Returns:
            VisualizationResult: 包含图片路径的结果
        """
        try:
            # 生成唯一文件标识
            if file_id is None:
                file_id = hashlib.md5(audio_data.tobytes()).hexdigest()[:12]

            # 1. 计算 Log-Mel 频谱图
            log_mel, mel_times = self._compute_log_mel(audio_data, sample_rate)

            # 2. 计算基音轨迹
            f0, f0_times = self._compute_pitch_trajectory(audio_data, sample_rate)

            # 3. 计算 RMS 能量
            rms, rms_times = self._compute_rms_energy(audio_data, sample_rate)

            # 4. 生成单独的图片
            spectrogram_path = self._save_spectrogram(
                log_mel, mel_times, sample_rate, file_id
            )
            pitch_path = self._save_pitch_trajectory(
                f0, f0_times, file_id
            )
            energy_path = self._save_energy(
                rms, rms_times, file_id
            )

            # 5. 生成组合图
            combined_path = self._save_combined(
                log_mel, mel_times,
                f0, f0_times,
                rms, rms_times,
                sample_rate, file_id
            )

            return VisualizationResult(
                success=True,
                spectrogram_path=spectrogram_path,
                pitch_trajectory_path=pitch_path,
                energy_path=energy_path,
                combined_path=combined_path
            )

        except Exception as e:
            return VisualizationResult(
                success=False,
                error=str(e)
            )

    def _compute_log_mel(
        self,
        audio_data: np.ndarray,
        sample_rate: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """计算 Log-Mel 频谱图"""
        mel_spectrogram = librosa.feature.melspectrogram(
            y=audio_data,
            sr=sample_rate,
            n_mels=self.N_MELS,
            n_fft=self.N_FFT,
            hop_length=self.HOP_LENGTH
        )
        log_mel = librosa.power_to_db(mel_spectrogram, ref=np.max)
        times = librosa.times_like(log_mel, sr=sample_rate, hop_length=self.HOP_LENGTH)
        return log_mel, times

    def _compute_pitch_trajectory(
        self,
        audio_data: np.ndarray,
        sample_rate: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """计算基音轨迹"""
        f0, voiced_flag, _ = librosa.pyin(
            audio_data,
            fmin=self.FMIN,
            fmax=self.FMAX,
            sr=sample_rate,
            hop_length=self.HOP_LENGTH
        )
        times = librosa.times_like(f0, sr=sample_rate, hop_length=self.HOP_LENGTH)
        return f0, times

    def _compute_rms_energy(
        self,
        audio_data: np.ndarray,
        sample_rate: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """计算 RMS 短时能量"""
        rms = librosa.feature.rms(
            y=audio_data,
            frame_length=self.N_FFT,
            hop_length=self.HOP_LENGTH
        )[0]
        times = librosa.times_like(rms, sr=sample_rate, hop_length=self.HOP_LENGTH)
        return rms, times

    def _save_spectrogram(
        self,
        log_mel: np.ndarray,
        times: np.ndarray,
        sample_rate: int,
        file_id: str
    ) -> str:
        """保存 Log-Mel 频谱图"""
        fig, ax = plt.subplots(figsize=(15, 4))

        img = librosa.display.specshow(
            log_mel,
            sr=sample_rate,
            hop_length=self.HOP_LENGTH,
            x_axis='time',
            y_axis='mel',
            ax=ax,
            cmap=self.COLORMAP,
            vmin=self.VMIN,
            vmax=self.VMAX
        )

        ax.set_title(f'Log-Mel Spectrogram ({self.N_MELS} bands)', fontsize=14, pad=15)
        ax.set_ylabel('Hz', fontsize=12)
        ax.set_xlabel('Time', fontsize=12)

        # 添加色条
        cbar = fig.colorbar(img, ax=ax, format='%+2.0f dB')
        cbar.set_ticks([0, -20, -40, -60, -80])

        # 时间格式化
        ax.xaxis.set_major_formatter(FuncFormatter(self._format_time))

        plt.tight_layout()

        filepath = self._output_dir / f'{file_id}_spectrogram.png'
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close(fig)

        # URL编码文件名以支持中文等非ASCII字符
        encoded_file_id = quote(file_id)
        return f'/plots/{encoded_file_id}_spectrogram.png'

    def _save_pitch_trajectory(
        self,
        f0: np.ndarray,
        times: np.ndarray,
        file_id: str
    ) -> str:
        """保存基音轨迹图"""
        fig, ax = plt.subplots(figsize=(15, 3))

        # 过滤无效值
        valid_mask = ~np.isnan(f0) & (f0 > 50) & (f0 < 600)
        valid_times = times[valid_mask]
        valid_f0 = f0[valid_mask]

        ax.plot(valid_times, valid_f0, color='#2ca02c', linewidth=1.5)
        ax.set_title('Pitch Trajectory', fontsize=14, pad=15)
        ax.set_ylabel('Hz', fontsize=12)
        ax.set_xlabel('Time', fontsize=12)
        ax.set_ylim(50, 600)
        ax.xaxis.set_major_formatter(FuncFormatter(self._format_time))

        plt.tight_layout()

        filepath = self._output_dir / f'{file_id}_pitch.png'
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close(fig)

        encoded_file_id = quote(file_id)
        return f'/plots/{encoded_file_id}_pitch.png'

    def _save_energy(
        self,
        rms: np.ndarray,
        times: np.ndarray,
        file_id: str
    ) -> str:
        """保存短时能量图"""
        fig, ax = plt.subplots(figsize=(15, 3))

        ax.plot(times, rms, color='#ff0000', linewidth=1)
        ax.set_title('Short-Time Energy (RMS)', fontsize=14, pad=15)
        ax.set_ylabel('Amplitude', fontsize=12)
        ax.set_xlabel('Time', fontsize=12)
        ax.set_ylim(0, np.max(rms) * 1.1)
        ax.xaxis.set_major_formatter(FuncFormatter(self._format_time))

        plt.tight_layout()

        filepath = self._output_dir / f'{file_id}_energy.png'
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close(fig)

        encoded_file_id = quote(file_id)
        return f'/plots/{encoded_file_id}_energy.png'

    def _save_combined(
        self,
        log_mel: np.ndarray,
        mel_times: np.ndarray,
        f0: np.ndarray,
        f0_times: np.ndarray,
        rms: np.ndarray,
        rms_times: np.ndarray,
        sample_rate: int,
        file_id: str
    ) -> str:
        """保存组合图（三合一）"""
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(15, 10), sharex=True)

        # 子图1：Log-Mel 频谱图
        img = librosa.display.specshow(
            log_mel,
            sr=sample_rate,
            hop_length=self.HOP_LENGTH,
            x_axis='time',
            y_axis='mel',
            ax=ax1,
            cmap=self.COLORMAP,
            vmin=self.VMIN,
            vmax=self.VMAX
        )
        ax1.set_title(f'Log-Mel Spectrogram ({self.N_MELS} bands)', fontsize=14, pad=15)
        ax1.set_ylabel('Hz', fontsize=12)
        cbar = fig.colorbar(img, ax=ax1, format='%+2.0f dB')
        cbar.set_ticks([0, -20, -40, -60, -80])

        # 子图2：基音轨迹
        valid_mask = ~np.isnan(f0) & (f0 > 50) & (f0 < 600)
        ax2.plot(f0_times[valid_mask], f0[valid_mask], color='#2ca02c', linewidth=1.5)
        ax2.set_title('Pitch Trajectory', fontsize=14, pad=15)
        ax2.set_ylabel('Hz', fontsize=12)
        ax2.set_ylim(50, 600)

        # 子图3：短时能量
        ax3.plot(rms_times, rms, color='#ff0000', linewidth=1)
        ax3.set_title('Short-Time Energy', fontsize=14, pad=15)
        ax3.set_ylabel('Amplitude', fontsize=12)
        ax3.set_xlabel('Time', fontsize=12)
        ax3.set_ylim(0, np.max(rms) * 1.1)

        # 统一时间格式
        for ax in [ax1, ax2, ax3]:
            ax.xaxis.set_major_formatter(FuncFormatter(self._format_time))

        plt.tight_layout()

        filepath = self._output_dir / f'{file_id}_combined.png'
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close(fig)

        encoded_file_id = quote(file_id)
        return f'/plots/{encoded_file_id}_combined.png'

    @staticmethod
    def _format_time(x, pos):
        """格式化时间为 分:秒 格式"""
        minutes = int(x // 60)
        seconds = int(x % 60)
        return f"{minutes}:{seconds:02d}"