"""
默认配置
所有配置项集中管理，便于维护和扩展
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Tuple, Dict


@dataclass(frozen=True)
class Config:
    """
    不可变配置类

    设计原则：
    - 所有配置项在此集中定义
    - frozen=True 保证不可变，防止运行时被修改
    - 便于测试时 mock

    扩展方式：
    - 新增配置项只需在此添加字段
    - 不同环境可创建子类覆盖
    """

    # ========== 项目路径 ==========
    PROJECT_ROOT: Path = field(default_factory=lambda: Path(__file__).parent.parent)

    # ========== 上传配置 ==========
    UPLOAD_FOLDER: Path = field(default_factory=lambda: Path(__file__).parent.parent / "uploads")
    MAX_CONTENT_LENGTH: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: Tuple[str, ...] = ('.wav', '.mp3', '.flac', '.ogg', '.m4a')

    # ========== 历史记录配置 ==========
    HISTORY_FILE: Path = field(default_factory=lambda: Path(__file__).parent.parent / "data" / "web_history.json")
    HISTORY_MAX_RECORDS: int = 50

    # ========== 人声分离配置 ==========
    SEPARATED_DIR: Path = field(default_factory=lambda: Path(__file__).parent.parent / "web" / "static" / "separated")

    # ========== 报告配置 ==========
    REPORTS_DIR: Path = field(default_factory=lambda: Path(__file__).parent.parent / "web" / "static" / "reports")

    # ========== 音频分析配置 ==========
    AUDIO_SAMPLE_RATE: int = 22050  # librosa 默认采样率
    AUDIO_HOP_LENGTH: int = 512     # 帧移
    AUDIO_FRAME_LENGTH: int = 2048  # 帧长

    # ========== 音高检测配置 ==========
    PITCH_FMIN: float = 65.0   # C2 ~ 65 Hz
    PITCH_FMAX: float = 1047.0 # C6 ~ 1047 Hz

    # ========== 评分配置 v4.1（气息专项优化版）==========
    # 专业权重分配（气息权重提升，总和=100%）
    SCORE_WEIGHTS: Dict[str, float] = field(default_factory=lambda: {
        'pitch': 0.30,      # 音准 30%
        'rhythm': 0.20,     # 节奏 20%
        'breath': 0.20,     # 气息 20%
        'technique': 0.20,  # 发声技术 20%
        'artistry': 0.10    # 艺术表现 10%
    })

    # 音准阈值（音分）
    PITCH_EXCELLENT_CENTS: int = 10   # 满分阈值
    PITCH_GOOD_CENTS: int = 30        # 良好阈值
    PITCH_PASS_CENTS: int = 50        # 合格阈值

    # 节奏阈值（拍长比例）
    RHYTHM_EXCELLENT_RATIO: float = 0.1   # 满分阈值
    RHYTHM_GOOD_RATIO: float = 0.2        # 良好阈值
    RHYTHM_PASS_RATIO: float = 0.3        # 合格阈值

    # 气息阈值（v4.1 调整）
    BREATH_EXCELLENT_FLUCTUATION: float = 0.20   # 满分阈值（放宽）
    BREATH_GOOD_FLUCTUATION: float = 0.35        # 良好阈值（放宽）
    BREATH_PASS_FLUCTUATION: float = 0.50        # 合格阈值（放宽）

    # 气息评估细分权重
    BREATH_WEIGHTS: Dict[str, float] = field(default_factory=lambda: {
        'long_note_support': 0.40,     # 长音气息支撑 40%
        'dynamic_control': 0.25,       # 强弱动态控制 25%
        'breath_design': 0.20,         # 气口设计 20%
        'breath_technique': 0.15       # 气声技巧 15%
    })

    # 分唱法HNR阈值
    HNR_THRESHOLDS: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        'pop': {'min_excellent': 8, 'max_excellent': 15, 'min_acceptable': 5},
        'classical': {'min_excellent': 20, 'max_excellent': 30, 'min_acceptable': 15},
        'folk': {'min_excellent': 15, 'max_excellent': 25, 'min_acceptable': 10},
        'rap': {'min_excellent': 5, 'max_excellent': 12, 'min_acceptable': 3}
    })

    # 底线规则阈值
    CONSECUTIVE_OFF_THRESHOLD: int = 3    # 连续跑调阈值
    OFF_BEAT_THRESHOLD: int = 2           # 脱离节拍段阈值
    MIN_HNR_THRESHOLD: float = 3.0        # 最低HNR阈值（从3.0放宽）

    # 等级阈值（兼容旧版）
    SCORE_LEVEL_EXCELLENT: int = 90
    SCORE_LEVEL_GOOD: int = 80
    SCORE_LEVEL_AVERAGE: int = 70
    SCORE_LEVEL_PASS: int = 60

    def __post_init__(self):
        """初始化后创建必要目录"""
        # 确保目录存在
        self.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        self.HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        self.SEPARATED_DIR.mkdir(parents=True, exist_ok=True)
        self.REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    def is_allowed_extension(self, filename: str) -> bool:
        """检查文件扩展名是否允许"""
        return Path(filename).suffix.lower() in self.ALLOWED_EXTENSIONS

    def get_upload_path(self, filename: str) -> Path:
        """获取上传文件的完整路径"""
        return self.UPLOAD_FOLDER / filename


# 全局配置实例 (单例)
config = Config()
