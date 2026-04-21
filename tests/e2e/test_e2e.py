"""
声乐评估系统 - E2E 测试 (Playwright)
测试首页加载、文件上传、分析结果、历史记录等核心流程

运行方式：
1. pytest tests/e2e/test_e2e.py -v
2. python tests/e2e/test_e2e.py (直接运行)

依赖：pip install pytest playwright
初始化：playwright install chromium
"""
import pytest
import os
import sys
import time
import socket
import subprocess
from pathlib import Path

from playwright.sync_api import Page, expect

# 项目路径配置
PROJECT_ROOT = Path(__file__).parent.parent
UPLOAD_FOLDER = PROJECT_ROOT / "uploads"
TEST_MUSIC_FOLDER = PROJECT_ROOT / "test_music"
WEB_APP_SCRIPT = PROJECT_ROOT / "web_app.py"

# 确保测试目录存在
UPLOAD_FOLDER.mkdir(exist_ok=True)
TEST_MUSIC_FOLDER.mkdir(exist_ok=True)

# 后端服务配置
BACKEND_URL = "http://localhost:5000"


@pytest.fixture(scope="session", autouse=True)
def backend_server():
    """启动 Flask 后端服务器"""
    # 检查是否已有服务运行
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', 5000))
    sock.close()

    if result == 0:
        print("\n[INFO] Flask 服务器已在运行")
        yield
        return

    # 启动服务器
    print("\n[INFO] 启动 Flask 服务器...")
    process = subprocess.Popen(
        [sys.executable, str(WEB_APP_SCRIPT)],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, 'FLASK_ENV': 'testing'}
    )

    # 等待服务器启动（增加超时时间）
    max_wait = 30
    for i in range(max_wait):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if sock.connect_ex(('localhost', 5000)) == 0:
                sock.close()
                print(f"[INFO] Flask 服务器启动成功 (等待 {i+1} 秒)")
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        # 打印错误信息用于调试
        stdout, stderr = process.communicate(timeout=1)
        print(f"[ERROR] stdout: {stdout.decode('utf-8', errors='ignore')}")
        print(f"[ERROR] stderr: {stderr.decode('utf-8', errors='ignore')}")
        process.kill()
        raise RuntimeError("Flask 服务器启动超时")

    yield

    # 关闭服务器
    print("\n[INFO] 关闭 Flask 服务器...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def create_test_audio() -> Path:
    """创建测试音频文件（简单的正弦波）"""
    import numpy as np
    import wave

    test_file = TEST_MUSIC_FOLDER / "test_audio.wav"

    if test_file.exists():
        return test_file

    # 生成1秒的440Hz正弦波
    sample_rate = 22050
    duration = 1.0
    frequency = 440

    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = (np.sin(2 * np.pi * frequency * t) * 32767 * 0.5).astype(np.int16)

    with wave.open(str(test_file), 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())

    return test_file


class TestHomePage:
    """首页测试"""

    def test_home_page_loads(self, page: Page):
        """测试首页是否正常加载"""
        page.goto(BACKEND_URL)

        # 验证页面标题
        expect(page).to_have_title("声乐评估系统 - 离线版")

        # 验证导航栏存在
        navbar = page.locator(".navbar")
        expect(navbar).to_be_visible()

        # 验证主要按钮存在
        import_btn = page.get_by_role("button", name="导入音频")
        expect(import_btn).to_be_visible()

        record_btn = page.get_by_role("button", name="快速录音")
        expect(record_btn).to_be_visible()

    def test_navigation_tabs(self, page: Page):
        """测试导航标签切换"""
        page.goto(BACKEND_URL)

        # 默认应该显示首页
        home_page = page.locator("#page-home")
        expect(home_page).to_be_visible()

        # 点击对比分析标签
        compare_tab = page.get_by_role("button", name="对比分析")
        compare_tab.click()

        compare_page = page.locator("#page-compare")
        expect(compare_page).to_be_visible()
        expect(home_page).not_to_be_visible()

        # 点击历史记录标签
        history_tab = page.get_by_role("button", name="历史记录")
        history_tab.click()

        history_page = page.locator("#page-history")
        expect(history_page).to_be_visible()

    def test_sidebar_elements(self, page: Page):
        """测试侧边栏元素"""
        page.goto(BACKEND_URL)

        # 验证五维评分卡片
        dim_list = page.locator(".dim-list")
        expect(dim_list).to_be_visible()

        # 验证雷达图
        radar_card = page.locator("text=能力雷达图")
        expect(radar_card).to_be_visible()

        # 验证技巧提示
        tips_card = page.locator("text=技巧提示")
        expect(tips_card).to_be_visible()


class TestAudioUpload:
    """音频上传测试"""

    def test_upload_button_opens_dialog(self, page: Page):
        """测试上传按钮是否触发文件选择"""
        page.goto(BACKEND_URL)

        # 点击导入音频按钮
        import_btn = page.get_by_role("button", name="导入音频")
        import_btn.click()

        # 验证文件输入存在
        file_input = page.locator("#fileInput")
        expect(file_input).to_be_attached()

    def test_upload_audio_file(self, page: Page):
        """测试上传音频文件并显示播放器"""
        # 创建测试音频文件
        test_file = create_test_audio()

        page.goto(BACKEND_URL)

        # 上传文件
        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_file))

        # 等待加载完成
        page.wait_for_timeout(1000)

        # 验证文件名显示
        audio_filename = page.locator("#audioFilename")
        expect(audio_filename).to_contain_text("test_audio")

        # 验证分析按钮出现
        analyze_btn = page.locator("#analyzeBtn")
        expect(analyze_btn).to_be_visible()

        # 验证播放器出现
        player_section = page.locator("#playerSection")
        expect(player_section).to_be_visible()

    def test_analyze_audio(self, page: Page):
        """测试音频分析功能"""
        test_file = create_test_audio()

        page.goto(BACKEND_URL)

        # 上传文件
        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_file))
        page.wait_for_timeout(500)

        # 点击分析按钮
        analyze_btn = page.locator("#analyzeBtn")
        analyze_btn.click()

        # 等待分析进度出现
        progress_section = page.locator("#analysisProgress")
        expect(progress_section).to_be_visible(timeout=5000)

        # 等待分析完成 - 检查总分不为空（最多60秒）
        total_score = page.locator("#totalScore")
        expect(total_score).not_to_contain_text("--", timeout=60000)

        # 验证评分面板已显示
        score_panel = page.locator("#scorePanel")
        expect(score_panel).to_be_visible()

        # 验证建议显示
        advice_section = page.locator("#adviceSection")
        expect(advice_section).to_be_visible()


