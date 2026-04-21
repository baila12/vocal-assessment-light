"""
录音模块 - 实时音频录制与分析
性能优化：使用deque限制缓冲、优化callback、减少concatenate
"""
import numpy as np
import threading
import time
import os
import tempfile
import platform
from typing import Optional
from collections import deque
from PySide6.QtCore import QObject, Signal, QTimer
import logging

logger = logging.getLogger(__name__)

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
    _sd_error = None
except OSError as e:
    SOUNDDEVICE_AVAILABLE = False
    sd = None
    _sd_error = str(e)
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    sd = None
    _sd_error = "sounddevice模块未安装"


class AudioRecorder(QObject):
    """音频录制器 - 性能优化版"""

    volume_updated = Signal(float)
    waveform_updated = Signal(np.ndarray)
    time_updated = Signal(float)
    recording_started = Signal()
    recording_stopped = Signal(str)
    error_occurred = Signal(str)

    DEFAULT_SAMPLE_RATE = 16000
    DEFAULT_CHANNELS = 1
    MAX_BUFFER_FRAMES = 6000  # 约10分钟@16kHz, 100ms/frame

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sample_rate = self.DEFAULT_SAMPLE_RATE
        self.channels = self.DEFAULT_CHANNELS
        self.is_recording = False
        # 使用deque限制缓冲区大小，避免内存无限增长
        self.recorded_frames: deque = deque(maxlen=self.MAX_BUFFER_FRAMES)
        self.stream = None
        self.recording_start_time = None
        self._frame_count = 0  # 用于波形更新计数
        self._check_audio_system()

    def _check_audio_system(self):
        """检查音频系统状态，提供详细错误信息"""
        self._audio_ready = False
        self._audio_error = ""

        if not SOUNDDEVICE_AVAILABLE:
            self._audio_error = self._get_detailed_init_error()
            return

        try:
            devices = sd.query_devices()
            default_input = sd.default.device[0]

            if default_input is None or default_input < 0:
                self._audio_error = self._get_no_device_error()
                return

            # 尝试打开测试流验证权限
            try:
                test_stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype=np.float32,
                    blocksize=1024
                )
                test_stream.close()
            except Exception as e:
                self._audio_error = self._get_permission_error(str(e))
                return

            self._audio_ready = True

        except Exception as e:
            self._audio_error = f"音频设备检测失败: {str(e)}"

    def _get_detailed_init_error(self) -> str:
        """获取详细的初始化错误信息"""
        error_msg = "音频系统初始化失败"

        if platform.system() == "Windows":
            error_msg += "\n\n可能原因：\n"
            error_msg += "1. 未安装Visual C++运行库\n"
            error_msg += "2. PortAudio驱动未正确安装\n"
            error_msg += "3. sounddevice模块安装不完整\n\n"
            error_msg += "解决方案：\n"
            error_msg += "pip uninstall sounddevice\n"
            error_msg += "pip install sounddevice"
        else:
            error_msg += f"\n\n错误详情: {_sd_error if _sd_error else 'unknown'}"

        return error_msg

    def _get_no_device_error(self) -> str:
        """获取无输入设备的错误信息"""
        error_msg = "未找到麦克风设备"

        if platform.system() == "Windows":
            error_msg += "\n\n请检查：\n"
            error_msg += "1. 麦克风已正确连接\n"
            error_msg += "2. 在Windows设置中允许应用访问麦克风\n"
            error_msg += "3. 在声音设置中设置默认录音设备"

        return error_msg

    def _get_permission_error(self, original_error: str) -> str:
        """获取权限错误的友好提示"""
        error_msg = "无法访问麦克风"

        if platform.system() == "Windows":
            error_msg += "\n\n请检查Windows隐私设置：\n"
            error_msg += "1. 打开设置 > 隐私 > 麦克风\n"
            error_msg += "2. 允许桌面应用访问麦克风\n"
            error_msg += "3. 允许Python访问麦克风"

        return error_msg

    def is_ready(self) -> bool:
        return self._audio_ready

    def get_error(self) -> str:
        return self._audio_error

    def _audio_callback(self, indata, frames, time_info, status):
        """音频回调 - 优化版：减少callback中的计算"""
        # 最小化拷贝操作
        self.recorded_frames.append(indata.copy())
        self._frame_count += 1

        # 计算音量 - 简化计算
        rms = np.sqrt(np.mean(indata ** 2))
        db = 20 * np.log10(rms) if rms > 0 else -80
        self.volume_updated.emit(db)

        # 每10帧更新一次波形（约1秒），减少concatenate开销
        if self._frame_count % 10 == 0 and len(self.recorded_frames) >= 10:
            # 只取最近10帧
            recent_frames = list(self.recorded_frames)[-10:]
            waveform = np.concatenate(recent_frames, axis=0).flatten()
            self.waveform_updated.emit(waveform)

        # 使用帧数计算时间，避免time.time()调用
        elapsed = self._frame_count * 0.1  # blocksize是100ms
        self.time_updated.emit(elapsed)

    def start_recording(self):
        if self.is_recording:
            self.error_occurred.emit("已经在录音中")
            return
        if not self._audio_ready:
            self.error_occurred.emit(self._audio_error)
            return
        # 重置缓冲区和计数器
        self.recorded_frames.clear()
        self._frame_count = 0
        self.is_recording = True
        self.recording_start_time = time.time()
        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate, channels=self.channels,
                dtype=np.float32, callback=self._audio_callback,
                blocksize=int(self.sample_rate * 0.1)
            )
            self.stream.start()
            self.recording_started.emit()
        except Exception as e:
            self.is_recording = False
            logger.error(f"录音启动失败: {e}")
            self.error_occurred.emit(f"录音启动失败: {str(e)}")

    def stop_recording(self, save_path: Optional[str] = None) -> Optional[str]:
        if not self.is_recording:
            return None
        self.is_recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        if self.recorded_frames:
            # 使用预分配数组加速合并
            total_frames = sum(len(f) for f in self.recorded_frames)
            audio_data = np.zeros((total_frames, self.channels), dtype=np.float32)

            offset = 0
            for frame in self.recorded_frames:
                frame_len = len(frame)
                audio_data[offset:offset + frame_len] = frame
                offset += frame_len

            # 清理缓冲区释放内存
            self.recorded_frames.clear()

            if save_path is None:
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                save_path = os.path.join(tempfile.gettempdir(), f"recording_{timestamp}.wav")
            try:
                import soundfile as sf
                sf.write(save_path, audio_data, self.sample_rate)
                self.recording_stopped.emit(save_path)
                return save_path
            except Exception as e:
                self.error_occurred.emit(f"保存录音失败: {str(e)}")
        return None

    def get_audio_data(self) -> Optional[np.ndarray]:
        if self.recorded_frames:
            return np.concatenate(self.recorded_frames, axis=0).flatten()
        return None