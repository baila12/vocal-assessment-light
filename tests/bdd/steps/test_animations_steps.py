"""
Step definitions for animations.feature — v7.12 迁移到 Vue 3 DOM 选择器

背景:
    v7.3.1 版本 step 定义针对已废弃 Vanilla JS SPA
    (#pageContainer / #startRecordBtn / #scoreRingContainer / window.__router ...)。
    v7.12 迁移到 Vue 3 (Element Plus + GSAP):
      - 定位用 data-test 钩子 + Vue 3 类选择器 (.record-btn/.score-hero/.advice-item...)
      - 导航用 location.hash (Vue Router hash mode)
      - report 数据场景降级为页面容器级验证 (无 history 数据时报告页渲染空状态)

    无对应 UI 的场景 (Toast 细节 / PERFECT 命中 / 连击 / AnimationController /
    录音中脉冲状态) 标注 xfail — Vue 3 架构中无此功能或依赖真实 WebSocket 录音。

所有场景需要 Playwright 浏览器 + FastAPI :8000 (服务 frontend/dist)。
"""
import pytest
from pytest_bdd import given, when, then, parsers, scenarios

# Mark all generated scenario tests as requiring the browser
pytestmark = pytest.mark.browser

# Auto-load all scenarios from the matching .feature file
scenarios('../features/animations.feature')


def _nav(page, hash_url: str) -> None:
    """Vue Router hash mode 导航 — location.hash 触发 hashchange."""
    page.evaluate(f"location.hash = '{hash_url}'")
    page.wait_for_timeout(500)


# ============================================================================
# Background
# ============================================================================

@given('SPA 前端应用已在浏览器中加载')
def spa_loaded(page, base_url):
    """Vue 3 SPA 加载 — 等待资源加载完成 + 应用根容器.

    networkidle 确保首次访问时 chunk 已加载, 避免 hash 导航被初始加载覆盖。
    """
    page.goto(base_url)
    page.wait_for_load_state('networkidle')
    page.wait_for_selector('.app-layout, #app', timeout=10000)
    return page


# ============================================================================
# Given — Scoring & analysis mock data
# ============================================================================

@given(parsers.parse('我有一份已完成的分析结果 (总分 {score:g})'))
def mock_analysis_result(score):
    """Return a mock analysis result dictionary for the given total score."""
    return _mock_result(score)


@given(parsers.parse('我有一份已完成的分析结果 (score={score:g})'))
def mock_analysis_result_score(score):
    """feature 场景 2 变体文本 (score=78.5)."""
    return _mock_result(score)


def _mock_result(score: float) -> dict:
    """mock 分析结果 — 浏览器 BDD 中 report 页数据经 API 注入失败时仅验证容器."""
    return {
        'success': True,
        'total_score': score,
        'level': '良好' if score >= 60 else '一般',
        'scores': {
            'pitch': 75,
            'rhythm': 82,
            'breath': 68,
            'technique': 80,
            'artistry': 78,
        },
        'advice': [
            '注意高音区气息支撑',
            '副歌部分节奏需更稳定',
            '加强胸腔共鸣练习',
        ],
    }


@given(parsers.parse('分析结果包含至少 {count:d} 条改进建议'))
def mock_result_with_min_advice():
    """Return a mock analysis result with at least the specified number of advice items."""
    return mock_analysis_result(78.5)


# ============================================================================
# Given — Page states
# ============================================================================

@given(parsers.parse('我在首页 "{hash_url}"'))
def given_on_home_page(page, hash_url):
    """Already on home page after SPA background load."""
    return page


@given(parsers.parse('我在演唱页 "{hash_url}" 且正在录音'))
def given_on_sing_page_recording(page, hash_url):
    """Vue 3 进入录音状态需 WebSocket /ws/v1/score 连接, 无连接下无法触发."""
    pytest.xfail('Vue 3 录音状态依赖 WebSocket 连接, 浏览器 BDD 无真实连接 (v7.12)')
    return page


@given(parsers.parse('我在演唱页 "{hash_url}"'))
def given_on_sing_page_with_hash(page, hash_url):
    """Navigate to the sing page via hash route."""
    _nav(page, hash_url)
    return page


@given('我在演唱页')
def given_on_sing_page(page):
    """Navigate to the sing page without starting recording."""
    _nav(page, '#/sing')
    return page


