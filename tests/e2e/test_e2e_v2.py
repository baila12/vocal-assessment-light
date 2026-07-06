"""
声乐评估系统 - E2E 测试 v2.0 (Playwright)
测试新的页面跳转逻辑、评分系统、真实音频文件
"""
import pytest
import os
import sys
import time
import socket
import subprocess
from pathlib import Path

from playwright.sync_api import Page, expect

PROJECT_ROOT = Path(__file__).parent.parent.parent  # tests/e2e/ -> tests/ -> project root
UPLOAD_FOLDER = PROJECT_ROOT / "uploads"
TEST_DATA_DIR = PROJECT_ROOT / "tests" / "test_data" / "audio"
VOCAL_DIR = TEST_DATA_DIR / "vocal"
NON_VOCAL_DIR = TEST_DATA_DIR / "non_vocal"
WEB_APP_SCRIPT = PROJECT_ROOT / "web_app.py"

UPLOAD_FOLDER.mkdir(exist_ok=True)
TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)

BACKEND_URL = "http://localhost:5000"


@pytest.fixture(scope="session", autouse=True)
def backend_server():
    """启动 Flask 后端服务器"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', 5000))
    sock.close()

    if result == 0:
        print("\n[INFO] Flask 服务器已在运行")
        yield
        return

    print("\n[INFO] 启动 Flask 服务器...")
    process = subprocess.Popen(
        [sys.executable, str(WEB_APP_SCRIPT)],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, 'FLASK_ENV': 'testing'}
    )

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
        stdout, stderr = process.communicate(timeout=1)
        print(f"[ERROR] stdout: {stdout.decode('utf-8', errors='ignore')}")
        print(f"[ERROR] stderr: {stderr.decode('utf-8', errors='ignore')}")
        process.kill()
        raise RuntimeError("Flask 服务器启动超时")

    yield

    print("\n[INFO] 关闭 Flask 服务器...")
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def get_test_files():
    """获取测试音频文件列表"""
    test_files = {}

    # 真实音乐文件
    real_music = list(VOCAL_DIR.glob("*.mp3"))
    if real_music:
        test_files['real_music'] = real_music[0]

    # WAV 测试文件
    wav_files = list(NON_VOCAL_DIR.glob("*.wav"))
    for f in wav_files:
        if 'synthetic' in f.name:
            test_files['synthetic'] = f
        elif 'noise' in f.name:
            test_files['noise'] = f
        elif 'clipped' in f.name:
            test_files['clipped'] = f
        elif 'simulated' in f.name:
            test_files['simulated_voice'] = f
        else:
            test_files['wav'] = f

    return test_files


class TestHomePage:
    """首页测试"""

    def test_home_page_loads(self, page: Page):
        """测试首页是否正常加载"""
        page.goto(BACKEND_URL)
        expect(page).to_have_title("声乐评估系统 - 离线版")
        # fileInput is hidden, check for presence instead
        expect(page.locator("#fileInput")).to_be_attached()
        # Check for the action cards
        import_card = page.locator(".action-card.primary")
        expect(import_card).to_be_visible()

    def test_navigation_tabs(self, page: Page):
        """测试导航标签"""
        page.goto(BACKEND_URL)
        home_tab = page.get_by_role("button", name="首页")
        expect(home_tab).to_be_visible()
        history_tab = page.get_by_role("button", name="历史记录")
        expect(history_tab).to_be_visible()
        # 对比分析现在是链接
        compare_link = page.locator("#navCompare")
        expect(compare_link).to_be_visible()


class TestPageNavigation:
    """页面跳转测试"""

    def test_upload_redirects_to_analysis(self, page: Page):
        """测试上传后跳转到分析页面"""
        test_files = get_test_files()
        if 'synthetic' not in test_files:
            pytest.skip("No synthetic test file available")

        page.goto(BACKEND_URL)
        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_files['synthetic']))

        analyze_btn = page.locator("#analyzeBtn")
        analyze_btn.click()

        page.wait_for_url("**/analysis.html**", timeout=30000)
        expect(page).to_have_url(BACKEND_URL + "/analysis.html")

    def test_analysis_page_back_button(self, page: Page):
        """测试分析页面返回按钮"""
        page.goto(f"{BACKEND_URL}/analysis.html")
        back_btn = page.get_by_role("button", name="返回首页")
        back_btn.click()
        expect(page).to_have_url(BACKEND_URL + "/")


class TestVoiceQualityDetection:
    """人声质量检测测试"""

    def test_synthetic_audio_detection(self, page: Page):
        """测试合成音检测"""
        test_files = get_test_files()
        if 'synthetic' not in test_files:
            pytest.skip("No synthetic test file available")

        page.goto(BACKEND_URL)
        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_files['synthetic']))

        analyze_btn = page.locator("#analyzeBtn")
        analyze_btn.click()

        page.wait_for_url("**/analysis.html**", timeout=30000)

        warning = page.locator("#voiceQualityWarning")
        expect(warning).to_be_visible()

        total_score = page.locator("#totalScore")
        score_text = total_score.text_content()
        score = int(score_text) if score_text.isdigit() else 0
        assert score < 30, f"合成音应该得低分，实际得分: {score}"

    def test_noise_audio_detection(self, page: Page):
        """测试噪声检测"""
        test_files = get_test_files()
        if 'noise' not in test_files:
            pytest.skip("No noise test file available")

        page.goto(BACKEND_URL)
        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_files['noise']))

        analyze_btn = page.locator("#analyzeBtn")
        analyze_btn.click()

        page.wait_for_url("**/analysis.html**", timeout=30000)

        warning = page.locator("#voiceQualityWarning")
        expect(warning).to_be_visible()


class TestRealMusicAnalysis:
    """真实音乐分析测试"""

    def test_real_music_analysis(self, page: Page):
        """测试真实音乐文件分析"""
        test_files = get_test_files()
        if 'real_music' not in test_files:
            pytest.skip("No real music test file available")

        page.goto(BACKEND_URL)
        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_files['real_music']))

        analyze_btn = page.locator("#analyzeBtn")
        analyze_btn.click()

        page.wait_for_url("**/analysis.html**", timeout=120000)

        expect(page.locator("#totalScore")).to_be_visible()
        expect(page.locator("#levelText")).to_be_visible()

        scores_section = page.locator(".scores-grid")
        expect(scores_section).to_be_visible()


class TestAnalysisPageFeatures:
    """分析页面功能测试"""

    def test_audio_player_display(self, page: Page):
        """测试音频播放器显示"""
        test_files = get_test_files()
        if 'synthetic' not in test_files:
            pytest.skip("No test file available")

        page.goto(BACKEND_URL)
        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_files['synthetic']))

        analyze_btn = page.locator("#analyzeBtn")
        analyze_btn.click()

        page.wait_for_url("**/analysis.html**", timeout=30000)

        play_btn = page.locator("#playBtn")
        expect(play_btn).to_be_visible()

        progress_bar = page.locator("#progressBar")
        expect(progress_bar).to_be_visible()

    def test_visualization_tabs(self, page: Page):
        """测试可视化标签页"""
        test_files = get_test_files()
        if 'synthetic' not in test_files:
            pytest.skip("No test file available")

        page.goto(BACKEND_URL)
        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_files['synthetic']))

        analyze_btn = page.locator("#analyzeBtn")
        analyze_btn.click()

        page.wait_for_url("**/analysis.html**", timeout=30000)

        viz_tabs = page.locator(".viz-tab")
        expect(viz_tabs.first).to_be_visible()

        pitch_tab = page.locator(".viz-tab[data-tab='pitch']")
        if pitch_tab.is_visible():
            pitch_tab.click()
            page.wait_for_timeout(300)
            # Check that 'active' is in the class list
            expect(pitch_tab).to_have_class("viz-tab active")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
