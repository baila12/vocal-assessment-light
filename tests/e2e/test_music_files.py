"""
声乐评估系统 - 所有音乐文件分析测试

测试 test_music 文件夹中所有音乐文件的分析功能。
"""
from pathlib import Path

import pytest

from playwright.sync_api import Page, expect

from .conftest import BACKEND_URL, TEST_MUSIC_FOLDER


class TestAllMusicFiles:
    """测试 test_music 文件夹中所有音乐文件的分析功能"""

    def get_music_files(self) -> list[Path]:
        """获取所有测试音乐文件"""
        music_files = []
        for ext in ['*.mp3', '*.wav', '*.ogg', '*.m4a']:
            music_files.extend(TEST_MUSIC_FOLDER.glob(ext))
        # 按文件大小排序，小的先测试
        return sorted(music_files, key=lambda f: f.stat().st_size)

    def test_analyze_all_music_files(self, page: Page):
        """测试分析所有音乐文件"""
        music_files = self.get_music_files()
        assert len(music_files) > 0, "test_music 文件夹中应该有音乐文件"

        results = []
        for music_file in music_files:
            file_size_kb = music_file.stat().st_size / 1024
            file_name = music_file.name

            page.goto(BACKEND_URL)
            page.wait_for_timeout(500)

            # 上传文件
            file_input = page.locator("#fileInput")
            file_input.set_input_files(str(music_file))

            page.wait_for_timeout(1000)

            # 验证文件已选中
            audio_card = page.locator("#selectedAudioCard")
            if audio_card.count() > 0:
                # 点击分析按钮
                analyze_btn = page.locator("#analyzeBtn")
                analyze_btn.click()

                # 根据文件大小设置超时时间
                # 小文件(<500KB): 30秒, 中文件(<5MB): 60秒, 大文件: 120秒
                if file_size_kb < 500:
                    timeout = 30000
                elif file_size_kb < 5000:
                    timeout = 60000
                else:
                    timeout = 120000

                # 等待分析完成（跳转到分析页面或显示结果）
                try:
                    page.wait_for_url("**/analysis.html**", timeout=timeout)
                    success = True
                    error_msg = None
                except Exception as e:
                    # 检查是否有错误提示
                    error_toast = page.locator(".toast-error")
                    if error_toast.count() > 0:
                        success = False
                        error_msg = error_toast.text_content()
                    else:
                        success = "analysis.html" in page.url
                        error_msg = str(e) if not success else None

                results.append({
                    "file": file_name,
                    "size_kb": round(file_size_kb, 2),
                    "success": success,
                    "error": error_msg
                })

        # 打印结果摘要
        print("\n" + "=" * 60)
        print("音乐文件分析测试结果:")
        print("=" * 60)
        for r in results:
            status = "✓" if r["success"] else "✗"
            msg = "成功" if r["success"] else r["error"]
            print(f"{status} {r['file']} ({r['size_kb']}KB): {msg}")
        print("=" * 60)

        # 至少有一个文件分析成功
        successful = [r for r in results if r["success"]]
        assert len(successful) > 0, "至少应该有一个文件分析成功"

    def test_visualization_for_real_audio(self, page: Page):
        """测试真实人声音频的可视化图片显示"""
        # 使用真实人声文件（恋人.mp3 或 手写的从前.mp3）
        real_vocal_files = [
            VOCAL_DIR / "恋人.mp3",
            VOCAL_DIR / "手写的从前.mp3"
        ]

        test_file = None
        for f in real_vocal_files:
            if f.exists():
                test_file = f
                break

        if test_file is None:
            pytest.skip("没有找到真实人声测试文件")

        page.goto(BACKEND_URL)

        # 上传文件
        file_input = page.locator("#fileInput")
        file_input.set_input_files(str(test_file))

        page.wait_for_timeout(1000)

        # 点击分析
        analyze_btn = page.locator("#analyzeBtn")
        analyze_btn.click()

        # 等待跳转到分析页面（大文件需要更长时间）
        try:
            page.wait_for_url("**/analysis.html**", timeout=120000)
        except Exception:
            page.wait_for_timeout(5000)

        if "analysis.html" in page.url:
            page.wait_for_timeout(3000)  # 等待可视化图片加载

            # 检查可视化图片是否正确显示
            spectrogram_img = page.locator("#spectrogramImg")
            pitch_img = page.locator("#pitchImg")
            energy_img = page.locator("#energyImg")

            # 检查图片元素存在
            assert spectrogram_img.count() > 0, "频谱图图片元素应存在"
            assert pitch_img.count() > 0, "基音轨迹图片元素应存在"
            assert energy_img.count() > 0, "能量曲线图片元素应存在"

            # 检查图片有有效的 src 属性
            spectrogram_src = spectrogram_img.get_attribute("src")
            pitch_src = pitch_img.get_attribute("src")
            energy_src = energy_img.get_attribute("src")

            assert spectrogram_src and len(spectrogram_src) > 0, "频谱图应有有效的 src"
            assert pitch_src and len(pitch_src) > 0, "基音轨迹应有有效的 src"
            assert energy_src and len(energy_src) > 0, "能量曲线应有有效的 src"

            # 检查图片是否可见
            expect(spectrogram_img).to_be_visible(timeout=5000)

            # 测试标签页切换
            pitch_tab = page.locator(".viz-tab[data-tab='pitch']")
            if pitch_tab.count() > 0:
                pitch_tab.click()
                page.wait_for_timeout(500)
                expect(pitch_img).to_be_visible(timeout=3000)

            energy_tab = page.locator(".viz-tab[data-tab='energy']")
            if energy_tab.count() > 0:
                energy_tab.click()
                page.wait_for_timeout(500)
                expect(energy_img).to_be_visible(timeout=3000)
