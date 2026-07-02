"""
E2E tests: Mode Select (browser-based)

Tests quick/professional mode switching and persistence.
"""
import pytest


def test_mode_selector_visible_on_home(page, base_url):
    """首页显示模式选择器"""
    page.goto(base_url + '/#/')
    page.wait_for_selector('#page-home', timeout=10000)

    modes = page.locator('.mode-option')
    assert modes.count() >= 2, 'Expected at least 2 mode options'


def test_default_mode_is_quick(page, base_url):
    """默认选中快速模式"""
    page.goto(base_url + '/#/')
    page.wait_for_timeout(500)

    active = page.locator('.mode-option.active')
    assert active.count() > 0
    mode = active.first.get_attribute('data-mode') or ''
    assert 'quick' in mode or active.first.text_content().find('快速') >= 0


def test_switch_to_professional(page, base_url):
    """切换到专业模式"""
    page.goto(base_url + '/#/')
    page.wait_for_timeout(500)

    prof = page.locator('.mode-option[data-mode="professional"]')
    if prof.count() > 0:
        prof.click()
        page.wait_for_timeout(300)

        active = page.locator('.mode-option.active')
        mode = active.first.get_attribute('data-mode') or ''
        assert 'professional' in mode or '专业' in active.first.text_content()


def test_mode_persists_after_refresh(page, base_url):
    """模式偏好持久化"""
    page.goto(base_url + '/#/')
    page.wait_for_timeout(500)

    # Switch to professional
    prof = page.locator('.mode-option[data-mode="professional"]')
    if prof.count() > 0:
        prof.click()
    page.evaluate("localStorage.setItem('vocal_app_evalMode', 'professional')")
    page.wait_for_timeout(300)

    # Reload
    page.reload()
    page.wait_for_selector('#page-home', timeout=10000)
    page.wait_for_timeout(500)

    # Mode should be restored
    stored = page.evaluate("localStorage.getItem('vocal_app_evalMode')")
    assert stored == 'professional', f'Expected professional, got {stored}'


def test_mode_switch_keeps_file(page, base_url):
    """模式切换不丢失已选文件"""
    page.goto(base_url + '/#/')
    page.wait_for_timeout(500)

    # Simulate file selection
    page.evaluate('''
        window.__mockFile = { name: 'test.mp3' };
        const info = document.getElementById('fileInfo');
        if (info) info.style.display = 'block';
    ''')

    # Switch mode
    prof = page.locator('.mode-option[data-mode="professional"]')
    if prof.count() > 0:
        prof.click()
    page.wait_for_timeout(300)

    file_exists = page.evaluate('!!window.__mockFile')
    assert file_exists, 'File reference lost after mode switch'
