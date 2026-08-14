"""
音频分析业务逻辑

处理音频分析、评分计算、结果构建
"""
from typing import Optional
from pathlib import Path
import numpy as np
import logging

from config import config
from services import (
    AudioService, VisualizationService,
    PhraseService, VoiceQualityService
)
from services.feature_flags import FeatureFlags
from api.response_builder import AnalysisResult, build_response

# v7.1.4 DDD 特征提取 + 评分编排器 (唯一路径 — V4 回退已移除)
# v7.16 P2-15 Phase 0b: 移除 EventBus 历史自动保存订阅 — 历史由路由 _save_history
# 单一负责 (双写 bug 修复: 旧代码每次评分写无 analysis_id 的垃圾记录挤占历史槽位)。
from backend.application.assessment.scoring_orchestrator import ScoringOrchestrator
from backend.application.assessment.ddd_feature_orchestrator import (
    DddFeatureExtractionOrchestrator,
)
from backend.application.assessment.advice_generator import AdviceGenerator
from backend.domain.assessment.feature_flags import DimensionFlags

ddd_orchestrator = ScoringOrchestrator()
# v7.7: 启用 audiofeat CPPS/GNE/HNR_praat 增强 (所有消费者有安全零值回退)
# v7.16 P2-15 Phase 5.2: 作为 feature_flags=None 时的模块级默认 (等价 to_dimension_flags(FeatureFlags())),
# 生产传入 for_quick/for_professional 时经 _resolve_ddd_extractor 按运行时 flag 对齐。
_ddd_feature_extractor = DddFeatureExtractionOrchestrator(
    flags=DimensionFlags(enable_audiofeat=True)
)

logger = logging.getLogger(__name__)


def _resolve_ddd_extractor(feature_flags=None):
    """feature_flags → DDD 特征提取器 (v7.16 P2-15 Phase 5.2 flag 对齐)。

    None → 模块级默认 (FeatureFlags() 全真, 数值不变, 真实音频回归走此路径)。
    显式 flags → 经 flag_bridge 转 DimensionFlags 构造, 生产 quick/pro 按 mode 对齐。
    """
    if feature_flags is None:
        return _ddd_feature_extractor
    from backend.shared.flag_bridge import to_dimension_flags
    return DddFeatureExtractionOrchestrator(flags=to_dimension_flags(feature_flags))


# 初始化服务
audio_service = AudioService(config)
# v7.16 P2-15 Phase 1: 建议生成迁入 DDD application 层 (AdviceGenerator)
advice_generator = AdviceGenerator()
visualization_service = VisualizationService(config)
phrase_service = PhraseService(config.AUDIO_SAMPLE_RATE)
voice_quality_service = VoiceQualityService(config.AUDIO_SAMPLE_RATE)

