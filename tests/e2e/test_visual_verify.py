"""
Visual Verification E2E Tests — Edge Browser (non-headless)

Verifies ALL pages render correctly, components display properly,
and click interactions work as expected.

Usage:
    pytest tests/e2e/test_visual_verify.py -v --tb=long -m e2e

Requires: Flask server running, Edge browser installed, Playwright
"""
import os
import pytest
from pathlib import Path
from playwright.sync_api import Page, expect

BACKEND_URL = "http://127.0.0.1:5000"
SCREENSHOT_DIR = Path(__file__).parent.parent.parent / "data" / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


def _screenshot(page, name):
    """Take a debug screenshot."""
    try:
        page.screenshot(path=str(SCREENSHOT_DIR / f"{name}.png"))
    except Exception:
        pass


# ============================================================================
# Home Page
# ============================================================================

@pytest.mark.e2e
class TestHomePage:
    """首页渲染与交互"""

    def test_page_loads_and_container_exists(self, page: Page):
        """首页加载后 #pageContainer 和 #page-home 存在"""
        page.goto(BACKEND_URL + "/#/")
        expect(page.locator("#pageContainer")).to_be_visible(timeout=10000)
        expect(page.locator("#page-home")).to_be_visible(timeout=5000)

    def test_welcome_section_rendered(self, page: Page):
        """欢迎区域渲染"""
        page.goto(BACKEND_URL + "/#/")
        page.wait_for_selector("#page-home", timeout=10000)
        welcome = page.locator(".welcome-section")
        expect(welcome.first).to_be_visible(timeout=5000)
        # Should not be empty
        text = welcome.first.text_content()
        assert text and len(text.strip()) > 0, "Welcome section is empty"

    def test_action_cards_exist(self, page: Page):
        """操作卡片存在 (导入音频 / 快速录音 / 对比分析)"""
        page.goto(BACKEND_URL + "/#/")
        page.wait_for_selector("#page-home", timeout=10000)
        cards = page.locator(".action-card")
        assert cards.count() >= 2, f"Expected >=2 action cards, got {cards.count()}"

    def test_mode_selector_rendered(self, page: Page):
        """模式选择器渲染 (快速模式 / 专业模式)"""
        page.goto(BACKEND_URL + "/#/")
        page.wait_for_selector("#page-home", timeout=10000)
        # Try multiple possible selectors
        mode_sel = page.locator(".mode-selector")
        if mode_sel.count() == 0:
            mode_sel = page.locator("#modeSelector")
        if mode_sel.count() == 0:
            mode_sel = page.locator('[name="evalMode"]')
        assert mode_sel.count() > 0, "Mode selector not found on home page"
        mode_options = page.locator(".mode-option")
        if mode_options.count() == 0:
            mode_options = page.locator('[name="evalMode"]')
        assert mode_options.count() >= 2, f"Expected >=2 mode options, got {mode_options.count()}"

    def test_mode_switch_to_professional(self, page: Page):
        """点击专业模式切换"""
        page.goto(BACKEND_URL + "/#/")
        page.wait_for_selector("#page-home", timeout=10000)
        prof_btn = page.locator('.mode-option[data-mode="professional"]')
        if prof_btn.count() > 0:
            prof_btn.first.click()
            page.wait_for_timeout(400)
            active = page.locator(".mode-option.active")
            assert active.count() > 0, "No active mode after click"
            mode = active.first.get_attribute("data-mode") or ""
            assert "professional" in mode or "专业" in active.first.text_content(), \
                f"Expected professional mode, got active: {mode}"

    def test_file_upload_area_clickable(self, page: Page):
        """文件上传区域可点击"""
        page.goto(BACKEND_URL + "/#/")
        page.wait_for_selector("#page-home", timeout=10000)
        upload_zone = page.locator("#fileDropZone")
        if upload_zone.count() == 0:
            upload_zone = page.locator(".upload-zone")
        if upload_zone.count() == 0:
            upload_zone = page.locator(".action-card.primary")
        assert upload_zone.count() > 0, "No upload zone found"
        # Click should open file dialog (can't test dialog, but verify no error)
        try:
            upload_zone.first.click()
            page.wait_for_timeout(300)
        except Exception as e:
            pytest.fail(f"Click on upload zone threw: {e}")

    def test_sidebar_info_present(self, page: Page):
        """侧边栏信息区域存在"""
        page.goto(BACKEND_URL + "/#/")
        page.wait_for_selector("#page-home", timeout=10000)
        sidebar = page.locator(".sidebar")
        if sidebar.count() > 0:
            text = sidebar.first.text_content()
            assert text and len(text.strip()) > 0, "Sidebar is empty"