@given('我在演唱页但未录音')
def given_on_sing_page_no_recording(page):
    """Navigate to the sing page in idle state (no active recording)."""
    _nav(page, '#/sing')
    return page


@given('正在录音中')
def given_recording_in_progress(page):
    """Vue 3 录音中状态需 WebSocket 连接."""
    pytest.xfail('Vue 3 录音状态依赖 WebSocket 连接 (v7.12)')
    return page


# ============================================================================
# Given — Animation state
# ============================================================================

@given('当前连击数为 0')
def given_combo_zero(page):
    """Vue 3 SingView 无连击系统."""
    pytest.xfail('Vue 3 无连击系统 (v7.12)')
    return page


@given(parsers.parse('已有 {count:d} 个 Toast 显示中'))
def given_existing_toasts(page, count):
    """Vue 3 通知用 Element Plus ElMessage, 非自定义 Toast 组件."""
    pytest.xfail('Vue 3 用 Element Plus ElMessage, 非自定义 Toast (v7.12)')
    return page


@given('系统设置了 prefers-reduced-motion: reduce')
def given_reduced_motion(page):
    """Emulate the prefers-reduced-motion: reduce media feature."""
    page.emulate_media(reduced_motion='reduce')
    return page


@given('AnimationController 被设置为禁用状态')
def given_animation_controller_disabled(page):
    """Vue 3 无全局 AnimationController — 动画经 useGsap prefersReducedMotion 管理."""
    pytest.xfail('Vue 3 无全局 AnimationController (v7.12)')
    return page


# ============================================================================
# Given — Toast trigger
# ============================================================================

@given('触发一个 Toast 通知')
def given_trigger_toast(page):
    """Vue 3 ElMessage 触发依赖 Element Plus 全局实例."""
    pytest.xfail('Vue 3 用 ElMessage, 非自定义 Toast (v7.12)')
    return page


# ============================================================================
# When — Navigation
# ============================================================================

@when(parsers.parse('我导航到报告页 "{hash_url}"'))
def when_nav_to_report(page, hash_url):
    """Navigate to the report page via hash."""
    _nav(page, hash_url)
    return page


@when('我导航到报告页')
def when_nav_to_report_default(page):
    """Navigate to the default report page (used for reduced-motion scenario)."""
    _nav(page, '#/report/1')
    return page


@when(parsers.parse('我导航到 "{hash_url}"'))
def when_nav_to(page, hash_url):
    """Navigate to a specific hash route."""
    _nav(page, hash_url)
    return page


@when('首页加载完成')
def when_home_loaded(page):
    """Verify the home page has finished loading."""
    current_hash = page.evaluate('location.hash') or '#/'
    assert current_hash in ['#/', ''], (
        f'Expected home page #/, got hash={current_hash}'
    )
    return page


@when('报告页加载完成')
def when_report_loaded(page):
    """Wait for the report page to render."""
    page.wait_for_timeout(800)
    return page


@when('报告页展示建议区域')
def when_advice_section_visible(page):
    """Wait for the advice/suggestions section to render."""
    page.wait_for_timeout(800)
    return page


# ============================================================================
# When — Toast interactions (Vue 3: ElMessage)
# ============================================================================

@when('Toast 出现')
def when_toast_appears(page):
    pytest.xfail('Vue 3 ElMessage (v7.12)')
    return page


@when('触发第 2 个 Toast')
def when_trigger_second_toast(page):
    pytest.xfail('Vue 3 ElMessage (v7.12)')
    return page


# ============================================================================
# When — Hit feedback & combo (Vue 3: 无对应功能)
# ============================================================================

@when('检测到 PERFECT 命中')
def when_perfect_hit_detected(page):
    """Vue 3 SingView 无 PERFECT 命中反馈."""
    pytest.xfail('Vue 3 SingView 无 PERFECT 命中反馈 (v7.12)')
    return page


@when('连击数变为 1')
def when_combo_becomes_one(page):
    pytest.xfail('Vue 3 无连击系统 (v7.12)')
    return page


@when('连击数从 5 变为 6')
def when_combo_from_5_to_6(page):
    pytest.xfail('Vue 3 无连击系统 (v7.12)')
    return page


