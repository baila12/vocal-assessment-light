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
    # v7.15 P2-14: 跳过启动上传孤儿清理
    os.environ.setdefault("VAS_SKIP_UPLOAD_CLEANUP", "1")


@pytest.fixture(scope='module', autouse=True)
def _reset_deps_caches():
    """模块级自动夹具 — 每个模块开始前清空 deps 单例缓存.

    v7.15 修复 (pre-existing 隔离缺陷): deps 的 @lru_cache 单例
    (get_song_repo/get_song_service/get_auto_match_use_case/
    get_song_match_profile_repo/get_pitch_cache/get_settings) 在单进程内
    跨模块持久。组合运行多个集成模块时, 后续模块即使已设 VAS_SONGS_DB,
    仍绑定上一模块的临时 DB → 数据污染。
    复现: `pytest test_songs_api.py test_song_match_api.py` → 后者的
    test_match_no_match_fallback 误命中前者写入的歌曲 (HEAD 亦复现, 与代码无关)。

    文档化工作流 (每模块独立进程) 本不受影响; 本夹具保证组合运行同样正确 —
    与 BDD conftest.fastapi_client 的 cache_clear 模式一致。
    """
    from backend.interfaces.api import deps
    for name in (
        'get_settings',
        'get_song_repo',
        'get_song_service',
        'get_pitch_cache',
        'get_song_match_profile_repo',
        'get_auto_match_use_case',
    ):
        fn = getattr(deps, name, None)
        clear = getattr(fn, 'cache_clear', None)
        if clear:
            clear()