def analyze_and_score(filepath: str, mode: str = 'quick',
                     feature_flags: Optional[FeatureFlags] = None) -> dict:
    """
    分析音频并计算评分

    Args:
        filepath: 音频文件路径
        mode: 评估模式
            - 'quick': 快速评估（跳过逐句评分，简化可视化，约30秒）
            - 'professional': 专业评估（完整分析，约2-5分钟）
        feature_flags: FeatureFlags 功能开关（可选，默认全部关闭）

    Returns:
        分析结果字典
    """
    # 1. 音频分析（快速模式跳过耗时DL分析）
    audio_result = audio_service.analyze(
        filepath, quick_mode=(mode == 'quick'), feature_flags=feature_flags
    )

    if not audio_result.success:
        logger.error(f"Audio analysis failed: {audio_result.error}")
        return {
            'success': False,
            'error': '音频分析失败，请稍后重试'
        }

    # 2. 人声质量检测
    voice_quality = voice_quality_service.analyze(audio_result._audio_data)

    # 如果不是有效人声，返回特殊结果
    if not voice_quality.is_voice:
        return _build_non_voice_result(audio_result, voice_quality)

    # 3. 评分计算 — v7.1.4 DDD 原生路径 (唯一路径)
    #    (v7.16 Phase 5.1: 死 analyze_emotion 启发式已删 — emotion 信号由 artistry_score 提供)
    y = audio_result._audio_data
    sr = audio_result.sample_rate
    f0 = audio_result._f0
    # 从 F0 生成 voiced_flags: 非 NaN = voiced
    if f0 is not None and len(f0) > 0:
        voiced_flags = ~np.isnan(f0)
    else:
        voiced_flags = None
    is_clean = getattr(audio_result, '_used_separation', False)

    # v7.17: 节拍锚定节奏 — pro 分离模式加载伴奏轨 (含节拍基准), 修复分离后 rhythm 崩坍
    accompaniment = None
    accompaniment_sr = None
    if is_clean and mode != 'quick':
        accomp_path = getattr(audio_result, '_accompaniment_path', None)
        if accomp_path:
            try:
                import librosa
                accompaniment, accompaniment_sr = librosa.load(accomp_path, sr=22050, mono=True)
            except Exception:
                logger.warning("伴奏轨加载失败, 节奏回退混音路径", exc_info=True)
                accompaniment = None

    ddd_features = _resolve_ddd_extractor(feature_flags).extract_all(
        y, sr, f0, voiced_flags, is_clean_vocal=is_clean,
        accompaniment=accompaniment, accompaniment_sr=accompaniment_sr,
    )
    score_result = ddd_orchestrator.calculate_ddd(
        pitch=ddd_features.pitch,
        rhythm=ddd_features.rhythm,
        breath=ddd_features.breath,
        technique=ddd_features.technique,
        muscle=ddd_features.muscle,
        artistry=ddd_features.artistry,
        timbre=ddd_features.timbre,
        audiofeat=ddd_features.audiofeat,  # v7.3: audiofeat 增强
        voice_quality_score=voice_quality.quality_score,
    )

    # 5. 生成建议 (v7.16 P2-15 Phase 1: DDD AdviceGenerator)
    advice_result = advice_generator.generate(score_result)

    # 6. 生成可视化图片（快速模式跳过）
    if mode == 'quick':
        viz_result = None
    else:
        viz_result = visualization_service.generate_feature_plots(
            audio_data=audio_result._audio_data,
            sample_rate=audio_result.sample_rate,
            file_id=Path(filepath).stem
        )

    # 7. 逐句评分（快速模式跳过） — 音色展示由 score_result['timbre_detail'] 组装 (v7.16 Phase 2)
    if mode == 'quick':
        phrase_result = None
    else:
        phrase_result = phrase_service.analyze_phrases(
            audio_data=audio_result._audio_data,
            f0=audio_result._f0
        )

    # 8. 构建响应
    return _build_success_result(
        audio_result, voice_quality, score_result,
        advice_result, viz_result, phrase_result,
        mode=mode
    )


def _build_non_voice_result(audio_result, voice_quality) -> dict:
    """
    构建非人声结果

    v5.12 修改: 非人声不返回假分数。所有维度返回 0 分，
    由前端判断 is_voice=false 后显示专用提示而非雷达图。
    """
    result_dto = AnalysisResult(
        filename=audio_result.filename,
        duration=f"{int(audio_result.duration // 60):02d}:{int(audio_result.duration % 60):02d}",
        duration_seconds=audio_result.duration,
        sample_rate=audio_result.sample_rate,
        file_size=f"{audio_result.file_size:.2f}MB",
        is_voice=False,
        voice_ratio=round(voice_quality.voice_ratio * 100, 1),
        voice_quality_score=round(voice_quality.quality_score, 1),
        silence_ratio=round(voice_quality.silence_ratio * 100, 1),
        harmonic_ratio=round(voice_quality.harmonic_ratio * 100, 1),
        total_score=0,
        level='无法评分',
        stars='————',
        color='#888888',
        breath_score=0.0,
        pitch_score=0.0,
        rhythm_score=0.0,
        technique_score=0.0,
        artistry_score=0.0,
        advice=['未检测到有效人声，请确认上传的是歌唱音频（非纯音乐或白噪声）']
    )
    result = build_response(result_dto, version='5.12')
    result['voice_quality']['warnings'] = voice_quality.warnings if hasattr(voice_quality, 'warnings') else []
    result['voice_quality']['suggestions'] = voice_quality.suggestions if hasattr(voice_quality, 'suggestions') else []
    result['scores']['volume'] = 0.0
    result['scores']['emotion'] = 0.0
    result['is_voice'] = False
    result['warning'] = '未检测到有效人声，请确认上传的是歌唱音频（非纯音乐或白噪声）'
    return result