class TestScoreDisplay:
    """评分显示测试"""

    def test_five_dimension_scores(self, page: Page):
        """测试五维评分显示"""
        test_file = create_test_audio()

        page.goto(BACKEND_URL)

        # 上传并分析
        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_file))

        analyze_btn = page.locator("#analyzeBtn")
        analyze_btn.click()

        # 等待分析完成
        page.wait_for_selector("#dimVolume:not(:has-text('--'))", timeout=60000)

        # 验证各维度分数
        dimensions = ["Volume", "Pitch", "Rhythm", "Breath", "Emotion"]
        for dim in dimensions:
            dim_value = page.locator(f"#dim{dim}")
            expect(dim_value).not_to_contain_text("--")

            # 验证进度条有宽度
            dim_bar = page.locator(f"#dim{dim}Bar")
            bar_style = dim_bar.get_attribute("style")
            assert "width" in bar_style and "0%" not in bar_style

    def test_radar_chart_updates(self, page: Page):
        """测试雷达图更新"""
        test_file = create_test_audio()

        page.goto(BACKEND_URL)

        # 上传并分析
        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_file))

        analyze_btn = page.locator("#analyzeBtn")
        analyze_btn.click()

        # 等待分析完成
        page.wait_for_selector("#totalScore:not(:has-text('--'))", timeout=60000)

        # 验证雷达图存在
        radar_canvas = page.locator("#radarChart")
        expect(radar_canvas).to_be_visible()

    def test_level_display(self, page: Page):
        """测试等级显示"""
        test_file = create_test_audio()

        page.goto(BACKEND_URL)

        # 上传并分析
        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_file))

        analyze_btn = page.locator("#analyzeBtn")
        analyze_btn.click()

        # 等待分析完成
        page.wait_for_selector("#scoreLevel:not(:has-text('等待分析'))", timeout=60000)

        # 验证等级显示
        score_level = page.locator("#scoreLevel")
        text = score_level.text_content()
        valid_levels = ["优秀", "良好", "普通", "一般", "待改进"]
        assert any(level in text for level in valid_levels), f"无效等级: {text}"


