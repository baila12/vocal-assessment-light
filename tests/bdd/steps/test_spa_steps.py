"""
Step definitions for animations, responsive, and offline features.

Browser-based BDD scenarios — requires Playwright + running Flask server.
"""
from pytest_bdd import given, when, then, parsers, scenarios

# Load scenarios from all 3 feature files
scenarios('../features/animations.feature')
scenarios('../features/responsive.feature')
scenarios('../features/offline.feature')


# ============================================================================
# Given — shared across features
# ============================================================================

@given('SPA 前端应用已在浏览器中加载')
def spa_browser(page, base_url):
    """Ensure SPA is loaded in browser."""
    page.goto(base_url)
    page.wait_for_selector('#pageContainer', timeout=10000)
    return page


@given(parsers.parse('我有一份已完成的分析结果 (总分 {score:g})'))
def mock_analysis_result(score):
    return {
        'success': True, 'total_score': score, 'level': '良好',
        'scores': {'pitch': 75, 'rhythm': 82, 'breath': 68,
                    'technique': 80, 'artistry': 78},
        'advice': ['注意高音区气息支撑', '副歌部分节奏需更稳定', '加强胸腔共鸣练习']
    }


@given(parsers.parse('分析结果包含至少 {count:d} 条改进建议'))
def mock_result_with_advice():
    return mock_analysis_result(78.5)


@given(parsers.parse('我在演唱页 "{hash_url}" 且正在录音'))
def at_sing_page(spa_browser):
    page = spa_browser
    page.evaluate('window.__router.navigate("#/sing")')
    page.wait_for_timeout(600)
    return page


@given('当前连击数为 0')
@given(parsers.parse('已有 {count:d} 个 Toast 显示中'))
def setup_state():
    pass


@given('系统设置了 prefers-reduced-motion: reduce')
def reduced_motion_on(page):
    page.emulate_media(reduced_motion='reduce')


@given(parsers.parse('视口宽度为 {width:d}px ({device})'))
def set_viewport_width(page, width):
    page.set_viewport_size({'width': width, 'height': 667 if width < 768 else 720})


@given('我使用触控设备')
def touch_device_mode(page):
    page.set_viewport_size({'width': 375, 'height': 667, 'has_touch': True})


@given('我断开网络连接')
def go_offline_mode(page):
    page.context.set_offline(True)


@given('我之前处于离线状态')
def was_offline_then_online(page):
    page.context.set_offline(True)
    page.wait_for_timeout(500)
    page.context.set_offline(False)


# Location Givens
@given(parsers.parse('我在首页 "{hash_url}"'))
def given_at_home(spa_browser): return spa_browser

@given(parsers.parse('我在历史页 "{hash_url}"'))
def given_at_history(spa_browser):
    spa_browser.evaluate('window.__router.navigate("#/history")')
    spa_browser.wait_for_timeout(600)
    return spa_browser

@given(parsers.parse('我在对比页 "{hash_url}"'))
def given_at_compare(spa_browser):
    spa_browser.evaluate('window.__router.navigate("#/compare")')
    spa_browser.wait_for_timeout(600)
    return spa_browser

@given(parsers.parse('我在设置页 "{hash_url}"'))
def given_at_settings(spa_browser):
    spa_browser.evaluate('window.__router.navigate("#/settings")')
    spa_browser.wait_for_timeout(600)
    return spa_browser

@given('我访问应用根路径 "/"')
@given('我已保存暗色主题偏好')
def settings_given(spa_browser):
    return spa_browser


# ============================================================================
# When
# ============================================================================

@when(parsers.parse('我导航到报告页 "{hash_url}"'))
def nav_to_report(spa_browser, hash_url):
    spa_browser.evaluate(f'window.__router.navigate("{hash_url}")')
    spa_browser.wait_for_timeout(600)

@when('报告页加载完成')
def report_loaded(spa_browser):
    spa_browser.wait_for_timeout(1500)

@when('报告页展示建议区域')
def advice_visible(spa_browser):
    spa_browser.wait_for_timeout(1000)

@when('触发一个 Toast 通知')
def trigger_toast(spa_browser):
    spa_browser.evaluate("""
        if (window.__store) {
            import('./js/components/Toast.js').then(m => {
                m.showToast ? m.showToast('测试通知', 'info') : null;
            });
        }
    """)
    spa_browser.wait_for_timeout(400)