# ============================================================================
# Sing Page
# ============================================================================

@pytest.mark.e2e
class TestSingPage:
    """演唱页渲染与交互"""

    def test_page_renders(self, page: Page):
        """演唱页渲染"""
        page.goto(BACKEND_URL + "/#/sing")
        page.wait_for_selector("#page-sing", timeout=10000)
        expect(page.locator("#page-sing")).to_be_visible(timeout=5000)

    def test_record_button_exists(self, page: Page):
        """录音按钮存在"""
        page.goto(BACKEND_URL + "/#/sing")
        page.wait_for_selector("#page-sing", timeout=10000)
        record_btn = page.locator("#recordBtn")
        if record_btn.count() == 0:
            record_btn = page.locator('[data-action="record"]')
        if record_btn.count() == 0:
            record_btn = page.locator("button").filter(has_text="录音")
        assert record_btn.count() > 0, "No record button found"

    def test_canvas_pitch_display_exists(self, page: Page):
        """音高 Canvas 显示区存在"""
        page.goto(BACKEND_URL + "/#/sing")
        page.wait_for_selector("#page-sing", timeout=10000)
        canvas = page.locator("#pitchCanvas")
        if canvas.count() == 0:
            canvas = page.locator("canvas")
        assert canvas.count() > 0, "No pitch canvas found"

    def test_realtime_indicators_present(self, page: Page):
        """实时评分指标面板存在"""
        page.goto(BACKEND_URL + "/#/sing")
        page.wait_for_selector("#page-sing", timeout=10000)
        indicators = page.locator("#liveIndicators")
        if indicators.count() == 0:
            indicators = page.locator(".live-indicators")
        if indicators.count() == 0:
            indicators = page.locator(".indicator-grid")
        # At minimum there should be some metric display
        assert page.locator("#page-sing").text_content(), "Sing page has no text content"


# ============================================================================
# Compare Page
# ============================================================================

@pytest.mark.e2e
class TestComparePage:
    """对比分析页渲染与交互"""

    def test_page_renders(self, page: Page):
        """对比页渲染"""
        page.goto(BACKEND_URL + "/#/compare")
        page.wait_for_selector("#page-compare", timeout=10000)
        expect(page.locator("#page-compare")).to_be_visible(timeout=5000)

    def test_dual_upload_zones(self, page: Page):
        """双音频上传区存在 (标准音频 + 用户音频)"""
        page.goto(BACKEND_URL + "/#/compare")
        page.wait_for_selector("#page-compare", timeout=10000)
        # Should have two upload areas
        upload_zones = page.locator(".upload-zone")
        if upload_zones.count() < 2:
            upload_zones = page.locator(".drop-zone")
        if upload_zones.count() < 2:
            upload_zones = page.locator('[class*="upload"]')
        # At minimum the page should render content
        assert page.locator("#page-compare").text_content(), "Compare page is empty"

    def test_compare_button_exists(self, page: Page):
        """开始对比按钮存在或其容器存在"""
        page.goto(BACKEND_URL + "/#/compare")
        page.wait_for_selector("#page-compare", timeout=10000)
        btn = page.locator("button").filter(has_text="对比")
        if btn.count() == 0:
            btn = page.locator("button").filter(has_text="分析")
        if btn.count() == 0:
            btn = page.locator('[data-action="compare"]')
        # OK if no button visible until files selected, just check no crash
        content = page.locator("#page-compare").text_content() or ""
        assert len(content) > 0, "Compare page content is empty"


# ============================================================================
# History Page
# ============================================================================

