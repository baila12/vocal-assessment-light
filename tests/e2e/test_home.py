"""
声乐评估系统 - 首页和导航测试

测试首页加载、导航栏、页面切换等核心功能。
覆盖修复的 showPage 问题。
"""
import pytest

from playwright.sync_api import Page, expect

from .conftest import BACKEND_URL


class TestHomePage:
    """首页加载和基础功能测试"""

    def test_home_page_loads_successfully(self, page: Page):
        """测试首页正常加载"""
        page.goto(BACKEND_URL)

        # 验证页面标题
        expect(page).to_have_title("声乐评估系统 - 离线版")

        # 验证导航栏存在
        navbar = page.locator(".navbar")
        expect(navbar).to_be_visible()

        # 验证品牌名称显示
        brand_name = page.locator(".brand-name")
        expect(brand_name).to_contain_text("声乐评估系统")

    def test_main_action_buttons_exist(self, page: Page):
        """测试主要操作按钮存在"""
        page.goto(BACKEND_URL)

        # 导入音频按钮（在 action-card 中）
        import_btn = page.locator(".action-card.primary")
        expect(import_btn).to_be_visible()

        # 快速录音按钮
        record_btn = page.locator(".action-card.secondary")
        expect(record_btn).to_be_visible()

    def test_file_input_exists(self, page: Page):
        """测试文件输入存在"""
        page.goto(BACKEND_URL)

        # 文件输入（隐藏的）
        file_input = page.locator("#fileInput")
        expect(file_input).to_be_attached()

    def test_chart_js_loaded(self, page: Page):
        """测试 Chart.js 已加载"""
        page.goto(BACKEND_URL)

        # 检查 Chart 是否定义
        chart_defined = page.evaluate("typeof Chart !== 'undefined'")
        assert chart_defined, "Chart.js 未加载"


class TestPageNavigation:
    """页面导航测试 - 覆盖修复的 showPage 问题"""

    def test_navigation_tabs_visible(self, page: Page):
        """测试导航标签可见"""
        page.goto(BACKEND_URL)

        # 三个导航标签
        home_tab = page.locator("#navHome")
        compare_tab = page.locator("#navCompare")
        history_tab = page.locator("#navHistory")

        expect(home_tab).to_be_visible()
        expect(compare_tab).to_be_visible()
        expect(history_tab).to_be_visible()

    def test_default_page_is_home(self, page: Page):
        """测试默认页面是首页"""
        page.goto(BACKEND_URL)

        home_page = page.locator("#page-home")
        expect(home_page).to_be_visible()
        expect(home_page).to_have_class("page active")

    def test_switch_to_compare_page(self, page: Page):
        """测试切换到对比分析页"""
        page.goto(BACKEND_URL)

        # 点击对比分析
        compare_tab = page.locator("#navCompare")
        compare_tab.click()

        # 验证页面切换
        compare_page = page.locator("#page-compare")
        expect(compare_page).to_be_visible()
        expect(compare_page).to_have_class("page active")

        # 验证标签高亮
        expect(compare_tab).to_have_class("nav-tab active")

    def test_switch_to_history_page(self, page: Page):
        """测试切换到历史记录页"""
        page.goto(BACKEND_URL)

        # 点击历史记录
        history_tab = page.locator("#navHistory")
        history_tab.click()

        # 验证页面切换
        history_page = page.locator("#page-history")
        expect(history_page).to_be_visible()
        expect(history_page).to_have_class("page active")

    def test_return_to_home_from_history(self, page: Page):
        """测试从历史记录页返回首页 - 覆盖导航修复"""
        page.goto(BACKEND_URL)

        # 先切换到历史记录
        history_tab = page.locator("#navHistory")
        history_tab.click()
        expect(page.locator("#page-history")).to_be_visible()

        # 返回首页
        home_tab = page.locator("#navHome")
        home_tab.click()

        # 验证返回首页成功
        home_page = page.locator("#page-home")
        expect(home_page).to_be_visible()
        expect(home_page).to_have_class("page active")
