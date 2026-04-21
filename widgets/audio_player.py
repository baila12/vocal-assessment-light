"""
音频播放器 - 播放控制组件
"""
from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from pathlib import Path


class AudioPlayer(QObject):
    """音频播放控制器"""
    position_changed = Signal(int)
    duration_changed = Signal(int)
    finished = Signal()
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._player.setAudioOutput(self._audio_output)
        self._filepath = None
        self._duration = 0
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.mediaStatusChanged.connect(self._on_media_status_changed)
        self._player.errorOccurred.connect(self._on_error)

    def load(self, filepath: str) -> bool:
        try:
            path = Path(filepath)
            if not path.exists():
                self.error_occurred.emit(f"文件不存在: {filepath}")
                return False
            self._filepath = filepath
            self._player.setSource(QUrl.fromLocalFile(filepath))
            return True
        except Exception as e:
            self.error_occurred.emit(f"加载失败: {str(e)}")
            return False

    def play(self):
        self._player.play()

    def pause(self):
        self._player.pause()

    def stop(self):
        self._player.stop()

    def set_position(self, position_ms: int):
        self._player.setPosition(position_ms)

    def get_position(self) -> int:
        return self._player.position()

    def get_duration(self) -> int:
        return self._duration

    def is_playing(self) -> bool:
        return self._player.playbackState() == QMediaPlayer.PlayingState

    def set_volume(self, volume: float):
        self._audio_output.setVolume(volume)

    def _on_position_changed(self, position: int):
        self.position_changed.emit(position)

    def _on_duration_changed(self, duration: int):
        self._duration = duration
        self.duration_changed.emit(duration)

    def _on_media_status_changed(self, status):
        if status == QMediaPlayer.EndOfMedia:
            self.finished.emit()

    def _on_error(self, error, error_string):
        self.error_occurred.emit(error_string)