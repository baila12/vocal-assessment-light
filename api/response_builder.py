"""
API 响应构建器
支持版本化的响应格式，便于 API 兼容性维护
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """分析结果数据传输对象"""
    # 基本信息
    filename: str = ""
    duration: float = 0.0
    duration_seconds: float = 0.0
    sample_rate: int = 22050
    file_size: str = ""

    # 人声质量
    is_voice: bool = True
    voice_ratio: float = 0.0
    voice_quality_score: float = 0.0
    silence_ratio: float = 0.0
    harmonic_ratio: float = 0.0

    # 音乐风格
    music_style: str = "unknown"
    style_cn: str = "未知"
    style_confidence: float = 0.0
    music_mood: str = "unknown"

    # DL 评估
    dl_mos_score: float = 0.0
    dl_mos_normalized: float = 0.0
    dl_method: str = "none"
    dl_confidence: float = 0.0
    dl_available: bool = False

    # 五维评分
    pitch_score: float = 0.0
    rhythm_score: float = 0.0
    breath_score: float = 0.0
    technique_score: float = 0.0
    artistry_score: float = 0.0
    total_score: float = 0.0

    # 等级
    level: str = ""
    stars: str = ""
    color: str = ""

    # 诊断
    pitch_diagnosis: Dict[str, Any] = field(default_factory=dict)
    rhythm_diagnosis: Dict[str, Any] = field(default_factory=dict)
    breath_diagnosis: Dict[str, Any] = field(default_factory=dict)
    technique_diagnosis: Dict[str, Any] = field(default_factory=dict)
    artistry_diagnosis: Dict[str, Any] = field(default_factory=dict)
    critical_issues: List[str] = field(default_factory=list)
    is_disqualified: bool = False

    # 建议
    advice: List[str] = field(default_factory=list)

    # 可视化
    visualization: Optional[Dict[str, str]] = None

    # 音色
    timbre: Optional[Dict[str, Any]] = None

    # 逐句评分
    phrases: Optional[Dict[str, Any]] = None

    # 波形和音高曲线
    waveform: Optional[Dict[str, Any]] = None
    pitch_curve: Optional[Dict[str, Any]] = None

    # 其他信息
    volume_info: Optional[Dict[str, Any]] = None
    pitch_info: Optional[Dict[str, Any]] = None
    rhythm_info: Optional[Dict[str, Any]] = None
    emotion_info: Optional[Dict[str, Any]] = None


class ResponseBuilder(ABC):
    """响应构建器接口"""

    @abstractmethod
    def build(self, result: AnalysisResult) -> Dict[str, Any]:
        """构建响应"""
        pass


class ResponseV5Builder(ResponseBuilder):
    """
    v5.0 响应格式

    最新的五维评分格式
    """

    def build(self, result: AnalysisResult) -> Dict[str, Any]:
        return {
            'success': True,
            'is_voice': result.is_voice,

            # 人声质量
            'voice_quality': {
                'is_voice': result.is_voice,
                'voice_ratio': round(result.voice_ratio, 1),
                'quality_score': round(result.voice_quality_score, 1),
                'silence_ratio': round(result.silence_ratio, 1),
                'harmonic_ratio': round(result.harmonic_ratio, 1)
            },

            # 基本信息
            'basic_info': {
                'filename': result.filename,
                'duration': result.duration,
                'duration_seconds': result.duration_seconds,
                'sample_rate': result.sample_rate,
                'file_size': result.file_size
            },

            # 音乐风格
            'music_style': {
                'style': result.music_style,
                'style_cn': result.style_cn,
                'confidence': round(result.style_confidence, 1),
                'mood': result.music_mood
            },

            # DL 评估
            'dl_assessment': {
                'mos_score': round(result.dl_mos_score, 2),
                'mos_normalized': round(result.dl_mos_normalized, 1),
                'method': result.dl_method,
                'confidence': round(result.dl_confidence, 2),
                'available': result.dl_available
            },

            # 五维评分
            'scores': {
                'pitch': result.pitch_score,
                'rhythm': result.rhythm_score,
                'breath': result.breath_score,
                'technique': result.technique_score,
                'artistry': result.artistry_score,
                'total': result.total_score
            },

            # 诊断
            'diagnosis': {
                'pitch': result.pitch_diagnosis,
                'rhythm': result.rhythm_diagnosis,
                'breath': result.breath_diagnosis,
                'technique': result.technique_diagnosis,
                'artistry': result.artistry_diagnosis,
                'critical_issues': result.critical_issues,
                'is_disqualified': result.is_disqualified
            },

            # 总分和等级
            'total_score': result.total_score,
            'level': result.level,
            'stars': result.stars,
            'color': result.color,

            # 建议
            'advice': result.advice,

            # 可视化
            'visualization': result.visualization,

            # 音色
            'timbre': result.timbre,

            # 逐句评分
            'phrases': result.phrases,

            # 波形和音高曲线
            'waveform': result.waveform,
            'pitch_curve': result.pitch_curve,

            # 其他信息
            'volume_info': result.volume_info,
            'pitch_info': result.pitch_info,
            'rhythm_info': result.rhythm_info,
            'emotion_info': result.emotion_info
        }


class ResponseV4Builder(ResponseBuilder):
    """
    v4.0 响应格式

    兼容旧版五维评分
    """

    def build(self, result: AnalysisResult) -> Dict[str, Any]:
        return {
            'success': True,
            'is_voice': result.is_voice,

            # 基本信息
            'basic_info': {
                'filename': result.filename,
                'duration': result.duration,
                'duration_seconds': result.duration_seconds,
                'sample_rate': result.sample_rate,
                'file_size': result.file_size
            },

            # 评分（v4.0 格式）
            'scores': {
                'pitch': result.pitch_score,
                'rhythm': result.rhythm_score,
                'breath': result.breath_score,
                'technique': result.technique_score,
                'artistry': result.artistry_score
            },

            'total_score': result.total_score,
            'level': result.level,
            'stars': result.stars,
            'color': result.color,
            'advice': result.advice
        }


class ResponseV3CompatibilityBuilder(ResponseBuilder):
    """
    v3.0 兼容格式

    适配旧客户端，将新字段映射到旧字段名
    """

    def __init__(self, wrapped: ResponseBuilder):
        self.wrapped = wrapped

    def build(self, result: AnalysisResult) -> Dict[str, Any]:
        # 先构建 v4/v5 格式
        response = self.wrapped.build(result)

        # 添加 v3 兼容字段
        response['scores']['volume'] = result.breath_score  # breath 映射到 volume
        response['scores']['emotion'] = result.artistry_score  # artistry 映射到 emotion
        response['total'] = result.total_score  # total_score 映射到 total

        # v3 评分格式（三维）
        response['v3_scores'] = {
            'volume': result.breath_score,
            'pitch': result.pitch_score,
            'rhythm': result.rhythm_score
        }

        return response


class ResponseV2CompatibilityBuilder(ResponseBuilder):
    """
    v2.0 兼容格式

    最简化的响应格式
    """

    def __init__(self, wrapped: ResponseBuilder):
        self.wrapped = wrapped

    def build(self, result: AnalysisResult) -> Dict[str, Any]:
        # v2 简化格式
        return {
            'success': True,
            'filename': result.filename,
            'total_score': result.total_score,
            'level': result.level,
            'scores': {
                'volume': result.breath_score,
                'pitch': result.pitch_score,
                'rhythm': result.rhythm_score
            },
            'advice': result.advice
        }


class ResponseFactory:
    """
    响应构建器工厂

    根据版本号创建对应的响应构建器
    """

    _builders = {
        '5.0': ResponseV5Builder,
        '4.0': ResponseV4Builder,
        '3.0': ResponseV3CompatibilityBuilder,
        '2.0': ResponseV2CompatibilityBuilder
    }

    @classmethod
    def create(cls, version: str = '5.0') -> ResponseBuilder:
        """
        创建响应构建器

        Args:
            version: API 版本号

        Returns:
            响应构建器实例
        """
        # 获取主版本号
        major_version = version.split('.')[0] + '.0'

        if major_version == '5.0':
            return ResponseV5Builder()
        elif major_version == '4.0':
            return ResponseV4Builder()
        elif major_version == '3.0':
            return ResponseV3CompatibilityBuilder(ResponseV5Builder())
        elif major_version == '2.0':
            return ResponseV2CompatibilityBuilder(ResponseV5Builder())
        else:
            # 默认返回最新版本
            logger.warning(f"Unknown API version: {version}, using latest")
            return ResponseV5Builder()

    @classmethod
    def register_builder(cls, version: str, builder_class: type) -> None:
        """
        注册自定义构建器

        Args:
            version: 版本号
            builder_class: 构建器类
        """
        cls._builders[version] = builder_class
        logger.info(f"Registered response builder for version {version}")


def build_response(
    result: AnalysisResult,
    version: str = '5.0'
) -> Dict[str, Any]:
    """
    便捷函数：构建响应

    Args:
        result: 分析结果
        version: API 版本号

    Returns:
        响应字典
    """
    builder = ResponseFactory.create(version)
    return builder.build(result)


def build_error_response(
    error: str,
    traceback: Optional[str] = None,
    version: str = '5.0'
) -> Dict[str, Any]:
    """
    构建错误响应

    Args:
        error: 错误信息
        traceback: 堆栈跟踪（可选）
        version: API 版本号

    Returns:
        错误响应字典
    """
    response = {
        'success': False,
        'error': error
    }

    if traceback:
        response['traceback'] = traceback

    return response