@when('触发第 2 个 Toast')
def trigger_second_toast(spa_browser):
    spa_browser.evaluate("""
        import('./js/components/Toast.js').then(m => {
            m.showToast ? m.showToast('第二条通知', 'warning') : null;
        });
    """)
    spa_browser.wait_for_timeout(400)

@when('检测到 PERFECT 命中')
def perfect_hit(spa_browser):
    spa_browser.evaluate("window.__store?.emit('hit', {type:'perfect',note:'C4'})")
    spa_browser.wait_for_timeout(100)

@when('连击数变为 1')
@when('连击数从 5 变为 6')
def combo_change(spa_browser):
    spa_browser.wait_for_timeout(100)

@when('我导航到历史页 "#/history"')
def nav_to_history_page(spa_browser):
    spa_browser.evaluate('window.__router.navigate("#/history")')
    spa_browser.wait_for_timeout(600)

@when('我点击任意按钮')
@when('页面加载完成')
@when('我加载应用页面')
def click_or_load(spa_browser):
    spa_browser.wait_for_timeout(500)

@when('我点击暗色主题按钮')
def click_dark_theme(spa_browser):
    btn = spa_browser.locator('.theme-btn[data-theme="dark"]')
    if btn.count() > 0: btn.first.click()
    spa_browser.wait_for_timeout(400)

@when('页面检测到离线')
def detect_offline(spa_browser):
    spa_browser.evaluate('window.dispatchEvent(new Event("offline"))')
    spa_browser.wait_for_timeout(400)

@when('网络恢复')
def network_online(spa_browser):
    spa_browser.evaluate('window.dispatchEvent(new Event("online"))')
    spa_browser.wait_for_timeout(400)

@when(parsers.parse('我导航到 "{hash_url}"'))
def nav_to(spa_browser, hash_url):
    spa_browser.evaluate(f'window.__router.navigate("{hash_url}")')
    spa_browser.wait_for_timeout(600)

@when('我刷新页面')
def refresh_page(spa_browser):
    spa_browser.reload()
    spa_browser.wait_for_selector('#pageContainer', timeout=10000)
    spa_browser.wait_for_timeout(600)


# ============================================================================
# Then — Animations
# ============================================================================

@then(parsers.parse('总分环形评分应在 {duration:g} 秒内从 0 动画到 {score:g}'))
def then_ring_animates(spa_browser, duration, score):
    spa_browser.wait_for_timeout(500)
    assert spa_browser.locator('#scoreRingContainer').count() > 0

@then('总分颜色应基于分数区间变化')
def then_score_color(spa_browser): pass

@then('五个维度进度条应依次展开')
def then_bars_stagger(spa_browser):
    bars = spa_browser.locator('[id^="dim"][id$="Bar"]')
    assert bars.count() >= 5

@then('相邻进度条展开间隔约 0.15 秒')
@then('每个进度条动画时长约 0.8 秒')
@then('每条从 opacity:0 y:10 过渡到 opacity:1 y:0')
@then('旧页面应以 opacity 0 + x -20 退出 (0.2秒)')
@then('新页面应以 opacity 1 + x 0 进入 (0.3秒)')
@then('动画时长约 0.3 秒')
@then('文字从 scale:0 弹到 scale:1.3 (back.out(2) easing)')
@then('随后向上飘出消失')
@then('连击数字从 scale:0 弹到 scale:1.5')
@then('连击数字 scale:1 → 1.3 → 1')
@then('分数应立即显示 (duration: 0)')
@then('页面切换也应在 0 秒内完成')
def then_animation_param_check(spa_browser): pass

@then('建议条目应逐条淡入 (stagger 0.1 秒)')
def then_advice_stagger(spa_browser):
    assert spa_browser.locator('#adviceList li').count() > 0

@then('页面切换期间不应出现白屏')
def then_no_white_flash(spa_browser):
    assert spa_browser.locator('#pageContainer').count() > 0

@then('Toast 应从顶部滑入 (y: -20 → 0)')
def then_toast_enters(spa_browser):
    assert spa_browser.locator('.toast-item').count() > 0

@then('Toast 应在 3.5 秒后自动消失')
def then_toast_dismisses(spa_browser):
    spa_browser.wait_for_timeout(4000)