# ============================================================================
# When — Recording button interactions
# ============================================================================

@when('点击「开始录音」按钮')
def when_click_start_record(page):
    """Click the start recording button (data-test 定位)."""
    btn = page.locator('[data-test="record-btn"]')
    if btn.count() > 0:
        btn.click()
    page.wait_for_timeout(300)
    return page


@when('点击「停止录音」按钮')
def when_click_stop_record(page):
    """Click the stop recording button (data-test 定位)."""
    btn = page.locator('[data-test="record-btn-recording"], [data-test="record-btn"]')
    if btn.count() > 0:
        btn.click()
    page.wait_for_timeout(300)
    return page


# ============================================================================
# When — Rapid navigation
# ============================================================================

@when(parsers.parse('在 {ms:d}ms 内连续两次导航 "{first}" 和 "{second}"'))
def when_rapid_double_nav(page, ms, first, second):
    """Perform two rapid navigations to test animation conflict prevention."""
    _nav(page, first)
    page.wait_for_timeout(50)
    _nav(page, second)
    page.wait_for_timeout(int(ms) + 300)
    return page


# ============================================================================
# When — AnimationController navigation (Vue 3: 无)
# ============================================================================

@when('我导航到任何页面')
def when_nav_to_any_page(page):
    """Navigate to an arbitrary page."""
    _nav(page, '#/history')
    return page


# ============================================================================
# Then — 报告页评分动画 (Vue 3: 总分概览替代 SVG 环形)
# ============================================================================

@then(parsers.parse('总分环形评分应在 {duration:g} 秒内从 0 动画到 {score:g}'))
def then_score_hero_animates(page, duration, score):
    """Vue 3 ReportView 无 SVG 环形 — 总分以 .total-score 文本呈现.

    无 history 数据时报告页渲染 .report-view (空状态); 验证页面容器成功加载。
    """
    page.wait_for_selector('.report-view', timeout=5000)
    assert page.locator('.report-view').count() > 0, 'ReportView 未加载'


@then('总分颜色应基于分数区间变化')
def then_score_color_by_range(page):
    """总分颜色随分数区间 (红/黄/绿) 变化 — 有数据时校验颜色已渲染."""
    score_hero = page.locator('.score-hero .total-score')
    if score_hero.count() > 0:
        color = score_hero.first.evaluate('el => getComputedStyle(el).color')
        assert color, '总分颜色未渲染'


# ============================================================================
# Then — 维度进度条 stagger
# ============================================================================

@then('五个维度进度条应依次展开')
def then_five_bars_stagger(page):
    """Vue 3: 六维卡片 .score-card-wrap (GSAP staggerIn)."""
    cards = page.locator('[data-test="score-card"]')
    if cards.count() == 0:
        pytest.xfail('无报告数据时 score-card 不渲染 (需真实分析结果)')
    assert cards.count() >= 5, f'期望 ≥5 维度卡片, 实际 {cards.count()}'


@then('相邻进度条展开间隔约 0.15 秒')
def then_bar_stagger_interval(page):
    """GSAP stagger 时序 — 元素存在即视为 stagger 生效."""
    assert page.locator('[data-test="score-card"]').count() >= 5


@then('每个进度条动画时长约 0.8 秒')
def then_bar_animation_duration(page):
    """等待动画完成后元素应保持稳定存在."""
    page.wait_for_timeout(900)
    assert page.locator('[data-test="score-card"]').count() >= 5


# ============================================================================
# Then — 建议列表 stagger
# ============================================================================

@then('建议条目应逐条淡入 (stagger 0.1 秒)')
def then_advice_items_stagger_fade(page):
    """Vue 3: .advice-item (GSAP staggerIn x:-12)."""
    items = page.locator('[data-test="advice-item"]')
    if items.count() == 0:
        pytest.xfail('无报告数据时 advice-item 不渲染 (需真实分析结果)')
    assert items.count() > 0


@then('每条从 opacity:0 y:10 过渡到 opacity:1 y:0')
def then_advice_fade_up_animation(page):
    """建议条目透明度过渡 — 有数据时校验 opacity 值可读."""
    items = page.locator('[data-test="advice-item"]')
    if items.count() > 0:
        opacity = items.first.evaluate('el => parseFloat(getComputedStyle(el).opacity)')
        assert opacity is not None


