"""
声乐评估系统 - 对比分析页面测试 (v5.4)

测试独立对比分析页面的完整流程：
1. 页面加载
2. 标准音频上传
3. 用户音频上传
4. 对比结果展示

页面结构：双音频并排布局（标准音频 + 用户音频）
"""
import pytest

from playwright.sync_api import Page, expect

from .conftest import BACKEND_URL, TEST_MUSIC_FOLDER


class TestComparePage:
    """对比分析页测试 - 双音频并排布局版本"""

    def test_compare_page_loads(self, page: Page):
        """测试对比分析独立页面加载"""
        page.goto(f"{BACKEND_URL}/compare.html", timeout=30000, wait_until="domcontentloaded")

        # 验证页面标题
        expect(page).to_have_title("对比分析 - 声乐评估系统")

        # 验证双音频卡片显示
        standard_card = page.locator("#standardCard")
        user_card = page.locator("#userCard")
        expect(standard_card).to_be_visible()
        expect(user_card).to_be_visible()

    def test_audio_cards_display(self, page: Page):
        """测试音频卡片显示"""
        page.goto(f"{BACKEND_URL}/compare.html", timeout=30000, wait_until="domcontentloaded")

        # 验证标准音频卡片
        standard_card = page.locator("#standardCard")
        expect(standard_card).to_be_visible()
        expect(standard_card).to_contain_text("标准音频")

        # 验证用户音频卡片
        user_card = page.locator("#userCard")
        expect(user_card).to_be_visible()
        expect(user_card).to_contain_text("待评估音频")

    def test_upload_areas_visible(self, page: Page):
        """测试上传区域可见"""
        page.goto(f"{BACKEND_URL}/compare.html", timeout=30000, wait_until="domcontentloaded")

        # 验证上传区域存在
        standard_upload = page.locator("#standardUpload")
        user_upload = page.locator("#userUpload")
        expect(standard_upload).to_be_visible()
        expect(user_upload).to_be_visible()

        # 验证提示文本
        expect(standard_upload).to_contain_text("点击选择标准音频")
        expect(user_upload).to_contain_text("点击选择您的演唱")

    def test_analyze_button_disabled_initially(self, page: Page):
        """测试分析按钮初始禁用状态"""
        page.goto(f"{BACKEND_URL}/compare.html", timeout=30000, wait_until="domcontentloaded")

        # 分析按钮初始应该禁用（因为没有用户音频）
        analyze_btn = page.locator("#analyzeBtn")
        expect(analyze_btn).to_be_disabled()

    def test_result_panel_hidden_initially(self, page: Page):
        """测试结果面板初始隐藏"""
        page.goto(f"{BACKEND_URL}/compare.html", timeout=30000, wait_until="domcontentloaded")

        # 结果面板初始隐藏
        result_panel = page.locator("#resultPanel")
        expect(result_panel).not_to_be_visible()

    def test_upload_standard_audio(self, page: Page, create_test_audio):
        """测试上传标准音频"""
        test_file = create_test_audio

        page.goto(f"{BACKEND_URL}/compare.html", timeout=30000, wait_until="domcontentloaded")

        # 监听文件选择对话框
        with page.expect_file_chooser() as fc_info:
            upload_area = page.locator("#standardUpload")
            upload_area.click()

        # 设置文件
        file_chooser = fc_info.value
        file_chooser.set_files(str(test_file))

        # 验证文件已加载
        standard_card = page.locator("#standardCard")
        expect(standard_card).to_have_class("audio-card standard has-file", timeout=5000)

        # 验证文件名显示
        standard_file_name = page.locator("#standardFileName")
        expect(standard_file_name).not_to_have_text("-", timeout=5000)

    def test_upload_user_audio(self, page: Page, create_test_audio):
        """测试上传用户音频"""
        test_file = create_test_audio

        page.goto(f"{BACKEND_URL}/compare.html", timeout=30000, wait_until="domcontentloaded")

        # 上传用户音频
        with page.expect_file_chooser() as fc_info:
            page.locator("#userUpload").click()
        fc_info.value.set_files(str(test_file))

        # 验证文件已加载
        user_card = page.locator("#userCard")
        expect(user_card).to_have_class("audio-card user has-file", timeout=5000)

        # 分析按钮应该启用
        analyze_btn = page.locator("#analyzeBtn")
        expect(analyze_btn).not_to_be_disabled(timeout=5000)

    def test_tip_banner_shows_without_standard(self, page: Page, create_test_audio):
        """测试没有标准音频时显示提示"""
        test_file = create_test_audio

        page.goto(f"{BACKEND_URL}/compare.html", timeout=30000, wait_until="domcontentloaded")

        # 直接上传用户音频（没有标准音频）
        with page.expect_file_chooser() as fc_info:
            page.locator("#userUpload").click()
        fc_info.value.set_files(str(test_file))

        # 提示横幅应该显示
        tip_banner = page.locator("#tipBanner")
        expect(tip_banner).to_have_class("tip-banner show", timeout=5000)


