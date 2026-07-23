"""
接口层 - 统一错误处理
"""
from flask import jsonify
from typing import Tuple


class APIError(Exception):
    """
    统一 API 错误类

    使用方式：
        raise APIError("文件不存在", 404)
    """
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(APIError):
    """参数校验错误"""
    def __init__(self, message: str):
        super().__init__(message, 400)


class NotFoundError(APIError):
    """资源不存在错误"""
    def __init__(self, message: str):
        super().__init__(message, 404)


class ForbiddenError(APIError):
    """权限不足错误"""
    def __init__(self, message: str):
        super().__init__(message, 403)


def register_error_handlers(app):
    """注册错误处理器"""

    @app.errorhandler(APIError)
    def handle_api_error(error: APIError) -> Tuple[dict, int]:
        """处理 API 错误"""
        return jsonify({
            'success': False,
            'error': error.message
        }), error.status_code

    @app.errorhandler(400)
    def handle_bad_request(error) -> Tuple[dict, int]:
        """处理 400 错误"""
        return jsonify({
            'success': False,
            'error': '请求格式错误'
        }), 400

    @app.errorhandler(404)
    def handle_not_found(error) -> Tuple[dict, int]:
        """处理 404 错误"""
        return jsonify({
            'success': False,
            'error': '资源不存在'
        }), 404

    @app.errorhandler(413)
    def handle_file_too_large(error) -> Tuple[dict, int]:
        """处理文件过大错误"""
        return jsonify({
            'success': False,
            'error': '文件大小超过50MB限制，请压缩音频或分段上传'
        }), 413

    @app.errorhandler(Exception)
    def handle_unexpected_error(error) -> Tuple[dict, int]:
        """处理未预期的错误"""
        import logging
        logger = logging.getLogger(__name__)
        logger.exception("Unexpected error: %s", error)
        # 返回通用错误信息给客户端 (不暴露内部细节)
        return jsonify({
            'success': False,
            'error': '服务器内部错误'
        }), 500
