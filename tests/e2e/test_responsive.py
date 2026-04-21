"""
声乐评估系统 - 响应式设计和可访问性测试

测试不同视口下的响应式布局以及键盘导航等可访问性功能。
"""
import pytest

from playwright.sync_api import Page, expect

from .conftest import BACKEND_URL


class TestResponsiveDesign:
    """响应式设计测试"""

    def test_mobile_viewport(self, page: Page):
        """测试移动端视口"""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(BACKEND_URL)

        # 导航栏应该可见
        navbar = page.locator(".navbar")
        expect(navbar).to_be_visible()

        # 主要按钮应该可用
        import_btn = page.get_by_role("button", name="导入音频")
        expect(import_btn).to_be_visible()

    def test_tablet_viewport(self, page: Page):
        """测试平板视口"""
        page.set_viewport_size({"width": 768, "height": 1024})
        page.goto(BACKEND_URL)

        # 侧边栏应该可见
        sidebar = page.locator(".sidebar")
        expect(sidebar).to_be_visible()

    def test_desktop_viewport(self, page: Page):
        """测试桌面视口"""
        page.set_viewport_size({"width": 1920, "height": 1080})
        page.goto(BACKEND_URL)

        # 完整布局
        main_content = page.locator(".main-content")
        expect(main_content).to_be_visible()

        sidebar = page.locator(".sidebar")
        expect(sidebar).to_be_visible()


class TestAccessibility:
    """可访问性测试"""

    def test_buttons_have_text(self, page: Page):
        """测试按钮有文本标签"""
        page.goto(BACKEND_URL)

        buttons = page.locator("button")
        count = buttons.count()

        for i in range(min(count, 10)):  # 只检查前10个按钮
            btn = buttons.nth(i)
            text = btn.text_content()
            # 按钮应该有文本或者图标
            assert text and text.strip(), f"按钮 {i} 缺少标签"

    def test_navigation_is_keyboard_accessible(self, page: Page):
        """测试导航可通过键盘访问"""
        page.goto(BACKEND_URL)

        # Tab 导航
        page.keyboard.press("Tab")
        page.keyboard.press("Tab")

        # 应该有元素获得焦点
        focused = page.locator(":focus")
        expect(focused).to_be_visible()