class TestHistoryPage:
    """历史记录页测试"""

    def test_history_page_loads(self, page: Page):
        """测试历史记录页加载"""
        page.goto(BACKEND_URL)

        # 点击历史记录标签
        history_tab = page.get_by_role("button", name="历史记录")
        history_tab.click()

        # 验证页面显示
        history_page = page.locator("#page-history")
        expect(history_page).to_be_visible()

        # 验证筛选按钮存在
        filter_btns = page.locator(".filter-btn")
        expect(filter_btns.first).to_be_visible()

    def test_history_list_display(self, page: Page):
        """测试历史记录列表显示"""
        # 先分析一个文件创建历史记录
        test_file = create_test_audio()

        page.goto(BACKEND_URL)

        # 上传并分析
        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_file))

        analyze_btn = page.locator("#analyzeBtn")
        analyze_btn.click()

        # 等待分析完成
        total_score = page.locator("#totalScore")
        expect(total_score).not_to_contain_text("--", timeout=60000)

        # 切换到历史记录页
        history_tab = page.get_by_role("button", name="历史记录")
        history_tab.click()

        # 等待历史记录加载
        page.wait_for_timeout(2000)

        # 验证历史记录容器存在
        history_grid = page.locator("#historyGrid")
        expect(history_grid).to_be_visible()

        # 验证有历史卡片显示
        history_cards = page.locator(".history-card")
        expect(history_cards.first).to_be_visible(timeout=5000)

    def test_date_filter_buttons(self, page: Page):
        """测试日期筛选按钮存在"""
        page.goto(BACKEND_URL)

        # 切换到历史记录页
        history_tab = page.get_by_role("button", name="历史记录")
        history_tab.click()

        # 验证筛选按钮存在并可点击
        today_btn = page.get_by_role("button", name="今天")
        expect(today_btn).to_be_visible()
        today_btn.click()

        week_btn = page.get_by_role("button", name="本周")
        expect(week_btn).to_be_visible()
        week_btn.click()

        all_btn = page.get_by_role("button", name="全部")
        expect(all_btn).to_be_visible()
        all_btn.click()


class TestComparePage:
    """对比分析页测试"""

    def test_compare_page_loads(self, page: Page):
        """测试对比分析页加载"""
        page.goto(BACKEND_URL)

        # 点击对比分析标签
        compare_tab = page.get_by_role("button", name="对比分析")
        compare_tab.click()

        # 验证页面显示
        compare_page = page.locator("#page-compare")
        expect(compare_page).to_be_visible()

        # 验证标题和描述
        compare_title = page.locator(".compare-title")
        expect(compare_title).to_contain_text("对比分析")


class TestResponsiveDesign:
    """响应式设计测试"""

    def test_mobile_viewport(self, page: Page):
        """测试移动端视口"""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(BACKEND_URL)

        # 验证页面仍然可用
        import_btn = page.get_by_role("button", name="导入音频")
        expect(import_btn).to_be_visible()

        # 验证布局适应
        main_content = page.locator(".main-content")
        expect(main_content).to_be_visible()

    def test_tablet_viewport(self, page: Page):
        """测试平板视口"""
        page.set_viewport_size({"width": 768, "height": 1024})
        page.goto(BACKEND_URL)

        # 验证侧边栏显示
        sidebar = page.locator(".sidebar")
        expect(sidebar).to_be_visible()

    def test_desktop_viewport(self, page: Page):
        """测试桌面视口"""
        page.set_viewport_size({"width": 1920, "height": 1080})
        page.goto(BACKEND_URL)

        # 验证完整布局
        home_layout = page.locator(".home-layout")
        expect(home_layout).to_be_visible()

        # 验证双栏布局
        expect(page.locator(".main-content")).to_be_visible()
        expect(page.locator(".sidebar")).to_be_visible()


class TestAccessibility:
    """可访问性测试"""

    def test_keyboard_navigation(self, page: Page):
        """测试键盘导航"""
        page.goto(BACKEND_URL)

        # Tab 键导航
        page.keyboard.press("Tab")
        page.keyboard.press("Tab")

        # 验证焦点元素
        focused_element = page.locator(":focus")
        expect(focused_element).to_be_visible()

    def test_button_labels(self, page: Page):
        """测试按钮标签"""
        page.goto(BACKEND_URL)

        # 验证按钮有明确的文本标签
        buttons = page.locator("button")
        count = buttons.count()

        for i in range(count):
            btn = buttons.nth(i)
            text = btn.text_content()
            assert text and text.strip(), f"按钮 {i} 缺少文本标签"