def _s(obj, key, default=0.0):
    """统一访问 dict 属性 — v7.1.4 DDD orchestrator 产物"""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _build_success_result(
    audio_result, voice_quality, score_result,
    advice_result, viz_result, phrase_result,
    mode: str = 'professional'
) -> dict:
    """构建成功结果

    Args:
        mode: 评估模式
            - 'quick': 快速评估（简化的结果）
            - 'professional': 专业评估（完整结果）
    """
    style_profile = getattr(audio_result, '_style_profile', None)

    result_dto = AnalysisResult(
        filename=audio_result.filename,
        duration=f"{int(audio_result.duration // 60):02d}:{int(audio_result.duration % 60):02d}",
        duration_seconds=float(audio_result.duration),
        sample_rate=int(audio_result.sample_rate),
        file_size=f"{audio_result.file_size:.2f}MB",
        is_voice=True,
        voice_ratio=round(voice_quality.voice_ratio * 100, 1),
        voice_quality_score=round(voice_quality.quality_score, 1),
        silence_ratio=round(voice_quality.silence_ratio * 100, 1),
        harmonic_ratio=round(voice_quality.harmonic_ratio * 100, 1),
        music_style=audio_result._music_style or 'unknown',
        style_cn=style_profile.style_cn if style_profile else '未知',
        style_confidence=round(audio_result._style_confidence * 100, 1) if audio_result._style_confidence else 0,
        music_mood=audio_result._music_mood or 'unknown',
        pitch_score=float(_s(score_result, 'pitch_score')),
        rhythm_score=float(_s(score_result, 'rhythm_score')),
        breath_score=float(_s(score_result, 'breath_score')),
        technique_score=float(_s(score_result, 'technique_score')),
        muscle_strength_score=float(_s(score_result, 'muscle_strength_score')),
        artistry_score=float(_s(score_result, 'artistry_score')),
        total_score=float(_s(score_result, 'total_score')),
        timbre_adjustment=float(_s(score_result, 'timbre_adjustment')),
        heuristic_dimensions=_s(score_result, 'heuristic_dimensions', []),
        normalization_applied=True,  # DDD + Legacy 都做归一化
        recording_condition_note=(
            '评分假设录音条件为标准人声拾音距离，已进行响度归一化减少录音条件差异。'
            'max_db_level 等绝对值指标受归一化影响，不作为绝对声压级测量。'
        ),
        level=str(_s(score_result, 'level', '')),
        stars=str(_s(score_result, 'stars', '')),
        color=str(_s(score_result, 'color', '')),
        pitch_diagnosis=_build_diagnosis_dict(_s(score_result, 'pitch_diagnosis', {}), 'mae_cents'),
        rhythm_diagnosis=_build_diagnosis_dict(_s(score_result, 'rhythm_diagnosis', {}), 'deviation_ratio'),
        breath_diagnosis=_build_breath_diagnosis(_s(score_result, 'breath_diagnosis', {})),
        technique_diagnosis=_build_technique_diagnosis(_s(score_result, 'technique_diagnosis', {})),
        artistry_diagnosis=_build_diagnosis_dict(_s(score_result, 'artistry_diagnosis', {})),
        critical_issues=_s(score_result, 'critical_issues', []),
        is_disqualified=_s(score_result, 'is_disqualified', False),
        advice=advice_result.advice,
        visualization=_build_viz_dict(viz_result) if viz_result and viz_result.success else None,
        timbre=_build_timbre_dict(score_result) if mode != 'quick' else None,
        phrases=_build_phrases_dict(phrase_result) if phrase_result and phrase_result.success else None,
        waveform=_waveform_to_dict(audio_result.waveform),
        pitch_curve=_pitch_curve_to_dict(audio_result.pitch_curve),
        volume_info=_to_python_type(audio_result.volume_info),
        pitch_info=_to_python_type(audio_result.pitch_info),
        rhythm_info=_to_python_type(audio_result.rhythm_info),
    )

    result = build_response(result_dto, version='5.0')
    result['scores']['volume'] = float(_s(score_result, 'volume'))
    result['scores']['emotion'] = float(_s(score_result, 'artistry_score'))
    result['scores']['muscle_strength'] = float(_s(score_result, 'muscle_strength_score'))
    result['timbre_adjustment'] = float(_s(score_result, 'timbre_adjustment'))
    result['heuristic_dimensions'] = _s(score_result, 'heuristic_dimensions', [])
    # v7.14 审查 6.3: 评分失败 fallback 告警透传 (假 50.0 可辨识)
    result['scoring_warnings'] = _s(score_result, 'scoring_warnings', [])
    result['mode'] = mode  # Quick / Professional

    # v7.1: analysis_id 始终生成 (API 层 + 业务层双重保障)
    import uuid
    if not result.get('analysis_id'):
        result['analysis_id'] = str(uuid.uuid4())[:12]

    return result


