"""
声乐评估系统 - 真实音频 E2E 测试

使用真实音频文件测试完整分析流程
"""
import pytest

from playwright.sync_api import Page, expect

from .conftest import BACKEND_URL, TEST_MUSIC_FOLDER


class TestRealAudioAnalysis:
    """真实音频分析测试"""

    @pytest.fixture
    def real_audio_file(self):
        """获取真实音频文件"""
        audio_file = VOCAL_DIR / "obj_wo3DlMOGwrbDjj7DisKw_34872776288_2a86_1d5c_dd56_58c1c8954ede8c3339aaf5f99850b667.mp3"
        if not audio_file.exists():
            pytest.skip("真实音频文件不存在")
        return audio_file

    def test_real_audio_upload_and_analysis(self, page: Page, real_audio_file):
        """测试真实音频上传和分析 - 首页上传后跳转到分析页面"""
        page.goto(f"{BACKEND_URL}/", timeout=30000, wait_until="domcontentloaded")

        # 首页的上传区域 - 使用 action-card primary
        with page.expect_file_chooser() as fc_info:
            # 首页的导入音频卡片
            page.locator(".action-card.primary").click()
        fc_info.value.set_files(str(real_audio_file))

        # 等待音频卡片显示（表示文件已选择）
        audio_card = page.locator("#selectedAudioCard")
        expect(audio_card).to_be_visible(timeout=10000)

        # 验证文件名显示
        file_name = page.locator("#selectedFileName")
        expect(file_name).not_to_have_text("未选择文件", timeout=5000)

        # 点击开始分析按钮
        analyze_btn = page.locator("#analyzeBtn")
        expect(analyze_btn).to_be_visible(timeout=5000)
        analyze_btn.click()

        # 等待页面跳转到分析页面
        # 分析按钮点击后会存储文件到 IndexedDB 然后跳转到 /analysis.html
        expect(page).to_have_url(f"{BACKEND_URL}/analysis.html", timeout=30000)

        # 在分析页面等待分析完成
        # 快速模式约 30-60 秒，等待结果显示
        page.wait_for_timeout(60000)

        # 验证分析页面已加载
        current_url = page.url
        print(f"当前URL: {current_url}")
        assert "analysis" in current_url, "应该跳转到分析页面"


class TestRealAudioCompare:
    """真实音频对比分析测试"""

    @pytest.fixture
    def real_audio_file(self):
        """获取真实音频文件"""
        audio_file = VOCAL_DIR / "obj_wo3DlMOGwrbDjj7DisKw_34872776288_2a86_1d5c_dd56_58c1c8954ede8c3339aaf5f99850b667.mp3"
        if not audio_file.exists():
            pytest.skip("真实音频文件不存在")
        return audio_file

    def test_real_audio_compare_page(self, page: Page, real_audio_file):
        """测试真实音频在对比页面的完整流程"""
        page.goto(f"{BACKEND_URL}/compare.html", timeout=30000, wait_until="domcontentloaded")

        # 上传标准音频
        with page.expect_file_chooser() as fc_info:
            page.locator("#standardUpload").click()
        fc_info.value.set_files(str(real_audio_file))

        # 等待文件加载
        expect(page.locator("#standardCard")).to_have_class("audio-card standard has-file", timeout=10000)

        # 上传用户音频（同一个文件）
        with page.expect_file_chooser() as fc_info:
            page.locator("#userUpload").click()
        fc_info.value.set_files(str(real_audio_file))

        # 等待文件加载
        expect(page.locator("#userCard")).to_have_class("audio-card user has-file", timeout=10000)

        # 点击分析按钮
        analyze_btn = page.locator("#analyzeBtn")
        expect(analyze_btn).not_to_be_disabled(timeout=5000)
        analyze_btn.click()

        # 等待结果显示（真实音频对比可能需要较长时间）
        result_panel = page.locator("#resultPanel")
        expect(result_panel).to_be_visible(timeout=120000)

        # 验证分数显示
        result_score = page.locator("#resultScore")
        expect(result_score).to_be_visible()
        score_text = result_score.text_content()
        print(f"对比分析评分: {score_text}")

        # 验证等级显示
        result_level = page.locator("#resultLevel")
        expect(result_level).to_be_visible()

        # 验证维度对比显示
        dimension_compare = page.locator("#dimensionCompare")
        expect(dimension_compare).to_be_visible()

        # 验证建议列表显示
        suggestion_list = page.locator("#suggestionList")
        expect(suggestion_list).to_be_visible()

    def test_real_audio_solo_analysis(self, page: Page, real_audio_file):
        """测试真实音频独立评估（无标准音频）"""
        page.goto(f"{BACKEND_URL}/compare.html", timeout=30000, wait_until="domcontentloaded")

        # 只上传用户音频
        with page.expect_file_chooser() as fc_info:
            page.locator("#userUpload").click()
        fc_info.value.set_files(str(real_audio_file))

        # 等待文件加载
        expect(page.locator("#userCard")).to_have_class("audio-card user has-file", timeout=10000)

        # 提示横幅应该显示
        tip_banner = page.locator("#tipBanner")
        expect(tip_banner).to_have_class("tip-banner show", timeout=5000)

        # 点击分析按钮
        analyze_btn = page.locator("#analyzeBtn")
        expect(analyze_btn).not_to_be_disabled(timeout=5000)
        analyze_btn.click()

        # 等待结果显示（快速模式分析真实音频约 30-60 秒）
        result_panel = page.locator("#resultPanel")
        expect(result_panel).to_be_visible(timeout=120000)

        # 验证分数显示
        result_score = page.locator("#resultScore")
        expect(result_score).to_be_visible()
        score_text = result_score.text_content()
        print(f"独立评估评分: {score_text}")

        # 验证等级显示
        result_level = page.locator("#resultLevel")
        expect(result_level).to_be_visible()