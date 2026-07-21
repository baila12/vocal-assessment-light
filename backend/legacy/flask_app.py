"""
Legacy Flask 应用包装 — 绞杀者模式

ADR-4: 独立 legacy 表隔离 (history_v6)
Phase 2 时 mount 到 FastAPI /old 路径。
"""

from __future__ import annotations

from pathlib import Path
import sys
import os

# 确保项目根目录在 sys.path 中 (legacy Flask 需要)
_project_root = Path(__file__).parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def create_legacy_flask_app():
    """
    延迟导入旧 Flask 应用工厂。

    注意: 旧代码依赖 config.Config dataclass (非 Pydantic Settings),
    两者互不干扰 — 旧 Flask 保持原有配置路径。
    """
    from api import create_app as create_flask_app
    from config import config as flask_config

    flask_app = create_flask_app(flask_config)
    return flask_app


# 懒加载 — Phase 2 挂载时才实例化
flask_app = None


def get_flask_app():
    global flask_app
    if flask_app is None:
        flask_app = create_legacy_flask_app()
    return flask_app