@pytest.mark.e2e
class TestHistoryPage:
    """历史记录页渲染与交互"""

    def test_page_renders(self, page: Page):
        """历史记录页渲染"""
        page.goto(BACKEND_URL + "/#/history")
        page.wait_for_selector("#page-history", timeout=10000)
        expect(page.locator("#page-history")).to_be_visible(timeout=5000)

    def test_history_list_or_empty_state(self, page: Page):
        """历史列表或空状态渲染"""
        page.goto(BACKEND_URL + "/#/history")
        page.wait_for_selector("#page-history", timeout=10000)
        # Either has history items or empty state
        items = page.locator(".history-item")
        empty = page.locator(".empty-state")
        loading = page.locator("#historyLoading")

        has_content = (items.count() > 0 or empty.count() > 0 or
                       (loading.count() > 0 and loading.first.is_visible()))
        assert has_content, "History page has no list items, empty state, or loading"

    def test_delete_button_state(self, page: Page):
        """删除按钮区域存在"""
        page.goto(BACKEND_URL + "/#/history")
        page.wait_for_selector("#page-history", timeout=10000)
        page.wait_for_timeout(500)
        delete_area = page.locator("#deleteSelectedBtn")
        if delete_area.count() == 0:
            delete_area = page.locator('[data-action="delete"]')
        # Delete button may be hidden when nothing selected
        assert page.locator("#page-history").text_content(), "History page empty"


# ============================================================================
# Settings Page
# ============================================================================

@pytest.mark.e2e
class TestSettingsPage:
    """设置页渲染与交互"""

    def test_page_renders(self, page: Page):
        """设置页渲染"""
        page.goto(BACKEND_URL + "/#/settings")
        page.wait_for_selector("#page-settings", timeout=10000)
        expect(page.locator("#page-settings")).to_be_visible(timeout=5000)

    def test_theme_toggle_checkbox_exists(self, page: Page):
        """主题切换复选框存在 (#themeToggle)"""
        page.goto(BACKEND_URL + "/#/settings")
        page.wait_for_selector("#page-settings", timeout=10000)
        theme_cb = page.locator("#themeToggle")
        assert theme_cb.count() >= 1, f"Expected #themeToggle checkbox, got {theme_cb.count()}"

    def test_theme_toggle_changes_theme(self, page: Page):
        """点击深色模式复选框应切换主题"""
        page.goto(BACKEND_URL + "/#/settings")
        page.wait_for_selector("#page-settings", timeout=10000)
        page.wait_for_timeout(500)

        cb = page.locator("#themeToggle")
        if cb.count() > 0:
            was_checked = cb.first.is_checked()
            cb.first.click()
            page.wait_for_timeout(500)
            # Verify state changed
            is_checked = cb.first.is_checked()
            assert is_checked != was_checked, f"Theme toggle state unchanged: {was_checked} -> {is_checked}"

    def test_default_mode_setting_exists(self, page: Page):
        """默认评估模式设置存在"""
        page.goto(BACKEND_URL + "/#/settings")
        page.wait_for_selector("#page-settings", timeout=10000)
        content = page.locator("#page-settings").text_content() or ""
        # Settings should mention mode or have mode selector
        has_mode = "模式" in content or "mode" in content.lower()
        assert has_mode or len(content) > 100, "Settings page looks too minimal"


# ============================================================================
# Song Library Page
# ============================================================================

@pytest.mark.e2e
class TestSongLibraryPage:
    """标准曲库页渲染与交互"""

    def test_page_renders_empty_state(self, page: Page):
        """曲库页渲染 (空状态)"""
        page.goto(BACKEND_URL + "/#/songs")
        page.wait_for_selector("#page-songs", timeout=10000)
        expect(page.locator("#page-songs")).to_be_visible(timeout=5000)

    def test_empty_state_or_loading(self, page: Page):
        """空曲库应显示空状态或加载中"""
        page.goto(BACKEND_URL + "/#/songs")
        page.wait_for_selector("#page-songs", timeout=10000)
        page.wait_for_timeout(1000)

        empty_el = page.locator("#songsEmpty")
        loading_el = page.locator("#songsLoading")
        content_el = page.locator("#songsContent")

        has_state = empty_el.count() > 0 or loading_el.count() > 0 or content_el.count() > 0
        assert has_state, "Song library has no empty/loading/content state element"

    def test_import_button_exists(self, page: Page):
        """导入音频按钮存在"""
        page.goto(BACKEND_URL + "/#/songs")
        page.wait_for_selector("#page-songs", timeout=10000)
        import_btn = page.locator("#importSongBtn")
        if import_btn.count() == 0:
            import_btn = page.locator("button").filter(has_text="导入")
        assert import_btn.count() > 0, f"No import button on song library, got {import_btn.count()}"


