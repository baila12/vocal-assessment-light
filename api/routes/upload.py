"""
上传路由
处理文件上传和分析请求
"""
from flask import Blueprint, request, jsonify
from pathlib import Path
from werkzeug.utils import secure_filename
import re
import numpy as np

from config import config
from services import (
    AudioService, AdviceService, VisualizationService,
    SeparationService, TimbreService, PhraseService, ReportService,
    VoiceQualityService
)
from services.score_service import ScoreServiceV4
from services.audio_features_service import AudioFeaturesResult
from repositories import JsonHistoryRepository
from api.errors import ValidationError, NotFoundError, ForbiddenError

upload_bp = Blueprint('upload', __name__)

# 初始化服务（依赖注入）
audio_service = AudioService(config)
score_service = ScoreServiceV4()  # v4.0 评分服务
advice_service = AdviceService()
visualization_service = VisualizationService(config)
separation_service = SeparationService(config.SEPARATED_DIR)
timbre_service = TimbreService(config.AUDIO_SAMPLE_RATE)
phrase_service = PhraseService(config.AUDIO_SAMPLE_RATE)
report_service = ReportService(config.REPORTS_DIR)
voice_quality_service = VoiceQualityService(config.AUDIO_SAMPLE_RATE)
history_repo = JsonHistoryRepository(config.HISTORY_FILE, config.HISTORY_MAX_RECORDS)


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


def sanitize_filename(filename: str) -> str:
    """
    安全处理文件名，保留中文字符但移除危险字符

    secure_filename 会移除中文，所以我们需要自定义处理
    """
    # 分离文件名和扩展名
    name_part = Path(filename).stem
    ext_part = Path(filename).suffix

    # 移除危险字符，但保留中文和其他Unicode字符
    # 只移除路径分隔符和控制字符
    safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name_part)

    # 如果处理后为空，使用时间戳
    if not safe_name:
        import time
        safe_name = f"audio_{int(time.time())}"

    return safe_name + ext_part


@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    """
    上传并分析音频文件

    请求：
        POST /api/upload
        Content-Type: multipart/form-data
        file: 音频文件

    响应：
        {
            "success": true,
            "basic_info": {...},
            "scores": {...},
            ...
        }
    """
    # 参数校验
    if 'file' not in request.files:
        raise ValidationError('没有上传文件')

    file = request.files['file']
    if file.filename == '':
        raise ValidationError('没有选择文件')

    # 扩展名校验
    if not config.is_allowed_extension(file.filename):
        raise ValidationError('不支持的文件格式')

    # 安全处理文件名
    safe_name = sanitize_filename(file.filename)

    # 保存文件
    filepath = config.get_upload_path(safe_name)
    file.save(str(filepath))

    # 分析音频
    try:
        result = _analyze_and_score(str(filepath))
    except Exception as e:
        import traceback
        print(f"[ERROR] Analysis failed: {e}")
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'分析失败: {str(e)}'
        }), 500

    # 保存历史记录
    if result['success']:
        history_record = {
            'filename': result['basic_info']['filename'],
            'filepath': str(filepath),
            'total_score': result['total_score'],
            'scores': result['scores'],
            'level': result['level'],
            'advice': result['advice']
        }
        history_repo.save(history_record)
        result['filepath'] = str(filepath)

    return jsonify(result)


