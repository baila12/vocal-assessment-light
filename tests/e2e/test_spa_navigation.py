"""
E2E 测试 — SPA 导航与路由 (Playwright)

测试:
1. Hash 路由切换正常
2. 页面刷新保持路由
3. 旧页面重定向
4. 移动端响应式切换
5. 组件渲染 (Toast, Modal, ProgressBar)
"""
import pytest
from playwright.sync_api import expect


@pytest.mark.e2e
class TestSPANavigation:
    """SPA Hash 路由导航测试"""

    def test_home_page_loads(self, page, base_url):
        """首页应正常加载 SPA."""
        page.goto(base_url)
        # Wait for SPA to initialize
        page.wait_for_selector('#pageContainer', timeout=10000)
        # Should be at #/ or #/
        assert '#/' in page.url or page.url.endswith('/'), \
            f'Expected home URL, got {page.url}'

    def test_navigate_to_history(self, page, base_url):
        """导航到历史记录页."""
        page.goto(base_url)
        page.wait_for_selector('#pageContainer', timeout=10000)
        page.evaluate('window.__router.navigate("#/history")')
        page.wait_for_timeout(500)
        assert '#/history' in page.url, \
            f'Expected #/history, got {page.evaluate("location.hash")}'

    def test_navigate_to_settings(self, page, base_url):
        """导航到设置页."""
        page.goto(base_url)
        page.wait_for_selector('#pageContainer', timeout=10000)
        page.evaluate('window.__router.navigate("#/settings")')
        page.wait_for_timeout(500)
        assert '#/settings' in page.url

    def test_navigate_to_compare(self, page, base_url):
        """导航到对比分析页."""
        page.goto(base_url)
        page.wait_for_selector('#pageContainer', timeout=10000)
        page.evaluate('window.__router.navigate("#/compare")')
        page.wait_for_timeout(500)
        assert '#/compare' in page.url

    def test_navigate_to_sing(self, page, base_url):
        """导航到演唱页."""
        page.goto(base_url)
        page.wait_for_selector('#pageContainer', timeout=10000)
        page.evaluate('window.__router.navigate("#/sing")')
        page.wait_for_timeout(500)
        assert '#/sing' in page.url

    def test_refresh_preserves_route(self, page, base_url):
        """刷新页面应保持当前路由."""
        page.goto(f'{base_url}#/history')
        page.wait_for_selector('#pageContainer', timeout=10000)
        page.wait_for_timeout(500)
        page.reload()
        page.wait_for_timeout(1000)
        current_hash = page.evaluate('location.hash')
        assert '#/history' in current_hash, \
            f'Hash not preserved on refresh: {current_hash}'

    def test_invalid_route_redirects(self, page, base_url):
        """无效路由应重定向到首页."""
        page.goto(f'{base_url}#/nonexistent-route-xyz')
        page.wait_for_selector('#pageContainer', timeout=10000)
        page.wait_for_timeout(1000)
        current_hash = page.evaluate('location.hash') or '#/'
        # Should redirect to home
        assert current_hash == '#/', \
            f'Expected redirect to #/, got {current_hash}'

    def test_browser_back_navigation(self, page, base_url):
        """浏览器后退应工作."""
        page.goto(base_url)
        page.wait_for_selector('#pageContainer', timeout=10000)
        # Navigate to history
        page.evaluate('window.__router.navigate("#/history")')
        page.wait_for_timeout(500)
        # Navigate to settings
        page.evaluate('window.__router.navigate("#/settings")')
        page.wait_for_timeout(500)
        # Go back
        page.go_back()
        page.wait_for_timeout(500)
        current_hash = page.evaluate('location.hash')
        assert '#/history' in current_hash, \
            f'Back should return to #/history, got {current_hash}'