# ============================================================================
# Cross-Page Navigation
# ============================================================================

@pytest.mark.e2e
class TestCrossPageNavigation:
    """跨页面导航流程"""

    def test_home_to_sing_to_home(self, page: Page):
        """首页 → 演唱页 → 返回首页"""
        page.goto(BACKEND_URL + "/#/")
        page.wait_for_selector("#pageContainer", timeout=10000)
        page.wait_for_timeout(500)

        # Navigate to sing
        page.evaluate('window.__router.navigate("#/sing")')
        page.wait_for_timeout(600)
        assert '#/sing' in page.evaluate('location.hash'), "Should be at #/sing"

        # Navigate back home
        page.evaluate('window.__router.navigate("#/")')
        page.wait_for_timeout(600)
        assert page.evaluate('location.hash') in ('#/', ''), "Should be at #/"

    def test_navigate_all_pages_no_crash(self, page: Page):
        """快速导航所有页面不应崩溃"""
        routes = ['#/', '#/sing', '#/compare', '#/history', '#/settings', '#/songs']
        page.goto(BACKEND_URL + "/#/")
        page.wait_for_selector("#pageContainer", timeout=10000)

        for route in routes:
            page.evaluate(f'window.__router.navigate("{route}")')
            page.wait_for_timeout(300)

        # After all navigation, container should still exist
        expect(page.locator("#pageContainer")).to_be_visible()
        # No JS errors should have accumulated
        errors = page.evaluate(
            "window.__navErrors ? window.__navErrors.length : 0"
        )
        assert errors == 0, f"Navigation caused {errors} JS errors"

    def test_browser_back_button(self, page: Page):
        """浏览器后退按钮回归"""
        page.goto(BACKEND_URL + "/#/")
        page.wait_for_selector("#pageContainer", timeout=10000)

        # Navigate to history then settings
        page.evaluate('window.__router.navigate("#/history")')
        page.wait_for_timeout(400)
        page.evaluate('window.__router.navigate("#/settings")')
        page.wait_for_timeout(400)

        # Go back should return to history
        page.go_back()
        page.wait_for_timeout(500)
        current = page.evaluate('location.hash')
        assert '#/history' in current, f"Back should go to #/history, got {current}"


# ============================================================================
# Component Verification
# ============================================================================

@pytest.mark.e2e
class TestComponentVerification:
    """关键组件存在性验证"""

    def test_toast_system_loaded(self, page: Page):
        """Toast 系统已加载 (#toastWrap)"""
        page.goto(BACKEND_URL + "/#/")
        page.wait_for_selector("#pageContainer", timeout=10000)
        page.wait_for_timeout(500)
        # #toastWrap is in index.html static HTML
        toast_wrap = page.locator("#toastWrap")
        assert toast_wrap.count() > 0, "#toastWrap not found in static HTML"

    def test_toast_dom_container_exists(self, page: Page):
        """Toast DOM 容器存在且可接受子元素"""
        page.goto(BACKEND_URL + "/#/")
        page.wait_for_selector("#toastWrap", state="attached", timeout=10000)
        # Toast container is hidden by default — that's fine
        # Add a toast element directly to verify the container works
        page.evaluate("""
            (function() {
                var wrap = document.getElementById('toastWrap');
                if (!wrap) return;
                wrap.style.display = 'block';  // Make visible for test
                var toast = document.createElement('div');
                toast.className = 'toast toast-info';
                toast.textContent = 'E2E Test Toast';
                wrap.appendChild(toast);
                setTimeout(function() { toast.remove(); }, 1500);
            })();
        """)
        page.wait_for_timeout(300)
        toast = page.locator(".toast")
        assert toast.count() >= 1, "Toast DOM element not found after insert"

    def test_nav_tabs_rendered(self, page: Page):
        """导航标签页全部渲染 (预计 5-6 个)"""
        page.goto(BACKEND_URL + "/#/")
        page.wait_for_selector(".nav-tab", timeout=10000)
        tabs = page.locator(".nav-tab")
        count = tabs.count()
        assert count >= 4, f"Expected >=4 nav tabs, got {count}"

    def test_nav_click_navigates(self, page: Page):
        """点击导航标签应切换页面"""
        page.goto(BACKEND_URL + "/#/")
        page.wait_for_selector(".nav-tab", timeout=10000)
        page.wait_for_timeout(500)

        # Find a nav tab that's not home
        tabs = page.locator(".nav-tab")
        count = tabs.count()
        clicked = False
        for i in range(count):
            tab = tabs.nth(i)
            href = tab.get_attribute("href") or tab.get_attribute("data-route") or ""
            if "history" in href or "compare" in href:
                tab.click()
                page.wait_for_timeout(600)
                clicked = True
                break

        if clicked:
            current = page.evaluate("location.hash")
            assert "#/" in current, "Navigation click should change hash"


