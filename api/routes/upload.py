"""
上传路由 v2.0 - 模块化重构

路由层仅处理请求/响应，业务逻辑委托给 business 模块
"""
from flask import Blueprint, request, jsonify
from pathlib import Path
import re
import logging

from config import config
from services import SeparationService, ReportService
from repositories import JsonHistoryRepository
from api.errors import ValidationError, NotFoundError, ForbiddenError
from api.business import analyze_and_score, calculate_comparison

logger = logging.getLogger(__name__)

upload_bp = Blueprint('upload', __name__)

# 初始化服务
separation_service = SeparationService(config.SEPARATED_DIR)
report_service = ReportService(config.REPORTS_DIR)
history_repo = JsonHistoryRepository(config.HISTORY_FILE, config.HISTORY_MAX_RECORDS)


def sanitize_filename(filename: str) -> str:
    """安全处理文件名，保留中文字符但移除危险字符"""
    name_part = Path(filename).stem
    ext_part = Path(filename).suffix
    safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', name_part)
    if not safe_name:
        import time
        safe_name = f"audio_{int(time.time())}"
    return safe_name + ext_part


def validate_filepath(filepath: str) -> Path:
    """验证文件路径安全性"""
    if '..' in filepath or '~' in filepath:
        raise ForbiddenError('无效的文件路径')
    if re.search(r'[\x00-\x1f\x7f]', filepath):
        raise ForbiddenError('无效的文件路径')

    filepath_obj = Path(filepath)
    if filepath_obj.suffix.lower() not in config.ALLOWED_EXTENSIONS:
        raise ForbiddenError('不支持的文件格式')

    try:
        filepath_obj = filepath_obj.resolve()
    except Exception:
        raise ForbiddenError('无效的文件路径')

    upload_dir = config.UPLOAD_FOLDER.resolve()
    test_dir = (config.PROJECT_ROOT / 'tests' / 'test_data' / 'audio').resolve()
    filepath_str = str(filepath_obj)

    if not (filepath_str.startswith(str(upload_dir)) or filepath_str.startswith(str(test_dir))):
        raise ForbiddenError('无权访问此文件')
    if not filepath_obj.exists() or not filepath_obj.is_file():
        raise NotFoundError('文件不存在')

    return filepath_obj


@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    """上传并分析音频文件

    支持评估模式:
    - quick: 快速评估（跳过逐句评分，简化可视化）
    - professional: 专业评估（完整分析）
    """
    if 'file' not in request.files:
        raise ValidationError('没有上传文件')
    file = request.files['file']
    if file.filename == '':
        raise ValidationError('没有选择文件')
    if not config.is_allowed_extension(file.filename):
        raise ValidationError('不支持的文件格式')

    # 获取评估模式参数
    mode = request.form.get('mode', 'quick')  # 默认快速模式

    safe_name = sanitize_filename(file.filename)
    filepath = config.get_upload_path(safe_name)
    file.save(str(filepath))

    # 处理可选的参考音频 (v5.10 DTW参考对比评分)
    reference_path = None
    if 'reference_file' in request.files:
        ref_file = request.files['reference_file']
        if ref_file.filename != '' and config.is_allowed_extension(ref_file.filename):
            ref_safe_name = sanitize_filename(ref_file.filename)
            ref_filepath = config.get_upload_path(ref_safe_name)
            ref_file.save(str(ref_filepath))
            reference_path = str(ref_filepath)
            logger.info(f"上传参考音频: {reference_path}")

    try:
        result = analyze_and_score(str(filepath), mode=mode, reference_path=reference_path)
    except Exception as e:
        logger.exception(f"Analysis failed: {e}")
        return jsonify({'success': False, 'error': f'分析失败: {str(e)}'}), 500

    if result['success']:
        _save_history(result, str(filepath))
        result['filepath'] = str(filepath)

    return jsonify(result)


