"""
音频播放路由
处理音频文件播放请求
"""
from flask import Blueprint, send_file, request
from pathlib import Path
from urllib.parse import unquote
import re

from config import config
from api.errors import NotFoundError, ForbiddenError

audio_bp = Blueprint('audio', __name__)

# MIME类型映射
MIME_TYPES = {
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.ogg': 'audio/ogg',
    '.flac': 'audio/flac',
    '.m4a': 'audio/mp4',
    '.aac': 'audio/aac'
}


@audio_bp.route('/audio', methods=['GET'])
def get_audio():
    """
    获取音频文件用于播放

    请求：
        GET /api/audio?file=/path/to/audio.wav

    响应：
        音频文件流
    """
    # URL解码后检查
    filepath = unquote(request.args.get('file', ''))

    if not filepath:
        raise NotFoundError('缺少文件路径')

    # 安全检查1：防止路径遍历（检查原始和解码后的路径）
    if '..' in filepath or '~' in filepath:
        raise ForbiddenError('无效的文件路径')

    # 安全检查2：防止控制字符注入
    if re.search(r'[\x00-\x1f\x7f]', filepath):
        raise ForbiddenError('无效的文件路径')

    # 安全检查3：验证文件扩展名
    filepath_obj = Path(filepath)
    if filepath_obj.suffix.lower() not in config.ALLOWED_EXTENSIONS:
        raise ForbiddenError('不支持的文件格式')

    # 规范化路径
    try:
        filepath = filepath_obj.resolve()
    except Exception:
        raise ForbiddenError('无效的文件路径')

    # 安全检查4：确保文件在允许的目录内
    upload_dir = config.UPLOAD_FOLDER.resolve()
    test_dir = (config.PROJECT_ROOT / 'test_music').resolve()

    filepath_str = str(filepath)
    if not (
        filepath_str.startswith(str(upload_dir)) or
        filepath_str.startswith(str(test_dir))
    ):
        raise ForbiddenError('无权访问此文件')

    # 安全检查5：验证文件存在且是文件
    if not filepath.exists() or not filepath.is_file():
        raise NotFoundError('文件不存在')

    # 获取正确的MIME类型
    mime_type = MIME_TYPES.get(filepath_obj.suffix.lower(), 'audio/mpeg')

    return send_file(filepath, mimetype=mime_type)
