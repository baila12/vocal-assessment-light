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
    AudioService, AdviceService, VisualizationService,
    TimbreService, PhraseService, VoiceQualityService
)
from services.score_service import ScoreServiceV4
from services.audio_features_service import AudioFeaturesResult
from services.feature_flags import FeatureFlags
from api.response_builder import AnalysisResult, build_response

logger = logging.getLogger(__name__)

# 初始化服务
audio_service = AudioService(config)
score_service = ScoreServiceV4()
advice_service = AdviceService()
visualization_service = VisualizationService(config)
timbre_service = TimbreService(config.AUDIO_SAMPLE_RATE)
phrase_service = PhraseService(config.AUDIO_SAMPLE_RATE)
voice_quality_service = VoiceQualityService(config.AUDIO_SAMPLE_RATE)

# v5.0 深度学习质量评估
try:
    from services.dl_services.dl_quality_assessor import create_dl_assessor
    dl_assessor = create_dl_assessor()
except Exception as e:
    logger.warning(f"DL assessor init failed: {e}")
    dl_assessor = None

def analyze_and_score(filepath: str, mode: str = 'quick', reference_path: str = None,
                     feature_flags: Optional[FeatureFlags] = None) -> dict:
    """
    分析音频并计算评分

    Args:
        filepath: 音频文件路径
        mode: 评估模式
            - 'quick': 快速评估（跳过逐句评分，简化可视化，约30秒）
            - 'professional': 专业评估（完整分析，约2-5分钟）
        reference_path: 参考音频路径（可选，用于DTW对比评分）
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
            'error': audio_result.error
        }

    # 2. 人声质量检测
    voice_quality = voice_quality_service.analyze(audio_result._audio_data)

    # 如果不是有效人声，返回特殊结果
    if not voice_quality.is_voice:
        return _build_non_voice_result(audio_result, voice_quality)

    # 3. 情绪分析（快速模式使用简化版本）
    emotion_info = analyze_emotion(
        audio_result._audio_data,
        audio_result.sample_rate,
        quick_mode=(mode == 'quick')
    )

    # 4. 评分计算
    advanced_features = audio_result._advanced_features or AudioFeaturesResult()
    style_profile = getattr(audio_result, '_style_profile', None)
    music_mood = getattr(audio_result, '_music_mood', None)

    # v5.0 深度学习质量评估（专业模式才使用）
    if mode == 'professional':
        dl_result = _assess_with_dl(filepath)
    else:
        # 快速模式跳过深度学习评估，节省时间
        dl_result = {'mos_score': 0.0, 'mos_normalized': 0.0, 'method': 'none', 'confidence': 0.0}

    # 快速/专业模式使用相同的评分标准
    # 快速模式的"快"来自跳过的分析步骤（DL评估、逐句评分、可视化等），而非放宽评分标准
    scoring_config = None  # 使用默认配置

    score_result = score_service.calculate(
        features=advanced_features,
        emotion_confidence=emotion_info['confidence'],
        emotions=emotion_info['emotions'],
        voice_quality_score=voice_quality.quality_score,
        style_profile=style_profile,
        music_mood=music_mood,
        dl_mos_score=dl_result['mos_score'],
        dl_mos_normalized=dl_result['mos_normalized'],
        dl_method=dl_result['method'],
        dl_confidence=dl_result['confidence'],
        scoring_config=scoring_config,
        user_filepath=filepath,
        audio_data=audio_result._audio_data,
        f0=audio_result._f0,
        sample_rate=audio_result.sample_rate,
        reference_path=reference_path,
        feature_flags=feature_flags,  # v6.2: 跨维度修正
    )

    # 5. 生成建议
    advice_result = advice_service.generate(score_result)

    # 6. 生成可视化图片（快速模式跳过）
    if mode == 'quick':
        viz_result = None
    else:
        viz_result = visualization_service.generate_feature_plots(
            audio_data=audio_result._audio_data,
            sample_rate=audio_result.sample_rate,
            file_id=Path(filepath).stem
        )

    # 7. 音色分析（快速模式简化）
    if mode == 'quick':
        timbre_result = None
    else:
        timbre_result = timbre_service.analyze(
            audio_data=audio_result._audio_data,
            f0=audio_result._f0
        )

    # 8. 逐句评分（快速模式跳过）
    if mode == 'quick':
        phrase_result = None
    else:
        phrase_result = phrase_service.analyze_phrases(
            audio_data=audio_result._audio_data,
            f0=audio_result._f0
        )

    # 9. 构建响应
    return _build_success_result(
        audio_result, voice_quality, emotion_info, score_result,
        advice_result, viz_result, timbre_result, phrase_result,
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


def _assess_with_dl(filepath: str) -> dict:
    """深度学习质量评估"""
    if not dl_assessor:
        return {'mos_score': 0.0, 'mos_normalized': 0.0, 'method': 'none', 'confidence': 0.0}

    try:
        result = dl_assessor.assess(filepath)
        logger.info(f"[DL] MOS: {result.mos_score:.2f}, Method: {result.method}")
        return {
            'mos_score': result.mos_score,
            'mos_normalized': result.mos_normalized,
            'method': result.method,
            'confidence': result.confidence
        }
    except Exception as e:
        logger.warning(f"DL assessment failed: {e}")
        return {'mos_score': 0.0, 'mos_normalized': 0.0, 'method': 'none', 'confidence': 0.0}


def _build_success_result(
    audio_result, voice_quality, emotion_info, score_result,
    advice_result, viz_result, timbre_result, phrase_result,
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
        dl_mos_score=round(score_result.dl_mos_score, 2),
        dl_mos_normalized=round(score_result.dl_mos_normalized, 1),
        dl_method=score_result.dl_method,
        dl_confidence=round(score_result.dl_confidence, 2),
        dl_available=score_result.dl_method != 'none',
        pitch_score=float(score_result.pitch_score),
        rhythm_score=float(score_result.rhythm_score),
        breath_score=float(score_result.breath_score),
        technique_score=float(score_result.technique_score),
        artistry_score=float(score_result.artistry_score),
        total_score=float(score_result.total_score),
        level=score_result.level,
        stars=score_result.stars,
        color=score_result.color,
        pitch_diagnosis=_build_diagnosis_dict(score_result.pitch_diagnosis, 'mae_cents'),
        rhythm_diagnosis=_build_diagnosis_dict(score_result.rhythm_diagnosis, 'deviation_ratio'),
        breath_diagnosis=_build_breath_diagnosis(score_result.breath_diagnosis),
        technique_diagnosis=_build_technique_diagnosis(score_result.technique_diagnosis),
        artistry_diagnosis=_build_diagnosis_dict(score_result.artistry_diagnosis),
        critical_issues=score_result.critical_issues,
        is_disqualified=score_result.is_disqualified,
        advice=advice_result.advice,
        visualization=_build_viz_dict(viz_result) if viz_result and viz_result.success else None,
        timbre=_build_timbre_dict(timbre_result) if timbre_result and timbre_result.success else None,
        phrases=_build_phrases_dict(phrase_result) if phrase_result and phrase_result.success else None,
        waveform=_waveform_to_dict(audio_result.waveform),
        pitch_curve=_pitch_curve_to_dict(audio_result.pitch_curve),
        volume_info=_to_python_type(audio_result.volume_info),
        pitch_info=_to_python_type(audio_result.pitch_info),
        rhythm_info=_to_python_type(audio_result.rhythm_info),
        emotion_info={
            'dominant': emotion_info['dominant'],
            'scores': {k: round(float(v) * 100, 1) for k, v in emotion_info['emotions'].items()}
        }
    )

    result = build_response(result_dto, version='5.0')
    result['scores']['volume'] = float(score_result.volume)
    result['scores']['emotion'] = float(score_result.artistry_score)
    result['mode'] = mode  # Quick / Professional

    return result


def _build_diagnosis_dict(diagnosis, *extra_fields) -> dict:
    """构建诊断字典"""
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
    """构建气息诊断"""
    return {
        'score': float(diagnosis.score),
        'fluctuation': float(diagnosis.fluctuation),
        'level': diagnosis.level,
        'issues': diagnosis.issues,
        'suggestions': diagnosis.suggestions,
        'positives': diagnosis.positives,  # 正面发现
        'long_note_support': float(diagnosis.long_note_support),
        'dynamic_control': float(diagnosis.dynamic_control),
        'breath_design': float(diagnosis.breath_design),
        'breath_technique': float(diagnosis.breath_technique),
        'is_artistic': diagnosis.is_artistic,
        'has_controlled_breathiness': diagnosis.has_controlled_breathiness
    }


def _build_technique_diagnosis(diagnosis) -> dict:
    """构建技巧诊断"""
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


def _build_timbre_dict(timbre_result) -> dict:
    """构建音色字典"""
    return _to_python_type({
        'brightness': timbre_result.brightness,
        'warmth': timbre_result.warmth,
        'nasality': timbre_result.nasality,
        'breathiness': timbre_result.breathiness,
        'hnr': timbre_result.hnr,
        'vibrato_rate': timbre_result.vibrato_rate,
        'vibrato_extent': timbre_result.vibrato_extent,
        'vibrato_count': timbre_result.vibrato_count,
        'style': timbre_result.timbre_style
    })


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


def analyze_emotion(audio_data, sample_rate: int, quick_mode: bool = False) -> dict:
    """
    分析情绪

    Args:
        audio_data: 音频数据
        sample_rate: 采样率
        quick_mode: 快速模式（跳过DL模型，直接使用启发式方法）

    Returns:
        情绪分析结果
    """
    import librosa

    # 快速模式直接使用启发式方法
    if not quick_mode:
        # 尝试使用模型
        try:
            from services.dl_services.emotion_manager import get_model_manager
            manager = get_model_manager()
            result = manager.analyze_emotion(audio_data, sample_rate)
            return {
                'emotions': result.get('emotions', {}),
                'dominant': result.get('dominant', 'neutral'),
                'confidence': result.get('confidence', 0.5)
            }
        except Exception as e:
            logger.warning(f"Emotion analysis failed: {e}")

    # 启发式方法（快速模式或模型失败时使用）
    rms_feature = librosa.feature.rms(y=audio_data)[0]
    energy_mean = np.mean(rms_feature)
    energy_std = np.std(rms_feature)
    spectral_centroids = librosa.feature.spectral_centroid(y=audio_data, sr=sample_rate)[0]
    brightness = np.mean(spectral_centroids)

    energy_score = min(1.0, energy_mean / 0.1)
    brightness_score = min(1.0, brightness / 3000)
    variation_score = min(1.0, energy_std / 0.05)

    emotions = {
        'happy': energy_score * 0.4 + brightness_score * 0.4 + variation_score * 0.2,
        'sad': (1 - energy_score) * 0.5 + (1 - brightness_score) * 0.3 + (1 - variation_score) * 0.2,
        'angry': energy_score * 0.5 + variation_score * 0.5,
        'neutral': 0.3 + (1 - variation_score) * 0.4,
        'surprised': variation_score * 0.6 + energy_score * 0.4
    }
    dominant = max(emotions, key=emotions.get)

    return {
        'emotions': emotions,
        'dominant': dominant,
        'confidence': emotions[dominant]
    }


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