def _build_diagnosis_dict(diagnosis, *extra_fields) -> dict:
    """构建诊断字典 (兼容 dict 和 dataclass)"""
    if isinstance(diagnosis, dict):
        result = {
            'score': float(diagnosis.get('score', 0.0)),
            'level': diagnosis.get('level', ''),
            'issues': diagnosis.get('issues', []),
            'suggestions': diagnosis.get('suggestions', [])
        }
        for field in extra_fields:
            if field in diagnosis:
                result[field] = float(diagnosis[field])
        return result
    result = {
        'score': float(diagnosis.score),
        'level': diagnosis.level,
        'issues': diagnosis.issues,
        'suggestions': diagnosis.suggestions
    }
    for field in extra_fields:
        if hasattr(diagnosis, field):
            result[field] = float(getattr(diagnosis, field))
    return result


def _build_breath_diagnosis(diagnosis) -> dict:
    """构建气息诊断 (兼容 dict 和 dataclass)"""
    if isinstance(diagnosis, dict):
        return {
            'score': float(diagnosis.get('score', 0.0)),
            'fluctuation': float(diagnosis.get('fluctuation', 0.0)),
            'level': diagnosis.get('level', ''),
            'issues': diagnosis.get('issues', []),
            'suggestions': diagnosis.get('suggestions', []),
            'positives': diagnosis.get('positives', []),
            'long_note_support': float(diagnosis.get('long_note_support', 0.0)),
            'dynamic_control': float(diagnosis.get('dynamic_control', 0.0)),
            'breath_design': float(diagnosis.get('breath_design', 0.0)),
            'breath_technique': float(diagnosis.get('breath_technique', 0.0)),
            'is_artistic': diagnosis.get('is_artistic', False),
            'has_controlled_breathiness': diagnosis.get('has_controlled_breathiness', False)
        }
    return {
        'score': float(diagnosis.score),
        'fluctuation': float(diagnosis.fluctuation),
        'level': diagnosis.level,
        'issues': diagnosis.issues,
        'suggestions': diagnosis.suggestions,
        'positives': diagnosis.positives,
        'long_note_support': float(diagnosis.long_note_support),
        'dynamic_control': float(diagnosis.dynamic_control),
        'breath_design': float(diagnosis.breath_design),
        'breath_technique': float(diagnosis.breath_technique),
        'is_artistic': diagnosis.is_artistic,
        'has_controlled_breathiness': diagnosis.has_controlled_breathiness
    }


