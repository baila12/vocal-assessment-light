"""
BDD 测试专用 fixtures.

Provides:
- test_data_dir: 测试数据根目录
- api_client: FastAPI 测试客户端 (session 级别复用) — v7.11: Flask 已移除
- base_url: 应用根 URL (Playwright) — FastAPI :8000 生产构建
- page: Playwright 浏览器页面 (function 级别)
- browser: Playwright 浏览器实例 (session 级别)
"""
import pytest
from pathlib import Path
import sys


@pytest.fixture(scope='session')
def test_data_dir():
    """测试数据根目录."""
    path = Path(__file__).parent.parent / 'test_data'
    if not path.exists():
        pytest.skip(f'测试数据目录不存在: {path}')
    return path


@pytest.fixture(scope='session')
def api_client():
    """FastAPI 测试客户端 (session 级别复用). v7.11: 原 Flask client 已随 Flask 移除."""
    from backend.main import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope='session')
def project_root():
    """项目根目录."""
    return Path(__file__).parent.parent.parent


@pytest.fixture(scope='function')
def fastapi_client():
    """FastAPI 测试客户端 — 每个 BDD 场景独立临时 DB, 完全隔离.

    歌曲库场景 (database.feature) 共享 DB 会导致跨场景数据冲突,
    故每场景新建临时 songs.db + 音频目录, 并重置 DI 缓存让其重新读取。
    """
    import os
    import tempfile
    tmp = tempfile.mkdtemp(prefix='vas_bdd_songs_')
    os.environ['VAS_SONGS_DB'] = str(Path(tmp) / 'songs.db')
    os.environ['VAS_SONGS_DIR'] = str(Path(tmp) / 'audio')

    # 重置 DI 缓存 — 让仓储/设置重新读取新的 DB 路径
    from backend.interfaces.api import deps
    deps.get_settings.cache_clear()
    deps.get_song_service.cache_clear()
    # v7.14: auto-match 单例也绑定 DB 路径, 必须一并清空 (否则跨场景复用旧 profile 库)
    deps.get_song_match_profile_repo.cache_clear()
    deps.get_auto_match_use_case.cache_clear()

    from backend.main import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    with TestClient(app) as client:
        yield client


# ============================================================================
# Playwright fixtures — for browser-based BDD scenarios
# (navigation, animations, responsive, offline features)
# ============================================================================

@pytest.fixture(scope='session')
def base_url():
    """应用基础 URL — v7.11: Flask :5000 已移除, FastAPI :8000 服务 frontend/dist.

    运行浏览器 BDD 前需: python backend/main.py (生产构建挂载 /)。
    """
    return 'http://localhost:8000'


@pytest.fixture(scope='session')
def browser():
    """浏览器实例 - session 级别 (Playwright)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        pytest.skip('playwright not installed')

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        yield browser
        browser.close()


@pytest.fixture(scope='function')
def page(browser, base_url):
    """为每个 BDD 场景创建新的浏览器页面."""
    context = browser.new_context(
        viewport={'width': 1280, 'height': 720},
        locale='zh-CN',
        timezone_id='Asia/Shanghai'
    )
    page = context.new_page()

    # Navigate to app
    try:
        page.goto(base_url, timeout=10000)
    except Exception:
        # Server may not be running — skip browser tests
        pytest.skip('FastAPI server not reachable at ' + base_url)

    yield page
    context.close()