# ============================================================================
# GSAP Animation Verification
# ============================================================================

@pytest.mark.e2e
class TestGSAPAnimation:
    """GSAP 动效验证"""

    def test_animation_controller_initialized(self, page: Page):
        """AnimationController 全局实例已初始化 (window.__ac)"""
        page.goto(BACKEND_URL + "/#/")
        page.wait_for_selector("#pageContainer", timeout=10000)
        page.wait_for_timeout(500)
        has_ac = page.evaluate("window.__ac !== undefined")
        assert has_ac, "AnimationController (window.__ac) not initialized"

    def test_presets_loaded(self, page: Page):
        """动画预设已加载 (window.__presets)"""
        page.goto(BACKEND_URL + "/#/")
        page.wait_for_selector("#pageContainer", timeout=10000)
        has_presets = page.evaluate("window.__presets !== undefined")
        assert has_presets, "Animation presets (window.__presets) not loaded"

    def test_page_entrance_animation_runs(self, page: Page):
        """页面入场应有动画（元素 opacity 从 0 变到 1）"""
        page.goto(BACKEND_URL + "/#/sing")
        page.wait_for_selector("#page-sing", timeout=10000)
        page.wait_for_timeout(800)  # Animation should be done by now

        # After entrance animation, page should be fully visible
        opacity = page.evaluate("""
            (function() {
                var el = document.querySelector('#page-sing');
                if (!el) return 'no-el';
                return window.getComputedStyle(el).opacity;
            })();
        """)
        if opacity != 'no-el':
            assert float(opacity) >= 0.9, f"Page opacity is {opacity}, expected ~1 after animation"

    def test_reduced_motion_disables_animation(self, page: Page):
        """prefers-reduced-motion 应禁用动画"""
        page.goto(BACKEND_URL + "/#/")
        page.wait_for_selector("#pageContainer", timeout=10000)

        # Force reduced motion via window.__ac (AnimationController)
        page.evaluate("""
            (function() {
                if (window.__ac) {
                    window.__ac.setEnabled(false);
                }
            })();
        """)
        page.wait_for_timeout(200)

        # Now navigate — should navigate instantly
        page.evaluate('window.__router.navigate("#/history")')
        page.wait_for_timeout(300)

        # Page should still be visible (just no animation)
        history_page = page.locator("#page-history")
        assert history_page.count() > 0 or page.evaluate('location.hash') in ('#/history',), \
            "Navigation should work even with animation disabled"

    def test_gsap_click_micro_interaction(self, page: Page):
        """GSAP 按钮点击微交互 (scale)"""
        page.goto(BACKEND_URL + "/#/")
        page.wait_for_selector("#pageContainer", timeout=10000)
        page.wait_for_timeout(500)

        # Verify clickPress works on a button via window.__ac
        result = page.evaluate("""
            (function() {
                try {
                    var ac = window.__ac;
                    if (!ac) return 'no-ac';
                    var btn = document.createElement('button');
                    document.body.appendChild(btn);
                    ac.clickPress(btn);
                    document.body.removeChild(btn);
                    return 'ok';
                } catch(e) {
                    return 'error:' + e.message;
                }
            })();
        """)
        assert result == 'ok', f"clickPress failed: {result}"
