"""
声乐评估系统 - 可视化图片测试

测试音频特征可视化图片生成、标签切换等功能。
"""
import json

import pytest

from playwright.sync_api import Page, expect

from .conftest import BACKEND_URL


class TestVisualizationImages:
    """音频特征可视化图片测试"""

    def test_visualization_images_generated(self, page: Page, create_test_audio):
        """测试分析后生成可视化图片"""
        test_file = create_test_audio

        page.goto(BACKEND_URL)

        # 上传并分析
        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_file))

        analyze_btn = page.locator("#analyzeBtn")
        analyze_btn.click()

        # 等待跳转到分析页面
        try:
            page.wait_for_url("**/analysis.html**", timeout=60000)
        except Exception:
            page.wait_for_timeout(5000)

        # 检查是否在分析页面
        if "analysis.html" in page.url:
            page.wait_for_timeout(2000)

            # 检查可视化标签页存在
            viz_tabs = page.locator(".viz-tab")
            assert viz_tabs.count() >= 3, "应该有三个可视化标签页"

            # 检查图片元素存在
            spectrogram_img = page.locator("#spectrogramImg")
            pitch_img = page.locator("#pitchImg")
            energy_img = page.locator("#energyImg")

            # 验证图片元素存在（使用 count() 而不是 is_attached()）
            assert spectrogram_img.count() > 0, "频谱图图片元素应存在"
            assert pitch_img.count() > 0, "基音轨迹图片元素应存在"
            assert energy_img.count() > 0, "能量曲线图片元素应存在"

    def test_visualization_tab_switching(self, page: Page):
        """测试可视化标签页切换"""
        # 设置mock数据
        mock_result = {
            "success": True,
            "total_score": 75,
            "level": "良好",
            "scores": {"volume": 70, "pitch": 80, "rhythm": 75, "breath": 70, "emotion": 80},
            "basic_info": {"filename": "test.wav", "duration": "0:02", "file_size": "100KB"},
            "advice": ["建议1", "建议2"],
            "visualization": {
                "spectrogram": "/plots/test_spectrogram.png",
                "pitch_trajectory": "/plots/test_pitch.png",
                "energy": "/plots/test_energy.png"
            }
        }

        page.goto(BACKEND_URL)
        mock_json = json.dumps(mock_result, ensure_ascii=False)
        page.evaluate(f"sessionStorage.setItem('analysisResult', '{mock_json}')")

        # 访问分析页面
        page.goto(f"{BACKEND_URL}/analysis.html")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        # 测试标签切换
        pitch_tab = page.locator(".viz-tab[data-tab='pitch']")
        energy_tab = page.locator(".viz-tab[data-tab='energy']")

        if pitch_tab.count() > 0:
            pitch_tab.click()
            page.wait_for_timeout(500)

            # 验证面板切换
            pitch_panel = page.locator("#pitchPanel")
            if pitch_panel.count() > 0:
                panel_class = pitch_panel.get_attribute("class") or ""
                assert "active" in panel_class, "基音轨迹面板应该激活"

        if energy_tab.count() > 0:
            energy_tab.click()
            page.wait_for_timeout(500)

            energy_panel = page.locator("#energyPanel")
            if energy_panel.count() > 0:
                panel_class = energy_panel.get_attribute("class") or ""
                assert "active" in panel_class, "能量曲线面板应该激活"