def _build_technique_diagnosis(diagnosis) -> dict:
    """构建技巧诊断 (兼容 dict 和 dataclass)"""
    if isinstance(diagnosis, dict):
        return {
            'score': float(diagnosis.get('score', 0.0)),
            'level': diagnosis.get('level', ''),
            'issues': diagnosis.get('issues', []),
            'suggestions': diagnosis.get('suggestions', []),
            'hnr': float(diagnosis.get('hnr', 0.0)),
            'cpp': float(diagnosis.get('cpp', 0.0)),
            'vibrato_quality': float(diagnosis.get('vibrato_quality', 0.0)),
            'is_mixed_audio': diagnosis.get('is_mixed_audio', False)
        }
    return {
        'score': float(diagnosis.score),
        'level': diagnosis.level,
        'issues': diagnosis.issues,
        'suggestions': diagnosis.suggestions,
        'hnr': float(diagnosis.hnr),
        'cpp': float(diagnosis.cpp),
        'vibrato_quality': float(diagnosis.vibrato_quality),
        'is_mixed_audio': diagnosis.is_mixed_audio  # 是否混合音频
    }


def _build_viz_dict(viz_result) -> dict:
    """构建可视化字典"""
    return {
        'spectrogram': viz_result.spectrogram_path,
        'pitch_trajectory': viz_result.pitch_trajectory_path,
        'energy': viz_result.energy_path,
        'combined': viz_result.combined_path
    }


def _build_timbre_dict(score_result) -> dict:
    """从 DDD score_result['timbre_detail'] 构建音色字典 (v7.16 P2-15 Phase 2)。

    键契约与旧 TimbreResult 一致 (brightness/warmth/nasality/breathiness/hnr/
    vibrato_rate/vibrato_extent/vibrato_count/style)。
    """
    return _to_python_type(score_result.get('timbre_detail', {}))


def _build_phrases_dict(phrase_result) -> dict:
    """构建逐句评分字典"""
    return _to_python_type({
        'total': phrase_result.total_phrases,
        'avg_score': phrase_result.avg_score,
        'best_phrase_id': phrase_result.best_phrase_id,
        'worst_phrase_id': phrase_result.worst_phrase_id,
        'items': [
            {
                'id': p.phrase_id,
                'start': p.start_time,
                'end': p.end_time,
                'duration': p.duration,
                'scores': {
                    'volume': float(p.volume),
                    'pitch': float(p.pitch),
                    'rhythm': float(p.rhythm),
                    'breath': float(p.breath),
                    'emotion': float(p.emotion)
                },
                'total': float(p.total),
                'level': p.level,
                'advice': p.advice,
                'note_range': list(p.note_range)
            } for p in phrase_result.phrases
        ]
    })


def _to_python_type(value):
    """将 numpy 类型转换为 Python 原生类型"""
    if isinstance(value, (np.integer, np.int64, np.int32)):
        return int(value)
    elif isinstance(value, (np.floating, np.float64, np.float32)):
        return float(value)
    elif isinstance(value, np.ndarray):
        return value.tolist()
    elif isinstance(value, dict):
        return {k: _to_python_type(v) for k, v in value.items()}
    elif isinstance(value, (list, tuple)):
        return [_to_python_type(v) for v in value]
    return value


def _waveform_to_dict(waveform):
    """将波形 DTO 转换为字典"""
    if waveform is None:
        return None
    return {
        'times': _to_python_type(waveform.times),
        'amplitudes': _to_python_type(waveform.amplitudes)
    }


def _pitch_curve_to_dict(pitch_curve):
    """将音高曲线 DTO 转换为字典"""
    if pitch_curve is None:
        return None
    return {
        'times': _to_python_type(pitch_curve.times),
        'frequencies': _to_python_type(pitch_curve.frequencies),
        'confidence': _to_python_type(pitch_curve.confidence),
        'error': _to_python_type(pitch_curve.error)
    }