class TestTimbreAnalysis:
    """音色分析测试"""

    def test_timbre_section_display(self, page: Page):
        """测试音色分析区域显示"""
        test_file = create_test_audio()

        page.goto(BACKEND_URL)

        # 上传并分析
        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_file))

        analyze_btn = page.locator("#analyzeBtn")
        analyze_btn.click()

        # 等待分析完成
        page.wait_for_selector("#totalScore:not(:has-text('--'))", timeout=60000)

        # 验证音色分析区域显示
        timbre_section = page.locator("#timbreSection")
        expect(timbre_section).to_be_visible()

        # 验证音色风格标签
        timbre_style = page.locator("#timbreStyle")
        expect(timbre_style).not_to_contain_text("--")

    def test_timbre_metrics_display(self, page: Page):
        """测试音色指标显示"""
        test_file = create_test_audio()

        page.goto(BACKEND_URL)

        # 上传并分析
        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_file))

        analyze_btn = page.locator("#analyzeBtn")
        analyze_btn.click()

        # 等待分析完成
        page.wait_for_selector("#timbreSection", timeout=60000)

        # 验证各项音色指标
        metrics = ["Brightness", "Warmth", "Nasality", "Breathiness"]
        for metric in metrics:
            metric_el = page.locator(f"#timbre{metric}")
            expect(metric_el).not_to_contain_text("--")

        # 验证 HNR 显示
        hnr_el = page.locator("#timbreHNR")
        expect(hnr_el).to_contain_text("dB")


class TestPhraseAnalysis:
    """逐句评分测试"""

    def test_phrase_section_display(self, page: Page):
        """测试逐句评分区域显示"""
        test_file = create_test_audio()

        page.goto(BACKEND_URL)

        # 上传并分析
        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_file))

        analyze_btn = page.locator("#analyzeBtn")
        analyze_btn.click()

        # 等待分析完成
        page.wait_for_selector("#totalScore:not(:has-text('--'))", timeout=60000)

        # 验证逐句评分区域显示
        phrase_section = page.locator("#phraseSection")
        expect(phrase_section).to_be_visible()

    def test_phrase_list_display(self, page: Page):
        """测试逐句列表显示"""
        test_file = create_test_audio()

        page.goto(BACKEND_URL)

        # 上传并分析
        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_file))

        analyze_btn = page.locator("#analyzeBtn")
        analyze_btn.click()

        # 等待分析完成
        page.wait_for_selector("#phraseSection", timeout=60000)

        # 验证句数统计
        phrase_summary = page.locator("#phraseSummary")
        expect(phrase_summary).to_contain_text("句")

        # 验证句子列表
        phrase_list = page.locator("#phraseList")
        expect(phrase_list).to_be_visible()


class TestExportReport:
    """导出报告测试"""

    def test_export_section_display(self, page: Page):
        """测试导出区域显示"""
        test_file = create_test_audio()

        page.goto(BACKEND_URL)

        # 上传并分析
        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_file))

        analyze_btn = page.locator("#analyzeBtn")
        analyze_btn.click()

        # 等待分析完成
        page.wait_for_selector("#totalScore:not(:has-text('--'))", timeout=60000)

        # 验证导出区域显示
        export_section = page.locator("#exportSection")
        expect(export_section).to_be_visible()

    def test_export_buttons_exist(self, page: Page):
        """测试导出按钮存在"""
        test_file = create_test_audio()

        page.goto(BACKEND_URL)

        # 上传并分析
        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_file))

        analyze_btn = page.locator("#analyzeBtn")
        analyze_btn.click()

        # 等待分析完成
        page.wait_for_selector("#exportSection", timeout=60000)

        # 验证PDF导出按钮
        pdf_btn = page.get_by_role("button", name="导出 PDF 报告")
        expect(pdf_btn).to_be_visible()

        # 验证图片导出按钮
        image_btn = page.get_by_role("button", name="导出图片报告")
        expect(image_btn).to_be_visible()


class TestSeparationFeature:
    """人声分离功能测试"""

    def test_separation_button_display(self, page: Page):
        """测试人声分离按钮显示"""
        test_file = create_test_audio()

        page.goto(BACKEND_URL)

        # 上传文件
        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_file))

        page.wait_for_timeout(500)

        # 验证人声分离按钮显示
        separation_btn = page.locator("#separationBtn")
        expect(separation_btn).to_be_visible()

    def test_separation_button_click(self, page: Page):
        """测试人声分离按钮点击（仅验证UI响应，不等待分离完成）"""
        test_file = create_test_audio()

        page.goto(BACKEND_URL)

        # 上传文件
        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_file))

        page.wait_for_timeout(500)

        # 点击人声分离按钮
        separation_btn = page.locator("#separationBtn")
        separation_btn.click()

        # 验证进度显示
        separation_progress = page.locator("#separationProgress")
        expect(separation_progress).to_be_visible(timeout=5000)