class TestCompareAnalysis:
    """对比分析完整流程测试"""

    def test_full_compare_analysis(self, page: Page, create_test_audio):
        """测试完整对比分析流程（有标准音频）"""
        test_file = create_test_audio

        page.goto(f"{BACKEND_URL}/compare.html", timeout=30000, wait_until="domcontentloaded")

        # Step 1: 上传标准音频
        with page.expect_file_chooser() as fc_info:
            page.locator("#standardUpload").click()
        fc_info.value.set_files(str(test_file))

        # 等待标准音频加载
        expect(page.locator("#standardCard")).to_have_class("audio-card standard has-file", timeout=5000)

        # Step 2: 上传用户音频
        with page.expect_file_chooser() as fc_info2:
            page.locator("#userUpload").click()
        fc_info2.value.set_files(str(test_file))

        # 等待用户音频加载
        expect(page.locator("#userCard")).to_have_class("audio-card user has-file", timeout=5000)

        # 分析按钮应该启用
        analyze_btn = page.locator("#analyzeBtn")
        expect(analyze_btn).not_to_be_disabled(timeout=5000)

        # Step 3: 点击开始分析
        analyze_btn.click()

        # Step 4: 验证结果显示
        result_panel = page.locator("#resultPanel")
        expect(result_panel).to_be_visible(timeout=60000)

        # 验证分数显示
        result_score = page.locator("#resultScore")
        expect(result_score).to_be_visible()
        score_text = result_score.text_content()
        assert score_text is not None and score_text != "--", "应该显示评分"

    def test_analysis_without_standard(self, page: Page, create_test_audio):
        """测试无标准音频的分析（独立评估模式）"""
        test_file = create_test_audio

        page.goto(f"{BACKEND_URL}/compare.html", timeout=30000, wait_until="domcontentloaded")

        # 只上传用户音频
        with page.expect_file_chooser() as fc_info:
            page.locator("#userUpload").click()
        fc_info.value.set_files(str(test_file))

        # 点击开始分析
        analyze_btn = page.locator("#analyzeBtn")
        expect(analyze_btn).not_to_be_disabled(timeout=5000)
        analyze_btn.click()

        # 等待分析完成（快速模式约 30-60 秒）
        # 先等待按钮变为 loading 状态
        expect(analyze_btn).to_have_class("analyze-btn loading", timeout=5000)

        # 验证结果显示（快速模式可能需要 60 秒以上）
        result_panel = page.locator("#resultPanel")
        expect(result_panel).to_be_visible(timeout=120000)

        # 验证分数显示
        result_score = page.locator("#resultScore")
        expect(result_score).to_be_visible()