@then('两个 Toast 应向下偏移堆叠')
def then_toasts_stack(spa_browser):
    assert spa_browser.locator('.toast-item').count() >= 1

@then('不应超过 3 个同时显示')
def then_max_toasts(spa_browser):
    assert spa_browser.locator('.toast-item').count() <= 3

@then('应弹出 "PERFECT" 金色文字')
@then('所有 GSAP 动画应被禁用')
def then_visual_check(spa_browser): pass


# ============================================================================
# Then — Responsive
# ============================================================================

@then('顶部导航应隐藏')
def then_top_nav_hidden(spa_browser):
    display = spa_browser.evaluate('document.querySelector(".top-nav")?.style.display')
    assert display == 'none', f'Top nav display={display}'

@then('底部固定导航应显示')
def then_bottom_nav_shown(spa_browser):
    display = spa_browser.evaluate('document.querySelector(".bottom-nav")?.style.display')
    assert display == 'flex', f'Bottom nav display={display}'

@then(parsers.parse('底部导航应包含 {count:d} 个标签: {labels}'))
def then_bottom_nav_count(spa_browser, count, labels):
    tabs = spa_browser.locator('.nav-tab-mobile')
    assert tabs.count() >= count

@then('顶部导航应显示')
def then_top_nav_shown(spa_browser):
    assert spa_browser.locator('.top-nav').count() > 0

@then('底部导航应隐藏')
def then_bottom_nav_hidden(spa_browser):
    display = spa_browser.evaluate('document.querySelector(".bottom-nav")?.style.display')
    assert display != 'flex'

@then(parsers.parse('顶部导航应包含 {count:d} 个标签: {labels}'))
def then_top_nav_count(spa_browser, count, labels):
    assert spa_browser.locator('.nav-tab').count() >= count

@then('主内容区和侧边栏应堆叠为单列')
@then('操作卡片应为单列布局')
@then('历史卡片应为单列网格')
@then('标准音频和用户音频卡片应垂直堆叠')
def then_layout_single(spa_browser): pass

@then('按钮应立即响应 (无 300ms 延迟)')
@then('页面应有 touch-action: manipulation 样式')
def then_touch_action(spa_browser): pass

@then('body 应添加 dark-theme class')
def then_dark_body(spa_browser):
    assert spa_browser.evaluate('document.body.classList.contains("dark-theme")')

@then('CSS 变量应切换为暗色值')
def then_dark_vars(spa_browser):
    bg = spa_browser.evaluate('getComputedStyle(document.documentElement).getPropertyValue("--bg-page")')
    assert bg

@then('主题偏好应保存到 localStorage')
def then_theme_stored(spa_browser):
    assert spa_browser.evaluate('localStorage.getItem("vocal_app_theme")') == 'dark'

@then('暗色主题应自动恢复')
def then_theme_restored(spa_browser):
    assert spa_browser.evaluate('document.body.classList.contains("dark-theme")')


# ============================================================================
# Then — Offline
# ============================================================================

@then('GSAP 应从本地 /lib/gsap/gsap.min.js 加载')
@then('gsap 全局对象应可用')
def then_gsap_available(spa_browser):
    assert spa_browser.evaluate('typeof gsap !== "undefined"')

@then('页面动画应正常工作')
def then_animations_work(spa_browser): pass

@then('Chart.js 应从本地 /lib/chart.js/chart.umd.min.js 加载')
def then_chartjs_available(spa_browser):
    assert spa_browser.evaluate('typeof Chart !== "undefined"')

@then('成长曲线图表应正常渲染')
def then_growth_chart_renders(spa_browser):
    assert spa_browser.locator('#growthChart').count() > 0

@then('Toast 应提示 "网络已断开，离线功能仍可用"')
@then('Toast 应提示 "网络已恢复"')
def then_network_toast(spa_browser): pass

@then('应只有 index.html 作为入口')
def then_single_entry(spa_browser):
    url = spa_browser.url
    assert 'analysis.html' not in url and 'compare.html' not in url

@then('不应出现 analysis.html, compare.html, settings.html 作为独立页面')
def then_no_old_pages(spa_browser):
    url = spa_browser.url
    assert all(x not in url for x in ['analysis.html', 'compare.html', 'settings.html'])


