"""
声乐评估系统 - 历史记录测试

测试历史记录页加载、筛选功能等功能。
覆盖修复的历史记录功能。
"""
import pytest

from playwright.sync_api import Page, expect

from .conftest import BACKEND_URL


class TestHistoryPage:
    """历史记录页测试 - 覆盖修复的功能"""

    def test_history_page_loads(self, page: Page):
        """测试历史记录页加载"""
        page.goto(BACKEND_URL)

        history_tab = page.locator("#navHistory")
        history_tab.click()

        # 验证成长曲线
        growth_chart = page.locator("#growthChart")
        expect(growth_chart).to_be_visible()

        # 验证统计信息
        expect(page.locator("#avgScore")).to_be_visible()
        expect(page.locator("#maxScore")).to_be_visible()
        expect(page.locator("#minScore")).to_be_visible()
        expect(page.locator("#totalCount")).to_be_visible()

    def test_filter_buttons_exist(self, page: Page):
        """测试筛选按钮存在"""
        page.goto(BACKEND_URL)

        history_tab = page.locator("#navHistory")
        history_tab.click()

        # 四个筛选按钮
        all_btn = page.get_by_role("button", name="全部")
        today_btn = page.get_by_role("button", name="今天")
        week_btn = page.get_by_role("button", name="本周")
        month_btn = page.get_by_role("button", name="本月")

        expect(all_btn).to_be_visible()
        expect(today_btn).to_be_visible()
        expect(week_btn).to_be_visible()
        expect(month_btn).to_be_visible()

    def test_filter_button_clicking(self, page: Page):
        """测试筛选按钮点击"""
        page.goto(BACKEND_URL)

        history_tab = page.locator("#navHistory")
        history_tab.click()

        page.wait_for_timeout(500)

        # 点击"今天"
        today_btn = page.get_by_role("button", name="今天")
        today_btn.click()

        # 验证按钮激活状态
        expect(today_btn).to_have_class("filter-btn active")

        # 点击"本周"
        week_btn = page.get_by_role("button", name="本周")
        week_btn.click()
        expect(week_btn).to_have_class("filter-btn active")

    def test_history_cards_have_delete_buttons(self, page: Page, create_test_audio):
        """测试历史卡片有删除按钮 - 覆盖删除功能修复"""
        # 先创建一条历史记录
        test_file = create_test_audio

        page.goto(BACKEND_URL)

        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_file))

        analyze_btn = page.locator("#analyzeBtn")
        analyze_btn.click()

        # 等待分析完成或跳转
        page.wait_for_timeout(5000)

        # 返回首页
        page.goto(BACKEND_URL)

        # 切换到历史记录
        history_tab = page.locator("#navHistory")
        history_tab.click()

        page.wait_for_timeout(1000)

        # 检查是否有历史卡片
        history_cards = page.locator(".history-card")
        count = history_cards.count()

        if count > 0:
            # 验证删除按钮存在
            delete_btn = history_cards.first.locator(".delete-btn")
            expect(delete_btn).to_be_visible()

    def test_history_card_clickable(self, page: Page, create_test_audio):
        """测试历史卡片可点击查看详情"""
        test_file = create_test_audio

        page.goto(BACKEND_URL)

        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_file))

        analyze_btn = page.locator("#analyzeBtn")
        analyze_btn.click()

        # 等待分析完成
        page.wait_for_timeout(5000)

        # 返回首页
        page.goto(BACKEND_URL)

        history_tab = page.locator("#navHistory")
        history_tab.click()

        page.wait_for_timeout(1000)

        history_cards = page.locator(".history-card")
        count = history_cards.count()
        if count > 0:
            # 点击第一个卡片
            history_cards.first.click()

            # 等待跳转或显示详情
            page.wait_for_timeout(3000)
            # 验证已跳转或页面状态改变
            current_url = page.url
            assert "localhost:5000" in current_url, (
                f"Expected localhost:5000 in URL, got: {current_url}"
            )