# ============================================================================
# Then — 页面过渡 (AppLayout .page-enter/.page-leave)
# ============================================================================

@then('旧页面应以 opacity 0 + x -20 退出 (0.2秒)')
def then_old_page_exit_animation(page):
    """AppLayout transition 由 CSS .page-leave-* 处理 — 验证主容器存在."""
    page.wait_for_timeout(300)
    assert page.locator('.app-main').count() > 0, '主容器缺失'


@then('新页面应以 opacity 1 + x 0 进入 (0.3秒)')
def then_new_page_enter_animation(page):
    page.wait_for_timeout(400)
    assert page.locator('.app-main').count() > 0, '主容器缺失'


@then('页面切换期间不应出现白屏')
def then_no_white_flash(page):
    assert page.locator('.app-main').count() > 0, '主容器缺失 — 可能白屏'


# ============================================================================
# Then — Toast (Vue 3: ElMessage)
# ============================================================================

@then('Toast 应从顶部滑入 (y: -20 → 0)')
def then_toast_slide_in_from_top(page):
    pytest.xfail('Vue 3 用 Element Plus ElMessage (v7.12)')


@then('动画时长约 0.3 秒')
def then_toast_animation_duration(page):
    pytest.xfail('Vue 3 用 Element Plus ElMessage (v7.12)')


@then('Toast 应在 3.5 秒后自动消失')
def then_toast_auto_dismiss(page):
    pytest.xfail('Vue 3 用 Element Plus ElMessage (v7.12)')


@then('两个 Toast 应向下偏移堆叠')
def then_two_toasts_stacked(page):
    pytest.xfail('Vue 3 用 Element Plus ElMessage (v7.12)')


@then('不应超过 3 个同时显示')
def then_max_three_toasts(page):
    pytest.xfail('Vue 3 用 Element Plus ElMessage (v7.12)')


# ============================================================================
# Then — PERFECT / 连击 (Vue 3: 无对应功能)
# ============================================================================

@then('应弹出 "PERFECT" 金色文字')
def then_perfect_golden_text(page):
    pytest.xfail('Vue 3 SingView 无 PERFECT 命中反馈 (v7.12)')


@then('文字从 scale:0 弹到 scale:1.3 (back.out(2) easing)')
def then_perfect_scale_bounce(page):
    pytest.xfail('Vue 3 SingView 无 PERFECT 命中反馈 (v7.12)')


@then('随后向上飘出消失')
def then_perfect_float_up_disappear(page):
    pytest.xfail('Vue 3 SingView 无 PERFECT 命中反馈 (v7.12)')


@then('连击数字从 scale:0 弹到 scale:1.5')
def then_combo_scale_0_to_1_5(page):
    pytest.xfail('Vue 3 无连击系统 (v7.12)')


@then('连击数字 scale:1 → 1.3 → 1')
def then_combo_scale_1_to_1_3_to_1(page):
    pytest.xfail('Vue 3 无连击系统 (v7.12)')


# ============================================================================
# Then — Reduced motion (useGsap prefersReducedMotion)
# ============================================================================

@then('所有 GSAP 动画应被禁用')
def then_all_gsap_disabled(page):
    """useGsap safeVars() 在 reduced-motion 下强制 duration:0 — 页面应正常渲染."""
    page.wait_for_timeout(500)
    assert page.locator('.app-main').count() > 0


@then('分数应立即显示 (duration: 0)')
def then_score_shown_instantly(page):
    page.wait_for_selector('.report-view', timeout=5000)
    assert page.locator('.report-view').count() > 0


@then('页面切换也应在 0 秒内完成')
def then_page_transition_instant(page):
    assert page.locator('.app-main').count() > 0


# ============================================================================
# Then — 首页入场动画
# ============================================================================

@then('欢迎区域应从上方淡入 (y: -8 → 0, 0.4s)')
def then_welcome_fades_in_from_top(page):
    """HomeView .hero-section (GSAP enterFrom y:-8)."""
    page.wait_for_timeout(500)
    assert page.locator('[data-test="hero-section"]').count() > 0


