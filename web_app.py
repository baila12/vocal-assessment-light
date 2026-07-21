"""
v6.3 Flask 应用入口

兼容 v7.0 绞杀者模式:
  - 直接运行: python web_app.py (标准 Flask 模式)
  - WSGI 挂载: FastAPI mount 时通过 create_app() 获取 WSGI callable

ADR-4: 旧应用保持独立运行，不依赖 FastAPI。
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api import create_app
from config import config


# 全局 app 实例 — 供直接运行和 WSGI 挂载复用
app = create_app(config)


def get_wsgi_app():
    """返回 WSGI callable — FastAPI WSGIMiddleware 挂载点 (Phase 2)"""
    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    print("=" * 50)
    print("Vocal Assessment Web v6.3 - http://localhost:" + str(port))
    print("=" * 50)
    app.run(host="0.0.0.0", port=port, debug=debug, threaded=True, use_reloader=False)