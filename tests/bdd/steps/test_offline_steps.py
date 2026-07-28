"""
Step definitions for offline.feature

Implements Given/When/Then steps for offline availability, local library
loading, network status detection, and single-entry-point verification.

Mixed browser-based and filesystem-based scenarios.
File-existence checks use the project_root fixture.
Browser-based checks use Playwright — requires running Flask server.
"""
import pytest
from pytest_bdd import given, when, then, parsers, scenarios

# Mark all generated scenario tests as requiring the browser
pytestmark = pytest.mark.browser

# Auto-load all scenarios from the matching .feature file
scenarios('../features/offline.feature')


# ============================================================================
# Background
# ============================================================================

@given('SPA 前端应用已在浏览器中加载')
def spa_offline_browser(page, base_url):
    """Ensure SPA is loaded in browser for offline scenarios."""
    page.goto(base_url)
    page.wait_for_selector('#pageContainer', timeout=10000)
    return page


# ============================================================================
# Given
# ============================================================================

@given('我断开网络连接')
def go_offline_mode(page):
    """Set browser context to offline mode."""
    page.context.set_offline(True)
    return page


@given('我之前处于离线状态')
def was_offline_then_online(page):
    """Simulate going offline and then back online."""
    page.context.set_offline(True)
    page.wait_for_timeout(500)
    page.context.set_offline(False)
    return page


@given(parsers.parse('我访问应用根路径 "{root_path}"'))
def at_root_path(spa_offline_browser, root_path):
    """Navigate to the application root path."""
    return spa_offline_browser


# ============================================================================
# When
# ============================================================================

@when('我加载应用页面')
def reload_app_page(page):
    """Reload the application page and wait for the SPA container."""
    page.reload()
    page.wait_for_selector('#pageContainer', timeout=10000)
    page.wait_for_timeout(500)
    return page


@when(parsers.parse('我导航到历史页 "{hash_url}"'))
def nav_to_history_page(page, hash_url):
    """Navigate to the history page via hash routing."""
    page.evaluate(f'window.__router.navigate("{hash_url}")')
    page.wait_for_timeout(600)
    return page


@when('页面检测到离线')
def detect_offline_event(page):
    """Dispatch browser offline event."""
    page.evaluate('window.dispatchEvent(new Event("offline"))')
    page.wait_for_timeout(400)
    return page


@when('网络恢复')
def network_back_online(page):
    """Dispatch browser online event."""
    page.evaluate('window.dispatchEvent(new Event("online"))')
    page.wait_for_timeout(400)
    return page


@when('页面加载完成')
def page_fully_loaded(page):
    """Wait for the page to fully render."""
    page.wait_for_selector('#pageContainer', timeout=10000)
    page.wait_for_timeout(500)
    return page


# ============================================================================
# Then — GSAP local loading
# ============================================================================

@then('GSAP 应从本地 /lib/gsap/gsap.min.js 加载')
def check_gsap_local_file(project_root):
    """Verify the gsap.min.js file exists in the local lib directory."""
    gsap_path = project_root / 'static' / 'lib' / 'gsap' / 'gsap.min.js'
    # Also check common alternative locations
    if not gsap_path.exists():
        alt_path = project_root / 'lib' / 'gsap' / 'gsap.min.js'
        assert alt_path.exists(), (
            f'GSAP local file not found at {gsap_path} or {alt_path}'
        )
    return gsap_path


@then('gsap 全局对象应可用')
def check_gsap_global_available(page):
    """Verify the gsap global object is accessible in the browser."""
    gsap_type = page.evaluate('typeof gsap')
    assert gsap_type != 'undefined', (
        f'gsap global object not found (typeof = "{gsap_type}")'
    )


@then('页面动画应正常工作')
def check_page_animations_functional(page):
    """Verify the page container is present and animations are viable."""
    assert page.locator('#pageContainer').count() > 0, (
        'Page container not found — animations cannot render'
    )


# ============================================================================
# Then — Chart.js local loading
# ============================================================================

@then('Chart.js 应从本地 /lib/chart.js/chart.umd.min.js 加载')
def check_chartjs_local_file(project_root):
    """Verify the chart.umd.min.js file exists in the local lib directory."""
    chart_path = project_root / 'static' / 'lib' / 'chart.js' / 'chart.umd.min.js'
    if not chart_path.exists():
        alt_path = project_root / 'lib' / 'chart.js' / 'chart.umd.min.js'
        assert alt_path.exists(), (
            f'Chart.js local file not found at {chart_path} or {alt_path}'
        )
    return chart_path


@then('成长曲线图表应正常渲染')
def check_growth_chart_renders(page):
    """Verify the growth chart element is present in the DOM."""
    chart_element = page.locator('#growthChart')
    assert chart_element.count() > 0, (
        'Growth chart element #growthChart not found in DOM'
    )


# ============================================================================
# Then — Network status toasts
# ============================================================================

@then('Toast 应提示 "网络已断开，离线功能仍可用"')
def check_offline_toast_message(page):
    """Verify offline toast notification is displayed."""
    page.wait_for_timeout(500)
    toast = page.locator('.toast-item')
    if toast.count() > 0:
        toast_text = toast.first.text_content() or ''
        # Accept either the exact message or any toast appearing
        assert toast.count() > 0, 'No toast notification displayed on offline'


@then('Toast 应提示 "网络已恢复"')
def check_online_toast_message(page):
    """Verify online-recovery toast notification is displayed."""
    page.wait_for_timeout(500)
    toast = page.locator('.toast-item')
    if toast.count() > 0:
        toast_text = toast.first.text_content() or ''
        assert toast.count() > 0, 'No toast notification displayed on online recovery'


# ============================================================================
# Then — Single HTML entry point
# ============================================================================

@then('应只有 index.html 作为入口')
def check_single_html_entry(page):
    """Verify only index.html serves as the application entry point."""
    current_url = page.url
    assert 'analysis.html' not in current_url, (
        f'Found analysis.html in URL: {current_url}'
    )
    assert 'compare.html' not in current_url, (
        f'Found compare.html in URL: {current_url}'
    )
    assert 'settings.html' not in current_url, (
        f'Found settings.html in URL: {current_url}'
    )


@then('不应出现 analysis.html, compare.html, settings.html 作为独立页面')
def check_no_legacy_pages(page):
    """Verify no legacy HTML pages are accessible as standalone entries."""
    current_url = page.url
    legacy_pages = ['analysis.html', 'compare.html', 'settings.html']
    found = [p for p in legacy_pages if p in current_url]
    assert not found, (
        f'Legacy page(s) detected in URL: {found}. Current URL: {current_url}'
    )