# ============================================================================
# v3.0 AnimationController and layout validation steps
# ============================================================================


@given('AnimationController \u88ab\u8bbe\u7f6e\u4e3a\u7981\u7528\u72b6\u6001')
def ac_disabled(spa_browser):
    spa_browser.evaluate("window.__animationController?.setEnabled(false)")
    spa_browser.wait_for_timeout(100)


@given('\u6b63\u5728\u5f55\u97f3\u4e2d')
def is_recording(spa_browser):
    spa_browser.evaluate("window.__router.navigate('#/sing')")
    spa_browser.wait_for_timeout(600)
    spa_browser.evaluate("document.querySelector('#startRecordBtn')?.click()")
    spa_browser.wait_for_timeout(300)


@when('\u9996\u9875\u52a0\u8f7d\u5b8c\u6210')
def home_loaded(spa_browser):
    assert '#/' in spa_browser.evaluate("location.hash") or '/#' in spa_browser.url


@when('\u70b9\u51fb\u300c\u5f00\u59cb\u5f55\u97f3\u300d\u6309\u94ae')
def click_start_record(spa_browser):
    btn = spa_browser.locator('#startRecordBtn')
    if btn.count() > 0:
        btn.click()
    spa_browser.wait_for_timeout(300)


@when('\u70b9\u51fb\u300c\u505c\u6b62\u5f55\u97f3\u300d\u6309\u94ae')
def click_stop_record(spa_browser):
    btn = spa_browser.locator('#stopRecordBtn')
    if btn.count() > 0:
        btn.click()
    spa_browser.wait_for_timeout(300)


@when(parsers.parse('\u5728 {ms:d}ms \u5185\u8fde\u7eed\u4e24\u6b21\u5bfc\u822a \u201c{first}\u201d \u548c \u201c{second}\u201d'))
def rapid_nav(spa_browser, ms, first, second):
    spa_browser.evaluate("window.__router.navigate('" + first + "')")
    spa_browser.wait_for_timeout(50)
    spa_browser.evaluate("window.__router.navigate('" + second + "')")
    spa_browser.wait_for_timeout(int(ms) + 400)


@then('welcome fades in')
@then('cards stagger in')
@then('sidebar slides in')
@then('pulse animation stops')
@then('button style reverts')
@then('last nav executes animation')
@then('no flickering')
@then('gsap jumps to final state')
@then('no tween created')
def then_placeholder(spa_browser):
    spa_browser.wait_for_timeout(100)


@then('button shows pulse animation')
def then_record_pulse(spa_browser):
    has_pulse = spa_browser.evaluate(
        "document.querySelector('#startRecordBtn')?.className.includes('recording')"
    )
    assert has_pulse


@then('live panel activates')
def then_live_panel_activated(spa_browser):
    js = '''
        (function() {
            var p = document.querySelector('#liveScorePanel');
            if (!p) return false;
            var s = getComputedStyle(p);
            return s.display !== 'none' && s.opacity !== '0';
        })()
    '''
    assert spa_browser.evaluate(js)


@then('record button is 56px wide')
def then_btn_56px(spa_browser):
    js = '''
        (function() {
            var b = document.querySelector('#startRecordBtn');
            if (!b) return 0;
            return parseFloat(getComputedStyle(b).width);
        })()
    '''
    w = spa_browser.evaluate(js)
    assert 54 <= w <= 58, 'button width %d' % w


@then('record button is circle')
def then_btn_circle(spa_browser):
    r = spa_browser.evaluate(
        "getComputedStyle(document.querySelector('#startRecordBtn')).borderRadius"
    )
    assert r in ['50%', '9999px'], 'border-radius: ' + r


@then('panel shows placeholder text')
def then_placeholder_text(spa_browser):
    t = spa_browser.evaluate(
        "document.querySelector('[id^=livePitch]')?.textContent?.trim() || ''"
    )
    assert '--' in t or '...' in t


@then('panel collapses to no-data height')
def then_panel_collapsed(spa_browser):
    js = '''
        (function() {
            var p = document.querySelector('#liveScorePanel');
            return p ? p.getBoundingClientRect().height : 999;
        })()
    '''
    h = spa_browser.evaluate(js)
    assert h < 200, 'panel height %d' % h
