"""
接口层 - Flask 应用工厂
负责创建和配置 Flask 应用
"""
from flask import Flask
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS
from pathlib import Path
import numpy as np

from config import Config
from .routes import upload_bp, history_bp, audio_bp
from .errors import register_error_handlers

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent


class NumpyJSONProvider(DefaultJSONProvider):
    """自定义 JSON 提供器，支持 numpy 类型"""

    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        return super().default(obj)


def create_app(config: Config = None) -> Flask:
    """
    应用工厂函数

    Args:
        config: 配置对象，默认使用全局配置

    Returns:
        Flask 应用实例
    """
    if config is None:
        from config import config as default_config
        config = default_config

    # 静态文件目录
    static_folder = PROJECT_ROOT / 'web' / 'static'

    # 创建应用
    app = Flask(
        __name__,
        static_folder=str(static_folder),
        static_url_path=''
    )

    # 设置自定义 JSON 提供器以支持 numpy 类型
    app.json = NumpyJSONProvider(app)

    # 加载配置
    app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH
    app.config['UPLOAD_FOLDER'] = str(config.UPLOAD_FOLDER)

    # 启用 CORS
    CORS(app)

    # 注册蓝图
    app.register_blueprint(upload_bp, url_prefix='/api')
    app.register_blueprint(history_bp, url_prefix='/api')
    app.register_blueprint(audio_bp, url_prefix='/api')

    # 注册错误处理
    register_error_handlers(app)

    # 首页路由
    @app.route('/')
    def index():
        from flask import send_file
        index_path = static_folder / 'index.html'
        return send_file(str(index_path))

    # 分析页面路由
    @app.route('/analysis.html')
    def analysis():
        from flask import send_file
        analysis_path = static_folder / 'analysis.html'
        return send_file(str(analysis_path))

    # 健康检查端点
    @app.route('/health')
    def health_check():
        from flask import jsonify
        import time

        checks = {
            'upload_dir': config.UPLOAD_FOLDER.exists(),
            'history_file': config.HISTORY_FILE.parent.exists(),
            'plots_dir': (static_folder / 'plots').exists(),
            'separated_dir': config.SEPARATED_DIR.exists(),
            'reports_dir': config.REPORTS_DIR.exists()
        }

        all_healthy = all(checks.values())

        return jsonify({
            'status': 'healthy' if all_healthy else 'degraded',
            'version': '1.0.0',
            'timestamp': time.time(),
            'checks': checks
        }), 200 if all_healthy else 503

    # 可视化图片路由 - 确保 /plots/ 路径正确服务静态文件
    @app.route('/plots/<path:filename>')
    def serve_plot(filename):
        from flask import send_from_directory, abort
        import re

        # 只允许图片文件扩展名
        allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'}
        if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
            abort(403, "只允许访问图片文件")

        # 安全检查：防止路径遍历和控制字符注入
        # 注意：保留中文字符，只移除危险字符
        if '..' in filename or '\x00' in filename:
            abort(403, "无效的文件名")

        # 移除路径分隔符，只保留文件名部分
        safe_filename = filename.replace('/', '_').replace('\\', '_')

        plots_dir = static_folder / 'plots'

        # 验证文件存在
        file_path = plots_dir / safe_filename
        if not file_path.exists() or not file_path.is_file():
            abort(404, "文件不存在")

        return send_from_directory(str(plots_dir), safe_filename)

    return app