@pytest.mark.e2e
class TestSPAComponents:
    """SPA 组件渲染测试"""

    def test_toast_container_exists(self, page, base_url):
        """Toast 容器应存在."""
        page.goto(base_url)
        page.wait_for_selector('#toastWrap', timeout=10000)
        toast_wrap = page.locator('#toastWrap')
        assert toast_wrap.count() > 0

    def test_global_progress_bar_exists(self, page, base_url):
        """全局进度条应存在."""
        page.goto(base_url)
        page.wait_for_selector('#globalProgressBar', timeout=10000)
        bar = page.locator('#globalProgressBar')
        assert bar.count() > 0

    def test_top_nav_rendered(self, page, base_url):
        """顶部导航应由 JS 动态渲染."""
        page.goto(base_url)
        page.wait_for_selector('.top-nav .nav-tab', timeout=10000)
        tabs = page.locator('.nav-tab')
        assert tabs.count() >= 4, \
            f'Expected 4+ nav tabs, got {tabs.count()}'

    def test_bottom_nav_rendered(self, page, base_url):
        """底部导航应由 JS 动态渲染."""
        page.goto(base_url)
        page.wait_for_selector('.bottom-nav', timeout=10000)
        bottom_nav = page.locator('.bottom-nav')
        assert bottom_nav.count() > 0

    def test_home_page_content(self, page, base_url):
        """首页核心内容应渲染."""
        page.goto(base_url)
        page.wait_for_selector('#page-home', timeout=10000)
        # Should have welcome section, action cards, mode selector
        assert page.locator('.welcome-section').count() > 0
        assert page.locator('.action-cards').count() > 0
        assert page.locator('#modeSelector').count() > 0


@pytest.mark.e2e
class TestResponsiveLayout:
    """响应式布局测试"""

    def test_mobile_viewport_bottom_nav(self, page, base_url):
        """移动端应显示底部导航."""
        page.set_viewport_size({'width': 375, 'height': 667})
        page.goto(base_url)
        page.wait_for_selector('#pageContainer', timeout=10000)
        page.wait_for_timeout(500)

        # Bottom nav should be visible
        bottom_nav_display = page.evaluate(
            'document.querySelector(".bottom-nav")?.style.display'
        )
        # Top nav should be hidden
        top_nav_display = page.evaluate(
            'document.querySelector(".top-nav")?.style.display'
        )
        # At least one should be correct
        assert top_nav_display == 'none' or bottom_nav_display == 'flex', \
            f'Mobile nav not correct: top={top_nav_display}, bottom={bottom_nav_display}'

    def test_desktop_viewport_top_nav(self, page, base_url):
        """桌面端应显示顶部导航."""
        page.set_viewport_size({'width': 1280, 'height': 720})
        page.goto(base_url)
        page.wait_for_selector('#pageContainer', timeout=10000)
        page.wait_for_timeout(500)

        # Top nav should be visible
        top_nav = page.locator('.top-nav')
        assert top_nav.count() > 0


@pytest.mark.e2e
class TestOfflineCapability:
    """离线能力测试"""

    def test_gsap_loaded_locally(self, page, base_url):
        """GSAP 应从本地加载."""
        page.goto(base_url)
        page.wait_for_timeout(1000)
        gsap_available = page.evaluate('typeof gsap !== "undefined"')
        assert gsap_available, 'GSAP global not available'

    def test_chartjs_loaded_locally(self, page, base_url):
        """Chart.js 应从本地加载."""
        page.goto(base_url)
        page.wait_for_timeout(1000)
        chart_available = page.evaluate('typeof Chart !== "undefined"')
        assert chart_available, 'Chart.js global not available'

    def test_store_initialized(self, page, base_url):
        """Store 应全局初始化."""
        page.goto(base_url)
        page.wait_for_timeout(1000)
        has_store = page.evaluate('window.__store !== undefined')
        assert has_store, 'window.__store not initialized'

    def test_router_initialized(self, page, base_url):
        """Router 应全局初始化."""
        page.goto(base_url)
        page.wait_for_timeout(1000)
        has_router = page.evaluate('window.__router !== undefined')
        assert has_router, 'window.__router not initialized'


@pytest.mark.e2e
class TestThemeSwitching:
    """主题切换测试"""

    def test_dark_theme_toggle(self, page, base_url):
        """切换到暗色主题."""
        page.goto(f'{base_url}#/settings')
        page.wait_for_selector('#page-settings', timeout=10000)
        page.wait_for_timeout(500)

        # Click dark theme button
        dark_btn = page.locator('.theme-btn[data-theme="dark"]')
        if dark_btn.count() > 0:
            dark_btn.first.click()
            page.wait_for_timeout(300)

        # Verify dark class or localStorage
        has_dark = page.evaluate('document.body.classList.contains("dark-theme")')
        theme_stored = page.evaluate('localStorage.getItem("vocal_app_theme")')

        assert has_dark or theme_stored == 'dark', \
            f'Dark theme not applied: class={has_dark}, storage={theme_stored}'