class TestVisualization:
    """可视化功能测试"""

    def test_feature_visualization_display(self, page: Page):
        """测试三特征可视化显示"""
        test_file = create_test_audio()

        page.goto(BACKEND_URL)

        # 上传并分析
        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_file))

        analyze_btn = page.locator("#analyzeBtn")
        analyze_btn.click()

        # 等待分析完成
        page.wait_for_selector("#totalScore:not(:has-text('--'))", timeout=60000)

        # 验证可视化区域显示
        viz_section = page.locator("#featureVisualization")
        expect(viz_section).to_be_visible()

    def test_visualization_tabs(self, page: Page):
        """测试可视化标签切换"""
        test_file = create_test_audio()

        page.goto(BACKEND_URL)

        # 上传并分析
        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_file))

        analyze_btn = page.locator("#analyzeBtn")
        analyze_btn.click()

        # 等待分析完成
        page.wait_for_selector("#featureVisualization", timeout=60000)

        # 点击分项查看标签
        separate_tab = page.locator(".viz-tab[data-tab='separate']")
        if separate_tab.is_visible():
            separate_tab.click()
            page.wait_for_timeout(300)

            # 验证分项面板显示
            separate_panel = page.locator(".viz-panel[data-panel='separate']")
            expect(separate_panel).to_be_visible()


class TestGrowthChart:
    """成长曲线测试"""

    def test_growth_chart_display(self, page: Page):
        """测试成长曲线显示"""
        test_file = create_test_audio()

        page.goto(BACKEND_URL)

        # 上传并分析（创建历史记录）
        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_file))

        analyze_btn = page.locator("#analyzeBtn")
        analyze_btn.click()

        # 等待分析完成
        page.wait_for_selector("#totalScore:not(:has-text('--'))", timeout=60000)

        # 切换到历史记录页
        history_tab = page.get_by_role("button", name="历史记录")
        history_tab.click()

        page.wait_for_timeout(1000)

        # 验证成长曲线区域
        growth_chart = page.locator("#growthChart")
        expect(growth_chart).to_be_visible()

    def test_growth_stats_display(self, page: Page):
        """测试成长统计显示"""
        test_file = create_test_audio()

        page.goto(BACKEND_URL)

        # 上传并分析
        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_file))

        analyze_btn = page.locator("#analyzeBtn")
        analyze_btn.click()

        # 等待分析完成
        page.wait_for_selector("#totalScore:not(:has-text('--'))", timeout=60000)

        # 切换到历史记录页
        history_tab = page.get_by_role("button", name="历史记录")
        history_tab.click()

        page.wait_for_timeout(1000)

        # 验证统计数据
        avg_score = page.locator("#avgScore")
        expect(avg_score).to_be_visible()


class TestFullWorkflow:
    """完整工作流测试"""

    def test_complete_analysis_workflow(self, page: Page):
        """测试完整分析工作流"""
        test_file = create_test_audio()

        page.goto(BACKEND_URL)

        # 1. 上传文件
        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_file))
        page.wait_for_timeout(500)

        # 2. 验证播放器显示
        player_section = page.locator("#playerSection")
        expect(player_section).to_be_visible()

        # 3. 点击分析
        analyze_btn = page.locator("#analyzeBtn")
        analyze_btn.click()

        # 4. 等待分析完成
        page.wait_for_selector("#totalScore:not(:has-text('--'))", timeout=60000)

        # 5. 验证所有结果区域显示
        expect(page.locator("#scorePanel")).to_be_visible()
        expect(page.locator("#adviceSection")).to_be_visible()
        expect(page.locator("#timbreSection")).to_be_visible()
        expect(page.locator("#phraseSection")).to_be_visible()
        expect(page.locator("#exportSection")).to_be_visible()

        # 6. 切换到历史记录验证
        history_tab = page.get_by_role("button", name="历史记录")
        history_tab.click()
        page.wait_for_timeout(500)
        expect(page.locator("#page-history")).to_be_visible()

        # 7. 返回首页
        home_tab = page.get_by_role("button", name="首页")
        home_tab.click()
        page.wait_for_timeout(500)
        expect(page.locator("#page-home")).to_be_visible()


# ============ 运行测试 ============
if __name__ == "__main__":
    # 使用 pytest 运行测试
    pytest.main([
        __file__,
        "-v",
        "--headed",  # 显示浏览器窗口
        "--slowmo=500",  # 每步操作间隔500ms
        "-s"  # 显示打印输出
    ])