@upload_bp.route('/analyze', methods=['POST'])
def analyze_file():
    """分析已存在的音频文件，支持可选参考音频"""
    filepath = request.json.get('filepath')
    if not filepath:
        raise ValidationError('缺少 filepath 参数')

    filepath_obj = validate_filepath(filepath)

    # 可选的参考音频路径 (v5.10 DTW参考对比评分)
    reference_path = None
    ref_filepath = request.json.get('reference_filepath')
    if ref_filepath:
        try:
            ref_path_obj = validate_filepath(ref_filepath)
            reference_path = str(ref_path_obj)
        except Exception as e:
            logger.warning(f"参考音频验证失败: {e}")

    result = analyze_and_score(str(filepath_obj), reference_path=reference_path)

    if result['success']:
        _save_history(result, str(filepath_obj))
        result['filepath'] = str(filepath_obj)

    return jsonify(result)


@upload_bp.route('/extract-pitch', methods=['POST'])
def extract_pitch():
    """
    提取音频的音高曲线 v5.10

    用于实时对比模式的前端获取标准音频音高数据。
    支持两种调用方式：
    1. FormData: 上传音频文件
    2. JSON: {\"filepath\": \"...\"} 指定已有文件路径

    Returns:
        {
            \"success\": true,
            \"data\": {
                \"duration\": 225.5,
                \"sample_rate\": 22050,
                \"hop_length\": 512,
                \"frequencies\": [261.6, 264.5, ...],
                \"times\": [0.0, 0.023, ...],
                \"confidence\": [1.0, 0.95, ...],
                \"frame_count\": 9780
            }
        }
    """
    import librosa
    import numpy as np

    # 处理上传文件
    if 'file' in request.files:
        file = request.files['file']
        if file.filename == '':
            raise ValidationError('没有选择文件')
        if not config.is_allowed_extension(file.filename):
            raise ValidationError('不支持的文件格式')
        safe_name = sanitize_filename(file.filename)
        filepath = config.get_upload_path(safe_name)
        file.save(str(filepath))
        filepath = str(filepath)
    elif request.is_json:
        json_data = request.get_json(silent=True)
        filepath = (json_data or {}).get('filepath')
        if not filepath:
            raise ValidationError('缺少 filepath 参数')
        filepath_obj = validate_filepath(filepath)
        filepath = str(filepath_obj)
    else:
        raise ValidationError('需要上传音频文件或指定 filepath')

    try:
        # 加载并降采样到16kHz
        TARGET_SR = 16000
        y, sr = librosa.load(filepath, sr=None, mono=True)
        if sr > TARGET_SR:
            y = librosa.resample(y, orig_sr=sr, target_sr=TARGET_SR)
            sr = TARGET_SR

        hop_length = 512

        # 提取基频 (yin算法)
        f0 = librosa.yin(
            y,
            fmin=65.0,   # C2
            fmax=1047.0, # C6
            sr=sr,
            hop_length=hop_length
        )

        times = librosa.times_like(f0, sr=sr, hop_length=hop_length)
        confidence = (~np.isnan(f0)).astype(float)

        return jsonify({
            'success': True,
            'data': {
                'duration': float(len(y) / sr),
                'sample_rate': sr,
                'hop_length': hop_length,
                'frequencies': [float(np.nan_to_num(f, nan=0.0)) for f in f0],
                'times': times.tolist(),
                'confidence': confidence.tolist(),
                'frame_count': len(f0)
            }
        })
    except Exception as e:
        logger.exception(f"音高提取失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@upload_bp.route('/separate', methods=['POST'])
def separate_audio():
    """人声分离"""
    filepath = request.json.get('filepath')
    if not filepath:
        raise ValidationError('缺少 filepath 参数')
    if not Path(filepath).exists():
        raise NotFoundError('文件不存在')

    model = request.json.get('model', 'htdemucs_ft')
    two_stems = request.json.get('two_stems', 'vocals')
    result = separation_service.separate(audio_path=filepath, model=model, two_stems=two_stems, output_format='mp3')

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
    """获取可用的分离模型列表"""
    return jsonify({'models': separation_service.get_available_models()})


@upload_bp.route('/report', methods=['POST'])
def generate_report():
    """生成评估报告"""
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
    """对比分析两个音频文件

    支持两种调用方式：
    1. JSON: {"standard_filepath": "...", "user_filepath": "..."}
    2. FormData: file (用户音频), standard_file (标准音频)

    使用三级DTW对齐引擎进行精确对比分析
    """
    # 检查是否是文件上传方式
    if 'file' in request.files and 'standard_file' in request.files:
        # FormData 方式
        user_file = request.files['file']
        standard_file = request.files['standard_file']

        if user_file.filename == '' or standard_file.filename == '':
            raise ValidationError('没有选择文件')
        if not config.is_allowed_extension(user_file.filename):
            raise ValidationError('不支持的用户音频格式')
        if not config.is_allowed_extension(standard_file.filename):
            raise ValidationError('不支持的标准音频格式')

        # 保存文件
        user_safe_name = sanitize_filename(user_file.filename)
        std_safe_name = sanitize_filename(standard_file.filename)

        user_filepath = config.get_upload_path(user_safe_name)
        std_filepath = config.get_upload_path(std_safe_name)

        user_file.save(str(user_filepath))
        standard_file.save(str(std_filepath))

        filepath_obj_std = std_filepath
        filepath_obj_user = user_filepath
    else:
        # JSON 方式
        if request.json is None:
            raise ValidationError('请求格式错误：需要JSON或FormData格式')

        standard_filepath = request.json.get('standard_filepath')
        user_filepath = request.json.get('user_filepath')

        if not standard_filepath:
            raise ValidationError('缺少 standard_filepath 参数')
        if not user_filepath:
            raise ValidationError('缺少 user_filepath 参数')

        filepath_obj_std = validate_filepath(standard_filepath)
        filepath_obj_user = validate_filepath(user_filepath)

    # 获取风格参数 (兼容JSON和FormData)
    style = 'pop'
    # 使用 is_json 检查避免 415 错误
    if request.is_json:
        try:
            json_data = request.get_json(silent=True)
            if json_data and isinstance(json_data, dict):
                style = json_data.get('style', 'pop')
        except Exception:
            pass
    elif request.form:
        style = request.form.get('style', 'pop')

    try:
        # 使用新的DTW对比服务
        from api.business import compare_with_dtw
        dtw_result = compare_with_dtw(
            str(filepath_obj_std),
            str(filepath_obj_user),
            style=style
        )

        if not dtw_result.get('success'):
            return jsonify({'success': False, 'error': dtw_result.get('error', 'DTW对比分析失败')}), 500

        # 同时保留旧的分析结果用于兼容
        standard_result = analyze_and_score(str(filepath_obj_std))
        user_result = analyze_and_score(str(filepath_obj_user))

    except Exception as e:
        logger.exception(f"Compare analysis failed: {e}")
        return jsonify({'success': False, 'error': f'分析失败: {str(e)}'}), 500

    if not standard_result.get('success'):
        return jsonify({'success': False, 'error': '标准音频分析失败'}), 500
    if not user_result.get('success'):
        return jsonify({'success': False, 'error': '用户音频分析失败'}), 500

    comparison = calculate_comparison(standard_result, user_result)

    return jsonify({
        'success': True,
        'data': {
            'score': dtw_result['score'],
            'level': dtw_result['level'],
            'confidence': dtw_result['confidence'],
            'pitch_match_rate': dtw_result['pitch_match_rate'],
            'rhythm_match_rate': dtw_result['rhythm_match_rate'],
            'avg_cents_error': dtw_result['avg_cents_error'],
            'diagnosis': dtw_result['diagnosis'],
            'suggestions': dtw_result['suggestions'],
            'dimensions': dtw_result['dimensions'],
            'method': dtw_result.get('method', 'three_level_dtw'),
            'standard': standard_result,
            'user': user_result,
            'comparison': comparison
        }
    })


def _save_history(result: dict, filepath: str):
    """保存历史记录"""
    history_record = {
        'filename': result['basic_info']['filename'],
        'filepath': filepath,
        'total_score': result['total_score'],
        'scores': result['scores'],
        'level': result['level'],
        'advice': result['advice']
    }
    history_repo.save(history_record)