class TestCompareUI:
    """对比分析 UI 交互测试"""

    def test_audio_player_display(self, page: Page, create_test_audio):
        """测试音频播放器显示"""
        test_file = create_test_audio

        page.goto(f"{BACKEND_URL}/compare.html", timeout=30000, wait_until="domcontentloaded")

        # 上传标准音频
        with page.expect_file_chooser() as fc_info:
            page.locator("#standardUpload").click()
        fc_info.value.set_files(str(test_file))

        # 播放器应该显示
        standard_player = page.locator("#standardPlayer")
        expect(standard_player).to_be_visible(timeout=5000)

        # 播放按钮应该存在
        play_btn = page.locator("#standardPlayBtn")
        expect(play_btn).to_be_visible()

    def test_play_button_interaction(self, page: Page, create_test_audio):
        """测试播放按钮交互"""
        test_file = create_test_audio

        page.goto(f"{BACKEND_URL}/compare.html", timeout=30000, wait_until="domcontentloaded")

        # 上传标准音频
        with page.expect_file_chooser() as fc_info:
            page.locator("#standardUpload").click()
        fc_info.value.set_files(str(test_file))

        # 等待播放器显示
        play_btn = page.locator("#standardPlayBtn")
        expect(play_btn).to_be_visible(timeout=5000)

        # 点击播放
        play_btn.click()

        # 按钮应该变为播放状态
        expect(play_btn).to_have_class("play-btn playing", timeout=2000)

    def test_result_dimensions_display(self, page: Page, create_test_audio):
        """测试结果维度对比显示"""
        test_file = create_test_audio

        page.goto(f"{BACKEND_URL}/compare.html", timeout=30000, wait_until="domcontentloaded")

        # 完成对比流程
        with page.expect_file_chooser() as fc_info:
            page.locator("#standardUpload").click()
        fc_info.value.set_files(str(test_file))

        with page.expect_file_chooser() as fc_info2:
            page.locator("#userUpload").click()
        fc_info2.value.set_files(str(test_file))

        page.locator("#analyzeBtn").click()

        # 等待结果
        expect(page.locator("#resultPanel")).to_be_visible(timeout=60000)

        # 验证维度对比区域
        dimension_compare = page.locator("#dimensionCompare")
        expect(dimension_compare).to_be_visible()

        # 验证建议列表
        suggestion_list = page.locator("#suggestionList")
        expect(suggestion_list).to_be_visible()

    def test_reset_functionality(self, page: Page, create_test_audio):
        """测试重置功能"""
        test_file = create_test_audio

        page.goto(f"{BACKEND_URL}/compare.html", timeout=30000, wait_until="domcontentloaded")

        # 上传音频并分析
        with page.expect_file_chooser() as fc_info:
            page.locator("#standardUpload").click()
        fc_info.value.set_files(str(test_file))

        with page.expect_file_chooser() as fc_info2:
            page.locator("#userUpload").click()
        fc_info2.value.set_files(str(test_file))

        page.locator("#analyzeBtn").click()
        expect(page.locator("#resultPanel")).to_be_visible(timeout=60000)

        # 点击重新分析按钮
        reset_btn = page.locator("button:has-text('重新分析')")
        reset_btn.click()

        # 结果面板应该隐藏
        expect(page.locator("#resultPanel")).not_to_be_visible()

        # 分析按钮应该禁用
        expect(page.locator("#analyzeBtn")).to_be_disabled()


class TestCompareResponsive:
    """对比分析响应式测试"""

    def test_mobile_view(self, page: Page):
        """测试移动端视图"""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(f"{BACKEND_URL}/compare.html", timeout=30000, wait_until="domcontentloaded")

        # 验证页面加载
        expect(page.locator("#standardCard")).to_be_visible()
        expect(page.locator("#userCard")).to_be_visible()

        # 验证导航栏
        navbar = page.locator(".navbar")
        expect(navbar).to_be_visible()

    def test_tablet_view(self, page: Page):
        """测试平板视图"""
        page.set_viewport_size({"width": 768, "height": 1024})
        page.goto(f"{BACKEND_URL}/compare.html", timeout=30000, wait_until="domcontentloaded")

        # 验证页面加载
        expect(page.locator("#standardCard")).to_be_visible()
        expect(page.locator("#userCard")).to_be_visible()

        # 验证容器宽度适应
        container = page.locator(".compare-container")
        expect(container).to_be_visible()

    def test_desktop_view(self, page: Page):
        """测试桌面端视图"""
        page.set_viewport_size({"width": 1440, "height": 900})
        page.goto(f"{BACKEND_URL}/compare.html", timeout=30000, wait_until="domcontentloaded")

        # 验证页面加载
        expect(page.locator("#standardCard")).to_be_visible()
        expect(page.locator("#userCard")).to_be_visible()

        # 验证容器宽度适应
        container = page.locator(".compare-container")
        expect(container).to_be_visible()


class TestCompareNavigation:
    """对比分析页面导航测试"""

    def test_back_to_home(self, page: Page):
        """测试返回首页按钮"""
        page.goto(f"{BACKEND_URL}/compare.html", timeout=30000, wait_until="domcontentloaded")

        # 点击返回首页
        back_btn = page.locator(".nav-tab")
        back_btn.click()

        # 验证跳转到首页
        expect(page).to_have_url(BACKEND_URL + "/")