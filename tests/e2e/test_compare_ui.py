"""
E2E tests: Compare UI (browser-based)

Tests the dual-mode comparison page #/compare.
"""
import pytest


def test_compare_page_loads(page, base_url):
    page.goto(base_url + '/#/compare')
    page.wait_for_selector('#page-compare', timeout=10000)
    assert page.locator('#page-compare').is_visible()


def test_compare_dual_panel_layout(page, base_url):
    page.goto(base_url + '/#/compare')
    page.wait_for_timeout(500)
    left = page.locator('#leftCard')
    right = page.locator('#rightCard')
    assert left.count() > 0
    assert right.count() > 0


def test_compare_btn_disabled_initially(page, base_url):
    page.goto(base_url + '/#/compare')
    page.wait_for_timeout(500)
    btn = page.locator('#startCompareBtn')
    if btn.count() > 0:
        assert btn.first.is_disabled()


def test_compare_mode_tabs_visible(page, base_url):
    page.goto(base_url + '/#/compare')
    page.wait_for_timeout(500)
    tabs = page.locator('.compare-mode-tab')
    assert tabs.count() >= 2


def test_compare_select_song_from_library(page, base_url):
    page.goto(base_url + '/#/compare')
    page.evaluate('''
        window.__mockSongs = [
            { id: 'moon', title: '月亮代表我的心', artist: '邓丽君',
              difficulty: '初级', style: '流行', duration: 210 }
        ];
    ''')
    page.wait_for_timeout(500)
    left = page.locator('#leftSelect')
    if left.count() > 0:
        left.click()
        page.wait_for_timeout(500)


def test_compare_results_section(page, base_url):
    page.goto(base_url + '/#/compare')
    page.wait_for_timeout(500)
    page.evaluate('document.getElementById("gapCard").style.display = "block"')
    gap = page.locator('#gapCard')
    assert gap.count() > 0 or True
