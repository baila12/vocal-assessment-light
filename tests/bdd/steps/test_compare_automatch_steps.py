"""
Step definitions for compare-automatch.feature — v7.15 H-B14

覆盖当前 Vue 3 CompareView (frontend/src/views/CompareView.vue) 自动匹配反馈:
  - store.error        → 常驻错误告警 data-test="auto-match-error"   (H-B14: 死信 ref 修复)
  - matchedSong        → 命中徽标 data-test="auto-match-hit"
  - fallbackReason     → 回退提示 data-test="auto-match-fallback"

状态通过 window.__store.setState(partial, 'songMatch') 注入 (v7.11 测试钩子),
与 sing-song-select.feature 的 _inject_songs 同一模式 — 无需真实上传/后端匹配。

浏览器场景 — 需 Playwright + FastAPI :8000 服务 frontend/dist (base_url)。
"""
import pytest
from pytest_bdd import given, then, scenarios

# Mark all generated scenario tests as requiring the browser
pytestmark = pytest.mark.browser

# Auto-load all scenarios from the matching .feature file
scenarios('../features/compare-automatch.feature')


def _set_song_match_state(page, partial: dict) -> None:
    """通过 window.__store 注入 songMatch store 状态 (v7.11 钩子)."""
    page.evaluate(f'''
        if (window.__store) window.__store.setState({str(partial).replace("'", '"')}, 'songMatch');
    ''')


# ============================================================================
# Background
# ============================================================================

@given('对比分析页已加载')
def compare_page_loaded(page, base_url):
    """导航到 #/compare 并等待自动匹配区渲染 (Vue 3 CompareView)."""
    page.goto(base_url + '/#/compare')
    page.wait_for_selector('[data-test="auto-match-section"]', timeout=10000)
    page.wait_for_timeout(500)


# ============================================================================
# Given — 自动匹配结果状态 (store 注入)
# ============================================================================

@given('自动匹配已执行且失败')
def auto_match_failed(page):
    _set_song_match_state(page, {'error': '匹配服务不可用: 网络超时'})
    page.wait_for_timeout(300)


@given('自动匹配已执行且成功')
def auto_match_succeeded(page):
    _set_song_match_state(page, {
        'matchedSong': {
            'id': 'moon_love',
            'title': '月亮代表我的心',
            'artist': '邓丽君',
            'confidence': 0.87,
        },
        'candidates': [],
        'fallbackReason': '',
        'error': None,
    })
    page.wait_for_timeout(300)


@given('自动匹配已执行且无命中')
def auto_match_no_hit(page):
    _set_song_match_state(page, {
        'matchedSong': None,
        'candidates': [],
        'fallbackReason': 'no_match',
        'error': None,
    })
    page.wait_for_timeout(300)


# ============================================================================
# Then — 反馈可见性断言
# ============================================================================

@then('显示匹配错误告警 (data-test="auto-match-error")')
def auto_match_error_alert_visible(page):
    """H-B14 核心断言: store.error 必须可见 (修复前死信 ref 不渲染)."""
    alert = page.locator('[data-test="auto-match-error"]')
    assert alert.count() > 0, '匹配错误告警未显示 (H-B14: 死信 ref 未修复时此元素不渲染)'


@then('错误告警展示服务端错误信息')
def auto_match_error_text(page):
    alert = page.locator('[data-test="auto-match-error"]')
    assert alert.count() > 0, '匹配错误告警未显示'
    text = alert.first.text_content() or ''
    assert '匹配服务不可用' in text, f'错误告警未透传服务端错误信息: {text}'


@then('显示匹配命中徽标 (data-test="auto-match-hit")')
def auto_match_hit_badge_visible(page):
    badge = page.locator('[data-test="auto-match-hit"]')
    assert badge.count() > 0, '匹配命中徽标未显示'


@then('命中徽标展示匹配到的歌曲名')
def auto_match_hit_text(page):
    badge = page.locator('[data-test="auto-match-hit"]')
    assert badge.count() > 0, '匹配命中徽标未显示'
    text = badge.first.text_content() or ''
    assert '月亮代表我的心' in text, f'命中徽标未展示歌曲名: {text}'


@then('显示回退提示 (data-test="auto-match-fallback")')
def auto_match_fallback_visible(page):
    fallback = page.locator('[data-test="auto-match-fallback"]')
    assert fallback.count() > 0, '回退提示未显示 (无匹配时应优雅回退绝对评分)'


@then('不显示错误告警')
def auto_match_no_error_alert(page):
    alert = page.locator('[data-test="auto-match-error"]')
    assert alert.count() == 0, '不应显示匹配错误告警 (回退非错误)'