@upload_bp.route('/analyze', methods=['POST'])
def analyze_file():
    """
    分析已存在的音频文件

    请求：
        POST /api/analyze
        Content-Type: application/json
        {"filepath": "/path/to/audio.wav"}

    响应：
        {
            "success": true,
            ...
        }
    """
    filepath = request.json.get('filepath')
    if not filepath:
        raise ValidationError('缺少 filepath 参数')

    # 安全检查：防止路径遍历
    if '..' in filepath or '~' in filepath:
        raise ForbiddenError('无效的文件路径')

    # 防止控制字符注入
    if re.search(r'[\x00-\x1f\x7f]', filepath):
        raise ForbiddenError('无效的文件路径')

    filepath_obj = Path(filepath)

    # 验证文件扩展名
    if filepath_obj.suffix.lower() not in config.ALLOWED_EXTENSIONS:
        raise ForbiddenError('不支持的文件格式')

    # 规范化路径
    try:
        filepath_obj = filepath_obj.resolve()
    except Exception:
        raise ForbiddenError('无效的文件路径')

    # 确保文件在允许的目录内
    upload_dir = config.UPLOAD_FOLDER.resolve()
    test_dir = (config.PROJECT_ROOT / 'test_music').resolve()

    filepath_str = str(filepath_obj)
    if not (
        filepath_str.startswith(str(upload_dir)) or
        filepath_str.startswith(str(test_dir))
    ):
        raise ForbiddenError('无权访问此文件')

    if not filepath_obj.exists() or not filepath_obj.is_file():
        raise NotFoundError('文件不存在')

    result = _analyze_and_score(str(filepath_obj))

    # 保存历史记录
    if result['success']:
        history_record = {
            'filename': result['basic_info']['filename'],
            'filepath': str(filepath_obj),
            'total_score': result['total_score'],
            'scores': result['scores'],
            'level': result['level'],
            'advice': result['advice']
        }
        history_repo.save(history_record)
        result['filepath'] = str(filepath_obj)

    return jsonify(result)


@upload_bp.route('/separate', methods=['POST'])
def separate_audio():
    """
    人声分离

    请求：
        POST /api/separate
        Content-Type: application/json
        {
            "filepath": "/path/to/audio.wav",
            "model": "htdemucs_ft",  // 可选
            "two_stems": "vocals"    // 可选
        }

    响应：
        {
            "success": true,
            "vocals_path": "/static/separated/xxx/vocals.mp3",
            "accompaniment_path": "/static/separated/xxx/no_vocals.mp3",
            "duration": 180.5,
            "model_used": "htdemucs_ft"
        }
    """
    filepath = request.json.get('filepath')
    if not filepath:
        raise ValidationError('缺少 filepath 参数')

    if not Path(filepath).exists():
        raise NotFoundError('文件不存在')

    model = request.json.get('model', 'htdemucs_ft')
    two_stems = request.json.get('two_stems', 'vocals')

    # 执行分离
    result = separation_service.separate(
        audio_path=filepath,
        model=model,
        two_stems=two_stems,
        output_format='mp3'
    )

    return jsonify({
        'success': result.success,
        'vocals_path': result.vocals_path,
        'accompaniment_path': result.accompaniment_path,
        'drums_path': result.drums_path,
        'bass_path': result.bass_path,
        'other_path': result.other_path,
        'duration': result.duration,
        'model_used': result.model_used,
        'error': result.error_message
    })


@upload_bp.route('/separate/models', methods=['GET'])
def get_separation_models():
    """
    获取可用的分离模型列表

    响应：
        {
            "models": [
                {"name": "htdemucs_ft", "description": "快速分离模型", ...},
                ...
            ]
        }
    """
    models = separation_service.get_available_models()
    return jsonify({'models': models})


@upload_bp.route('/report', methods=['POST'])
def generate_report():
    """
    生成评估报告

    请求：
        POST /api/report
        Content-Type: application/json
        {
            "analysis_result": {...},  // 分析结果
            "filename": "song",        // 文件名
            "format": "pdf"            // pdf 或 image
        }

    响应：
        {
            "success": true,
            "pdf_path": "/static/reports/xxx_report.pdf",
            "image_path": null
        }
    """
    data = request.json
    analysis_result = data.get('analysis_result')
    filename = data.get('filename', 'report')
    format_type = data.get('format', 'image')

    if not analysis_result:
        raise ValidationError('缺少 analysis_result 参数')

    if format_type == 'pdf':
        result = report_service.generate_pdf_report(analysis_result, filename)
    else:
        result = report_service.generate_image_report(analysis_result, filename)

    return jsonify({
        'success': result.success,
        'pdf_path': result.pdf_path,
        'image_path': result.image_path,
        'error': result.error_message
    })


