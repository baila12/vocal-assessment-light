"""
BDD 测试专用 fixtures.

Provides:
- test_data_dir: 测试数据根目录
- api_client: Flask 测试客户端 (session 级别复用)
- base_url: 应用根 URL (Playwright)
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
    """Flask 测试客户端 (session 级别复用)."""
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    from api import create_app

    app = create_app()
    app.config['TESTING'] = True

    with app.test_client() as client:
        yield client


@pytest.fixture(scope='session')
def project_root():
    """项目根目录."""
    return Path(__file__).parent.parent.parent


# ============================================================================
# Playwright fixtures — for browser-based BDD scenarios
# (navigation, animations, responsive, offline features)
# ============================================================================

@pytest.fixture(scope='session')
def base_url():
    """应用基础 URL."""
    return 'http://localhost:5000'


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
        pytest.skip('Flask server not reachable at ' + base_url)

    yield page
    context.close()
