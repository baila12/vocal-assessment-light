"""
声乐评估系统 - 历史记录删除测试

测试删除历史记录功能。
"""
import pytest

from playwright.sync_api import Page, expect

from .conftest import BACKEND_URL


class TestHistoryDelete:
    """删除历史记录功能测试"""

    def test_delete_history_record(self, page: Page, create_test_audio):
        """测试删除历史记录功能"""
        test_file = create_test_audio

        page.goto(BACKEND_URL)

        # 上传并分析音频，创建历史记录
        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_file))

        analyze_btn = page.locator("#analyzeBtn")
        analyze_btn.click()

        # 等待分析完成
        page.wait_for_timeout(5000)

        # 返回首页
        page.goto(BACKEND_URL)

        # 切换到历史记录页
        history_tab = page.locator("#navHistory")
        history_tab.click()

        page.wait_for_timeout(1000)

        # 获取历史卡片数量
        history_cards = page.locator(".history-card")
        initial_count = history_cards.count()

        if initial_count > 0:
            # 获取第一个卡片的ID
            first_card = history_cards.first
            card_id = first_card.get_attribute("data-id")

            # 点击删除按钮
            delete_btn = first_card.locator(".delete-btn")

            # 设置对话框处理
            page.once("dialog", lambda dialog: dialog.accept())

            delete_btn.click()

            # 等待删除完成
            page.wait_for_timeout(2000)

            # 验证卡片已删除（通过检查特定ID的卡片是否还存在）
            deleted_card = page.locator(f".history-card[data-id='{card_id}']")
            assert deleted_card.count() == 0, f"ID为 {card_id} 的卡片应该已被删除"

    def test_delete_multiple_records(self, page: Page, create_test_audio):
        """测试删除多条历史记录"""
        test_file = create_test_audio

        page.goto(BACKEND_URL)

        # 创建多条历史记录
        for _ in range(2):
            file_input = page.locator("#fileInput")
            file_input.set_input_files(str(test_file))

            analyze_btn = page.locator("#analyzeBtn")
            analyze_btn.click()

            page.wait_for_timeout(3000)
            page.goto(BACKEND_URL)

        # 切换到历史记录页
        history_tab = page.locator("#navHistory")
        history_tab.click()

        page.wait_for_timeout(1000)

        history_cards = page.locator(".history-card")
        initial_count = history_cards.count()

        if initial_count >= 2:
            # 获取第一个卡片的ID
            first_card = history_cards.first
            card_id = first_card.get_attribute("data-id")

            # 设置对话框处理
            page.once("dialog", lambda dialog: dialog.accept())

            # 删除第一条记录
            delete_btn = first_card.locator(".delete-btn")
            delete_btn.click()

            page.wait_for_timeout(2000)

            # 验证特定ID的卡片已删除
            deleted_card = page.locator(f".history-card[data-id='{card_id}']")
            assert deleted_card.count() == 0, f"ID为 {card_id} 的卡片应该已被删除"