@upload_bp.route('/compare', methods=['POST'])
def compare_audio():
    """
    对比分析两个音频文件

    请求：
        POST /api/compare
        Content-Type: application/json
        {
            "standard_filepath": "/path/to/standard.wav",
            "user_filepath": "/path/to/user.wav"
        }

    响应：
        {
            "success": true,
            "standard": {...},  // 标准音频分析结果
            "user": {...},      // 用户音频分析结果
            "comparison": {     // 对比结果
                "pitch_diff": 15.2,
                "volume_diff": 3.5,
                "rhythm_diff": 0.12,
                "breath_diff": 2.1,
                "total_diff": 8.5,
                "pitch_match_rate": 85.3,
                "suggestions": [...]
            }
        }
    """
    standard_filepath = request.json.get('standard_filepath')
    user_filepath = request.json.get('user_filepath')

    if not standard_filepath:
        raise ValidationError('缺少 standard_filepath 参数')
    if not user_filepath:
        raise ValidationError('缺少 user_filepath 参数')

    # 安全检查：防止路径遍历
    for filepath in [standard_filepath, user_filepath]:
        if '..' in filepath or '~' in filepath:
            raise ForbiddenError('无效的文件路径')
        if re.search(r'[\x00-\x1f\x7f]', filepath):
            raise ForbiddenError('无效的文件路径')

    filepath_obj_std = Path(standard_filepath)
    filepath_obj_user = Path(user_filepath)

    # 验证文件扩展名
    for filepath_obj in [filepath_obj_std, filepath_obj_user]:
        if filepath_obj.suffix.lower() not in config.ALLOWED_EXTENSIONS:
            raise ForbiddenError('不支持的文件格式')

    # 规范化路径并验证
    upload_dir = config.UPLOAD_FOLDER.resolve()
    test_dir = (config.PROJECT_ROOT / 'test_music').resolve()

    # Resolve路径
    try:
        filepath_obj_std = filepath_obj_std.resolve()
        filepath_obj_user = filepath_obj_user.resolve()
    except Exception:
        raise ForbiddenError('无效的文件路径')

    # 验证路径在允许的目录内
    for filepath_obj in [filepath_obj_std, filepath_obj_user]:
        filepath_str = str(filepath_obj)
        if not (filepath_str.startswith(str(upload_dir)) or filepath_str.startswith(str(test_dir))):
            raise ForbiddenError('无权访问此文件')

        if not filepath_obj.exists() or not filepath_obj.is_file():
            raise NotFoundError('文件不存在')

    # 分析两个音频
    try:
        standard_result = _analyze_and_score(str(filepath_obj_std))
        user_result = _analyze_and_score(str(filepath_obj_user))
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[ERROR] Compare analysis failed: {e}")
        print(error_trace)
        return jsonify({
            'success': False,
            'error': f'分析失败: {str(e)}',
            'traceback': error_trace
        }), 500

    # 如果任一分析失败，返回错误
    if not standard_result.get('success'):
        return jsonify({'success': False, 'error': '标准音频分析失败'}), 500
    if not user_result.get('success'):
        return jsonify({'success': False, 'error': '用户音频分析失败'}), 500

    # 计算对比结果
    comparison = _calculate_comparison(standard_result, user_result)

    return jsonify({
        'success': True,
        'standard': standard_result,
        'user': user_result,
        'comparison': comparison
    })


