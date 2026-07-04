"""
声乐评估系统 - 分析页面测试 (已弃用)

⚠️ 此文件中的测试基于旧的多页面架构 (analysis.html)。
当前 SPA 使用 Hash 路由，分析结果在 #/report/:id 中展示。
请使用 test_spa_e2e.py 和 test_visual_verify.py 中的 SPA 兼容测试。
"""
import json

import pytest

from playwright.sync_api import Page, expect

from .conftest import BACKEND_URL

pytestmark = pytest.mark.skip(
    reason="旧版多页面架构测试 — /analysis.html 已 301 重定向到 /。"
           "分析结果现在通过 SPA 路由 #/report/:id 展示"
)


class TestAnalysisPage:
    """分析页面测试"""

    def test_analysis_page_loads(self, page: Page):
        """测试分析页面加载"""
        page.goto(f"{BACKEND_URL}/analysis.html")

        # 验证页面元素
        expect(page.locator("#totalScore")).to_be_visible()
        expect(page.locator("#radarChart")).to_be_visible()

    def test_return_to_home_button(self, page: Page):
        """测试返回首页按钮"""
        page.goto(f"{BACKEND_URL}/analysis.html")

        # 点击返回首页
        back_btn = page.get_by_role("button", name="返回首页")
        back_btn.click()

        # 验证返回首页
        expect(page).to_have_url(BACKEND_URL + "/")

    def test_audio_player_exists(self, page: Page):
        """测试音频播放器存在"""
        page.goto(f"{BACKEND_URL}/analysis.html")

        # 播放按钮
        play_btn = page.locator("#playBtn")
        expect(play_btn).to_be_visible()

        # 进度条
        progress_bar = page.locator("#progressBar")
        expect(progress_bar).to_be_visible()

    def test_visualization_tabs_exist(self, page: Page):
        """测试可视化标签页存在"""
        page.goto(f"{BACKEND_URL}/analysis.html")

        # 三个标签页
        spectrogram_tab = page.locator(".viz-tab[data-tab='spectrogram']")
        pitch_tab = page.locator(".viz-tab[data-tab='pitch']")
        energy_tab = page.locator(".viz-tab[data-tab='energy']")

        expect(spectrogram_tab).to_be_visible()
        expect(pitch_tab).to_be_visible()
        expect(energy_tab).to_be_visible()

    def test_visualization_tab_switching(self, page: Page):
        """测试可视化标签页切换"""
        # 需要先有分析结果才能正确初始化事件监听器
        # 直接访问analysis.html会因为缺少sessionStorage而重定向

        # 设置mock数据到sessionStorage
        mock_result = {
            "success": True,
            "total_score": 75,
            "level": "良好",
            "scores": {"volume": 70, "pitch": 80, "rhythm": 75, "breath": 70, "emotion": 80},
            "basic_info": {"filename": "test.wav", "duration": "0:02", "file_size": "100KB"},
            "advice": ["建议1", "建议2"]
        }

        # 先访问首页设置sessionStorage
        page.goto(BACKEND_URL)

        # 使用evaluate设置sessionStorage
        mock_json = json.dumps(mock_result, ensure_ascii=False)
        page.evaluate(f"sessionStorage.setItem('analysisResult', '{mock_json}')")

        # 然后访问分析页面
        page.goto(f"{BACKEND_URL}/analysis.html")

        # 等待页面加载
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        # 检查标签是否存在
        spectrogram_tab = page.locator(".viz-tab[data-tab='spectrogram']")
        pitch_tab = page.locator(".viz-tab[data-tab='pitch']")

        # 如果标签存在，尝试点击
        if spectrogram_tab.count() > 0 and pitch_tab.count() > 0:
            # 点击基音轨迹标签
            pitch_tab.click()
            page.wait_for_timeout(500)

            # 验证切换
            pitch_tab_class = pitch_tab.get_attribute("class") or ""
            spectrogram_tab_class = spectrogram_tab.get_attribute("class") or ""

            # 任一条件满足即可
            assert (
                "active" in pitch_tab_class
                or "active" not in spectrogram_tab_class
            ), "Tab switching should work"
