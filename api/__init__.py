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


def _detect_gpu_info() -> dict:
    """检测 GPU 加速可用性 v5.17"""
    info = {
        'available': False,
        'device': None,
        'name': None,
        'demucs_accelerated': False,
    }
    try:
        import torch
        if torch.cuda.is_available():
            info['available'] = True
            info['device'] = 'cuda'
            info['name'] = torch.cuda.get_device_name(0)
            info['demucs_accelerated'] = True
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            info['available'] = True
            info['device'] = 'mps'
            info['name'] = 'Apple Silicon GPU'
            info['demucs_accelerated'] = True
    except ImportError:
        pass
    except Exception:
        pass
    return info


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
    """应用工厂函数"""
    if config is None:
        from config import config as default_config
        config = default_config

    static_folder = PROJECT_ROOT / 'web' / 'static'

    app = Flask(
        __name__,
        static_folder=str(static_folder),
        static_url_path=''
    )

    app.json = NumpyJSONProvider(app)
    app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH
    app.config['UPLOAD_FOLDER'] = str(config.UPLOAD_FOLDER)

    CORS(app)
    app.register_blueprint(upload_bp, url_prefix='/api')
    app.register_blueprint(history_bp, url_prefix='/api')
    app.register_blueprint(audio_bp, url_prefix='/api')
    register_error_handlers(app)

    # SPA 入口 — 唯一 HTML 入口
    @app.route('/')
    def index():
        from flask import send_file
        return send_file(str(static_folder / 'index.html'))

    # 旧页面 301 重定向 — 保持已有书签可用
    @app.route('/analysis.html')
    def redirect_analysis():
        from flask import redirect
        return redirect('/', code=301)

    @app.route('/compare.html')
    def redirect_compare():
        from flask import redirect
        return redirect('/', code=301)

    @app.route('/settings.html')
    def redirect_settings():
        from flask import redirect
        return redirect('/', code=301)

    # SPA 回退 — 未知 HTML 路径返回 index.html (支持深层链接刷新)
    @app.route('/index.html')
    def spa_fallback():
        from flask import send_file
        return send_file(str(static_folder / 'index.html'))

    # 健康检查端点
    @app.route('/health')
    def health_check():
        from flask import jsonify
        import time
        gpu_info = _detect_gpu_info()
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
            'checks': checks,
            'gpu': gpu_info,
        }), 200 if all_healthy else 503

    # 可视化图片路由
    @app.route('/plots/<path:filename>')
    def serve_plot(filename):
        from flask import send_from_directory, abort
        allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'}
        if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
            abort(403, "只允许访问图片文件")
        if '..' in filename or '\x00' in filename:
            abort(403, "无效的文件名")
        safe_filename = filename.replace('/', '_').replace('\\', '_')
        plots_dir = static_folder / 'plots'
        file_path = plots_dir / safe_filename
        if not file_path.exists() or not file_path.is_file():
            abort(404, "文件不存在")
        return send_from_directory(str(plots_dir), safe_filename)

    return app