def _calculate_comparison(standard: dict, user: dict) -> dict:
    """计算两个音频的对比结果"""
    import numpy as np

    std_scores = standard.get('scores', {})
    user_scores = user.get('scores', {})

    # 各维度分数差距
    pitch_diff = abs(std_scores.get('pitch', 0) - user_scores.get('pitch', 0))
    volume_diff = abs(std_scores.get('volume', 0) - user_scores.get('volume', 0))
    rhythm_diff = abs(std_scores.get('rhythm', 0) - user_scores.get('rhythm', 0))
    breath_diff = abs(std_scores.get('breath', 0) - user_scores.get('breath', 0))
    emotion_diff = abs(std_scores.get('emotion', 0) - user_scores.get('emotion', 0))

    # 综合分数差距
    std_total = standard.get('total_score', 0)
    user_total = user.get('total_score', 0)
    total_diff = abs(std_total - user_total)

    # 音准匹配率
    pitch_match_rate = _calculate_pitch_match_rate(
        standard.get('pitch_curve'),
        user.get('pitch_curve')
    )

    # 生成改进建议
    suggestions = _generate_comparison_suggestions(std_scores, user_scores, std_total, user_total)

    return {
        'pitch_diff': round(pitch_diff, 1),
        'volume_diff': round(volume_diff, 1),
        'rhythm_diff': round(rhythm_diff, 1),
        'breath_diff': round(breath_diff, 1),
        'emotion_diff': round(emotion_diff, 1),
        'total_diff': round(total_diff, 1),
        'std_total': round(std_total, 1),
        'user_total': round(user_total, 1),
        'pitch_match_rate': round(pitch_match_rate, 1),
        'suggestions': suggestions
    }


def _calculate_pitch_match_rate(std_pitch_curve: dict, user_pitch_curve: dict) -> float:
    """计算音准匹配率（0-100）"""
    import numpy as np

    if not std_pitch_curve or not user_pitch_curve:
        return 50.0

    std_freqs = std_pitch_curve.get('frequencies', [])
    user_freqs = user_pitch_curve.get('frequencies', [])

    if not std_freqs or not user_freqs:
        return 50.0

    std_freqs = np.array(std_freqs)
    user_freqs = np.array(user_freqs)

    # 过滤有效频率（人声范围 50-1000 Hz）
    std_valid_mask = (std_freqs > 50) & (std_freqs < 1000)
    user_valid_mask = (user_freqs > 50) & (user_freqs < 1000)

    std_valid = std_freqs[std_valid_mask]
    user_valid = user_freqs[user_valid_mask]

    if len(std_valid) < 10 or len(user_valid) < 10:
        return 50.0

    # 重采样到相同长度进行比较
    min_len = min(len(std_valid), len(user_valid))
    if min_len < 10:
        return 50.0

    # 使用线性插值重采样到相同长度
    std_resampled = np.interp(
        np.linspace(0, len(std_valid) - 1, min_len),
        np.arange(len(std_valid)),
        std_valid
    )
    user_resampled = np.interp(
        np.linspace(0, len(user_valid) - 1, min_len),
        np.arange(len(user_valid)),
        user_valid
    )

    # 计算音分差距: cents = 1200 * log2(freq_ratio)
    with np.errstate(divide='ignore', invalid='ignore'):
        cents_diff = np.abs(1200 * np.log2(user_resampled / std_resampled))
        cents_diff = cents_diff[~np.isinf(cents_diff) & ~np.isnan(cents_diff)]

    if len(cents_diff) == 0:
        return 50.0

    # 音分差距小于50音分视为匹配
    match_threshold = 50
    matched = np.sum(cents_diff < match_threshold)
    match_rate = (matched / len(cents_diff)) * 100

    return float(match_rate)