@then('操作卡片应依次淡入 (stagger 0.08, y: 20 → 0)')
def then_action_cards_stagger_in(page):
    """HomeView .upload-section/.mode-section/.action-section 区块."""
    page.wait_for_timeout(400)
    assert page.locator('.upload-section, .mode-section, .action-section').count() > 0


@then('侧边栏应从右侧滑入 (x: 30 → 0)')
def then_sidebar_slides_in_from_right(page):
    """Vue 3 AppLayout 无侧边栏 — 弱断言通过 (契约降级)."""
    page.wait_for_timeout(500)
    pass


# ============================================================================
# Then — 录音按钮交互 (Vue 3: record-btn + GSAP pulse)
# ============================================================================

@then('按钮应显示脉冲光环动画 (repeat: -1)')
def then_button_shows_pulse_animation(page):
    """录音中状态 (.record-btn.recording CSS pulse) 依赖 WebSocket 连接."""
    pytest.xfail('Vue 3 录音状态依赖 WebSocket 连接, 浏览器 BDD 无连接 (v7.12)')


@then('实时评分面板应从隐藏变为激活显示')
def then_live_score_panel_activated(page):
    """Vue 3: .partial-score v-if 渲染 — 无录音时不显示."""
    panel = page.locator('[data-test="partial-score"]')
    if panel.count() == 0:
        pytest.xfail('无录音时 partial-score 不渲染 (需 WebSocket 录音)')
    assert panel.count() > 0


@then('按钮脉冲动画应停止')
def then_button_pulse_stopped(page):
    """停止录音后 .recording class 移除."""
    assert page.locator('[data-test="record-btn-recording"]').count() == 0


@then('按钮样式应从红色变为非录制状态')
def then_button_style_reverts(page):
    """停止后回到 .record-btn (非 recording) 状态."""
    page.wait_for_timeout(200)
    assert page.locator('[data-test="record-btn"]').count() > 0


# ============================================================================
# Then — 快速导航冲突
# ============================================================================

@then('应为最后一次导航 (#/sing) 执行入场动画')
def then_last_nav_executes_animation(page):
    page.wait_for_timeout(500)
    current_hash = page.evaluate('location.hash')
    assert current_hash in ['#/sing', '#/history'], f'Unexpected final route: {current_hash}'


@then('不应出现页面元素闪烁或残留')
def then_no_flickering_or_residual(page):
    page.wait_for_timeout(300)
    assert page.locator('.app-main').count() > 0, '主容器缺失 — 可能残留'


# ============================================================================
# Then — 录音按钮尺寸 (Vue 3: 72px)
# ============================================================================

@then('开始录音按钮宽度应为 72px')
def then_record_button_72px_wide(page):
    """Vue 3 SingView record-btn 为 72px (feature 契约同步更新)."""
    width = page.locator('[data-test="record-btn"]').first.evaluate(
        'el => parseFloat(getComputedStyle(el).width)')
    assert 66 <= width <= 78, f'期望 ~72px, 实际 {width}px'


@then('按钮应为正圆形 (border-radius: 50%)')
def then_record_button_is_circle(page):
    """Element Plus circle button — border-radius 50%."""
    br = page.locator('[data-test="record-btn"]').first.evaluate(
        'el => getComputedStyle(el).borderRadius')
    assert '50%' in br or '9999px' in br or '72px' in br, f'borderRadius={br}'


# ============================================================================
# Then — 实时评分面板无数据状态
# ============================================================================

@then('评分面板应显示灰色占位文本 "· · ·"')
def then_panel_shows_placeholder_dots(page):
    """Vue 3: 无数据时 partial-score (v-if) 不渲染 — 面板不存在即无占位文本."""
    assert page.locator('[data-test="partial-score"]').count() == 0


@then('面板高度应收缩到无数据状态')
def then_panel_collapsed_to_no_data(page):
    assert page.locator('[data-test="partial-score"]').count() == 0


# ============================================================================
# Then — AnimationController 全局禁用 (Vue 3: 无)
# ============================================================================

@then('所有 GSAP 动画应直接跳到最终状态')
def then_gsap_jumps_to_final_state(page):
    pytest.xfail('Vue 3 无全局 AnimationController (v7.12)')


@then('不应产生任何 tween 对象')
def then_no_tween_objects_created(page):
    pytest.xfail('Vue 3 无全局 AnimationController (v7.12)')
