"""
Integration tests conftest — v7.3

修复 pytest + PyTorch 扩展模块冲突:
- VAS_SKIP_GPU=1 跳过 GPU 检测 (避免 import torch 导致 C 扩展冲突)
- 使用 --no-header 减少输出噪音
"""

import os
import pytest


def pytest_configure(config):
    """在 pytest 启动时设置环境变量，在 import 任何测试模块之前生效"""
    os.environ.setdefault("VAS_SKIP_GPU", "1")
    # 同时禁用 rate-limit 以加速测试
    os.environ.setdefault("VAS_DISABLE_RATE_LIMIT", "1")


@pytest.fixture(autouse=True)
def _integration_marker(request):
    """自动为 integration 目录下所有测试添加 integration 标记"""
    pass