def _generate_comparison_suggestions(
    std_scores: dict,
    user_scores: dict,
    std_total: float,
    user_total: float
) -> list:
    """生成对比改进建议"""
    suggestions = []

    # 音准建议
    pitch_diff = std_scores.get('pitch', 0) - user_scores.get('pitch', 0)
    if pitch_diff > 10:
        suggestions.append({
            'dimension': '音准',
            'gap': round(pitch_diff, 1),
            'suggestion': '音准差距较大，建议使用钢琴或调音器练习音阶，特别注意半音的准确度。'
        })
    elif pitch_diff > 5:
        suggestions.append({
            'dimension': '音准',
            'gap': round(pitch_diff, 1),
            'suggestion': '音准略有偏差，注意长音的稳定性和尾音的收束。'
        })

    # 音量建议
    volume_diff = std_scores.get('volume', 0) - user_scores.get('volume', 0)
    if volume_diff > 10:
        suggestions.append({
            'dimension': '音量',
            'gap': round(volume_diff, 1),
            'suggestion': '音量控制差距较大，建议练习气息支持，保持稳定的音量输出。'
        })
    elif volume_diff > 5:
        suggestions.append({
            'dimension': '音量',
            'gap': round(volume_diff, 1),
            'suggestion': '音量控制略有不足，注意歌曲高潮和过渡段的音量变化。'
        })

    # 节奏建议
    rhythm_diff = std_scores.get('rhythm', 0) - user_scores.get('rhythm', 0)
    if rhythm_diff > 10:
        suggestions.append({
            'dimension': '节奏',
            'gap': round(rhythm_diff, 1),
            'suggestion': '节奏稳定性差距较大，建议跟着节拍器练习，注意不要抢拍或拖拍。'
        })
    elif rhythm_diff > 5:
        suggestions.append({
            'dimension': '节奏',
            'gap': round(rhythm_diff, 1),
            'suggestion': '节奏略有波动，注意休止符的时值和切分音的准确性。'
        })

    # 气息建议
    breath_diff = std_scores.get('breath', 0) - user_scores.get('breath', 0)
    if breath_diff > 10:
        suggestions.append({
            'dimension': '气息',
            'gap': round(breath_diff, 1),
            'suggestion': '气息控制差距较大，建议练习腹式呼吸，增强肺活量和气息控制能力。'
        })
    elif breath_diff > 5:
        suggestions.append({
            'dimension': '气息',
            'gap': round(breath_diff, 1),
            'suggestion': '气息控制略有不足，注意换气点的选择和气息的分配。'
        })

    # 情绪建议
    emotion_diff = std_scores.get('emotion', 0) - user_scores.get('emotion', 0)
    if emotion_diff > 10:
        suggestions.append({
            'dimension': '情感',
            'gap': round(emotion_diff, 1),
            'suggestion': '情感表达差距较大，建议理解歌词含义，用声音传达歌曲的情感起伏。'
        })
    elif emotion_diff > 5:
        suggestions.append({
            'dimension': '情感',
            'gap': round(emotion_diff, 1),
            'suggestion': '情感表达略有不足，注意歌曲的强弱对比和情感转折。'
        })

    # 综合建议
    total_diff = std_total - user_total
    if total_diff > 15:
        suggestions.append({
            'dimension': '综合',
            'gap': round(total_diff, 1),
            'suggestion': f'与标准音频相比，整体差距{round(total_diff, 1)}分。建议从音准和节奏入手，逐步提升各项技能。'
        })
    elif total_diff > 5:
        suggestions.append({
            'dimension': '综合',
            'gap': round(total_diff, 1),
            'suggestion': f'整体表现接近标准，差距仅{round(total_diff, 1)}分。继续练习，精益求精！'
        })
    else:
        suggestions.append({
            'dimension': '综合',
            'gap': round(total_diff, 1),
            'suggestion': '表现优秀！与标准音频非常接近，保持当前状态，可以尝试更高难度的歌曲。'
        })

    return suggestions


