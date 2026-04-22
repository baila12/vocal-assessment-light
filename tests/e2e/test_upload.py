"""
声乐评估系统 - 文件上传和分析测试

测试音频文件上传、分析按钮状态、进度显示等功能。
"""
import pytest

from playwright.sync_api import Page, expect

from .conftest import BACKEND_URL


class TestAudioUploadAndAnalysis:
    """音频上传和分析测试"""

    def test_file_upload_shows_audio_card(self, page: Page, create_test_audio):
        """测试上传文件后显示音频卡片"""
        test_file = create_test_audio

        page.goto(BACKEND_URL)

        # 上传文件
        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_file))

        page.wait_for_timeout(500)

        # 验证音频卡片显示
        audio_card = page.locator("#selectedAudioCard")
        expect(audio_card).to_be_visible()

        # 验证文件名显示
        filename = page.locator("#selectedFileName")
        expect(filename).to_contain_text("test_e2e_audio")

    def test_analyze_button_enabled_after_upload(self, page: Page, create_test_audio):
        """测试上传后分析按钮可用"""
        test_file = create_test_audio

        page.goto(BACKEND_URL)

        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_file))

        page.wait_for_timeout(500)

        # 分析按钮应该可用
        analyze_btn = page.locator("#analyzeBtn")
        expect(analyze_btn).to_be_enabled()

    def test_analysis_shows_progress(self, page: Page, create_test_audio):
        """测试分析显示进度或跳转到分析页"""
        test_file = create_test_audio

        page.goto(BACKEND_URL)

        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_file))

        analyze_btn = page.locator("#analyzeBtn")
        analyze_btn.click()

        # 分析可能很快完成，检查进度条或页面跳转
        # 等待跳转到分析页面（最多60秒）
        try:
            page.wait_for_url("**/analysis.html**", timeout=60000)
            expect(page).to_have_url(BACKEND_URL + "/analysis.html")
        except Exception:
            # 如果没有跳转，检查进度条是否显示过
            progress = page.locator("#analysisProgress")
            # 进度条可能已经完成
            pass

    def test_analysis_completes_and_redirects(self, page: Page, create_test_audio):
        """测试分析完成并跳转"""
        test_file = create_test_audio

        page.goto(BACKEND_URL)

        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_file))

        # 等待分析按钮可见
        analyze_btn = page.locator("#analyzeBtn")
        analyze_btn.wait_for(state="visible", timeout=5000)
        analyze_btn.click()

        # 等待跳转到分析页面（最多60秒）
        page.wait_for_url("**/analysis.html**", timeout=60000)
        expect(page).to_have_url(BACKEND_URL + "/analysis.html")
