"""
Unit tests conftest — v7.3

在模块导入前设置环境变量，防止 PyTorch 等 C 扩展模块在 pytest 进程中冲突。
"""

import os


def pytest_configure(config):
    """pytest 启动时最早调用 — 在任何测试模块 import 之前"""
    os.environ.setdefault("VAS_SKIP_GPU", "1")
    os.environ.setdefault("VAS_DISABLE_RATE_LIMIT", "1")