def _analyze_and_score(filepath: str) -> dict:
    """
    分析音频并计算评分

    Args:
        filepath: 音频文件路径

    Returns:
        分析结果字典
    """
    # 1. 音频分析
    audio_result = audio_service.analyze(filepath)

    if not audio_result.success:
        return {
            'success': False,
            'error': audio_result.error,
            'traceback': audio_result.traceback
        }

    # 2. 人声质量检测（核心：避免对非人声给出高分）
    voice_quality = voice_quality_service.analyze(audio_result._audio_data)

    # 如果不是有效人声，返回特殊结果
    if not voice_quality.is_voice:
        return {
            'success': True,
            'is_voice': False,
            'voice_quality': {
                'is_voice': False,
                'voice_ratio': round(voice_quality.voice_ratio * 100, 1),
                'quality_score': round(voice_quality.quality_score, 1),
                'silence_ratio': round(voice_quality.silence_ratio * 100, 1),
                'harmonic_ratio': round(voice_quality.harmonic_ratio * 100, 1),
                'warnings': voice_quality.warnings,
                'suggestions': voice_quality.suggestions
            },
            'basic_info': {
                'filename': audio_result.filename,
                'duration': f"{int(audio_result.duration // 60):02d}:{int(audio_result.duration % 60):02d}",
                'duration_seconds': audio_result.duration,
                'sample_rate': audio_result.sample_rate,
                'file_size': f"{audio_result.file_size:.2f}MB"
            },
            'total_score': 0,
            'level': '无效',
            'stars': '☆☆☆☆☆',
            'color': '#888888',
            'scores': {
                'volume': max(20, voice_quality.quality_score * 0.3),
                'pitch': max(10, voice_quality.voice_ratio * 30),
                'rhythm': 20,
                'breath': 20,
                'emotion': 20
            },
            'advice': voice_quality.suggestions
        }

    # 3. 情绪分析（使用模型或启发式方法）
    emotion_info = _analyze_emotion(
        audio_result._audio_data,
        audio_result.sample_rate
    )

    # 4. 评分计算 v4.0（使用高级特征）
    # 获取高级特征提取结果
    advanced_features = audio_result._advanced_features
    if advanced_features is None:
        # 如果未提取，使用默认值
        advanced_features = AudioFeaturesResult()

    score_result = score_service.calculate(
        features=advanced_features,
        emotion_confidence=emotion_info['confidence'],
        emotions=emotion_info['emotions'],
        voice_quality_score=voice_quality.quality_score
    )

    # 5. 生成建议
    advice_result = advice_service.generate(score_result)

    # 6. 生成可视化图片
    viz_result = visualization_service.generate_feature_plots(
        audio_data=audio_result._audio_data,
        sample_rate=audio_result.sample_rate,
        file_id=Path(filepath).stem
    )

    # 7. 音色分析
    timbre_result = timbre_service.analyze(
        audio_data=audio_result._audio_data,
        f0=audio_result._f0
    )

    # 8. 逐句评分
    phrase_result = phrase_service.analyze_phrases(
        audio_data=audio_result._audio_data,
        f0=audio_result._f0
    )

    # 9. 构建响应
    result = {
        'success': True,
        'is_voice': True,
        'voice_quality': {
            'is_voice': True,
            'voice_ratio': round(voice_quality.voice_ratio * 100, 1),
            'quality_score': round(voice_quality.quality_score, 1),
            'silence_ratio': round(voice_quality.silence_ratio * 100, 1),
            'harmonic_ratio': round(voice_quality.harmonic_ratio * 100, 1)
        },
        'basic_info': {
            'filename': audio_result.filename,
            'duration': f"{int(audio_result.duration // 60):02d}:{int(audio_result.duration % 60):02d}",
            'duration_seconds': float(audio_result.duration),
            'sample_rate': int(audio_result.sample_rate),
            'file_size': f"{audio_result.file_size:.2f}MB"
        },
        'volume_info': _to_python_type(audio_result.volume_info),
        'pitch_info': _to_python_type(audio_result.pitch_info),
        'rhythm_info': _to_python_type(audio_result.rhythm_info),
        'emotion_info': {
            'dominant': emotion_info['dominant'],
            'scores': {k: round(v * 100, 1) for k, v in emotion_info['emotions'].items()}
        },
        'scores': {
            # v4.0 新维度
            'pitch': float(score_result.pitch_score),
            'rhythm': float(score_result.rhythm_score),
            'breath': float(score_result.breath_score),
            'technique': float(score_result.technique_score),
            'artistry': float(score_result.artistry_score),
            # 兼容旧接口
            'volume': float(score_result.breath_score),  # 映射
            'emotion': float(score_result.artistry_score)  # 映射
        },
        'diagnosis': {
            'pitch': {
                'score': float(score_result.pitch_diagnosis.score),
                'mae_cents': float(score_result.pitch_diagnosis.mae_cents),
                'level': score_result.pitch_diagnosis.level,
                'issues': score_result.pitch_diagnosis.issues,
                'suggestions': score_result.pitch_diagnosis.suggestions
            },
            'rhythm': {
                'score': float(score_result.rhythm_diagnosis.score),
                'deviation_ratio': float(score_result.rhythm_diagnosis.deviation_ratio),
                'level': score_result.rhythm_diagnosis.level,
                'issues': score_result.rhythm_diagnosis.issues,
                'suggestions': score_result.rhythm_diagnosis.suggestions
            },
            'breath': {
                'score': float(score_result.breath_diagnosis.score),
                'fluctuation': float(score_result.breath_diagnosis.fluctuation),
                'level': score_result.breath_diagnosis.level,
                'issues': score_result.breath_diagnosis.issues,
                'suggestions': score_result.breath_diagnosis.suggestions,
                # v4.1 新增：细分维度
                'long_note_support': float(score_result.breath_diagnosis.long_note_support),
                'dynamic_control': float(score_result.breath_diagnosis.dynamic_control),
                'breath_design': float(score_result.breath_diagnosis.breath_design),
                'breath_technique': float(score_result.breath_diagnosis.breath_technique),
                'is_artistic': score_result.breath_diagnosis.is_artistic,
                'has_controlled_breathiness': score_result.breath_diagnosis.has_controlled_breathiness
            },
            'technique': {
                'score': float(score_result.technique_diagnosis.score),
                'hnr': float(score_result.technique_diagnosis.hnr),
                'cpp': float(score_result.technique_diagnosis.cpp),
                'level': score_result.technique_diagnosis.level,
                'issues': score_result.technique_diagnosis.issues,
                'suggestions': score_result.technique_diagnosis.suggestions
            },
            'artistry': {
                'score': float(score_result.artistry_diagnosis.score),
                'level': score_result.artistry_diagnosis.level,
                'issues': score_result.artistry_diagnosis.issues,
                'suggestions': score_result.artistry_diagnosis.suggestions
            },
            'critical_issues': score_result.critical_issues,
            'is_disqualified': score_result.is_disqualified
        },
        'total_score': float(score_result.total_score),
        'level': score_result.level,
        'stars': score_result.stars,
        'color': score_result.color,
        'advice': advice_result.advice,
        'waveform': _waveform_to_dict(audio_result.waveform),
        'pitch_curve': _pitch_curve_to_dict(audio_result.pitch_curve),
        'visualization': {
            'spectrogram': viz_result.spectrogram_path,
            'pitch_trajectory': viz_result.pitch_trajectory_path,
            'energy': viz_result.energy_path,
            'combined': viz_result.combined_path
        } if viz_result.success else None,
        'timbre': _to_python_type({
            'brightness': timbre_result.brightness,
            'warmth': timbre_result.warmth,
            'nasality': timbre_result.nasality,
            'breathiness': timbre_result.breathiness,
            'hnr': timbre_result.hnr,
            'vibrato_rate': timbre_result.vibrato_rate,
            'vibrato_extent': timbre_result.vibrato_extent,
            'vibrato_count': timbre_result.vibrato_count,
            'style': timbre_result.timbre_style
        }) if timbre_result.success else None,
        'phrases': _to_python_type({
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
        }) if phrase_result.success else None
    }

    return result


def _analyze_emotion(audio_data, sample_rate: int) -> dict:
    """
    分析情绪

    优先使用深度学习模型，失败则使用启发式方法
    """
    import librosa
    import numpy as np

    # 尝试使用模型
    try:
        from model_manager import get_model_manager
        manager = get_model_manager()
        result = manager.analyze_emotion(audio_data, sample_rate)
        return {
            'emotions': result.get('emotions', {}),
            'dominant': result.get('dominant', 'neutral'),
            'confidence': result.get('confidence', 0.5)
        }
    except Exception as e:
        print(f"[ModelManager] Emotion analysis failed: {e}")

    # 启发式方法
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


def _waveform_to_dict(waveform):
    """将波形 DTO 转换为字典"""
    if waveform is None:
        return None
    return {
        'times': waveform.times,
        'amplitudes': waveform.amplitudes
    }


def _pitch_curve_to_dict(pitch_curve):
    """将音高曲线 DTO 转换为字典"""
    if pitch_curve is None:
        return None
    return {
        'times': pitch_curve.times,
        'frequencies': pitch_curve.frequencies,
        'confidence': pitch_curve.confidence,
        'error': pitch_curve.error
    }
