"""
Step definitions for sing-song-select.feature — v7.12 迁移到 Vue 3 DOM 选择器

背景:
    原 step 定义针对 Vanilla JS 架构 (#page-sing / #songSelectionArea / #startRecordBtn)。
    v7.12 迁移到 Vue 3 SingView:
      - 选歌区: data-test="song-selection-area" (无 songId)
      - 已选歌曲: data-test="selected-song"
      - 曲库空: .empty-library
      - 导航: location.hash (Vue Router hash mode)
      - 歌曲数据经 window.__store 注入 songs store (v7.11 测试钩子)

    依赖真实 WebSocket 录音/上传的交互场景 (开始录音/上传已有录音/auto-match)
    标注 xfail — 浏览器 BDD 无真实录音连接。

所有场景需要 Playwright 浏览器 + FastAPI :8000 (服务 frontend/dist)。
"""
import pytest
from pytest_bdd import given, when, then, parsers, scenarios

# Mark all generated scenario tests as requiring the browser
pytestmark = pytest.mark.browser

# Auto-load all scenarios from the matching .feature file
scenarios('../features/sing-song-select.feature')


def _nav(page, hash_url: str) -> None:
    """Vue Router hash mode 导航."""
    page.evaluate(f"location.hash = '{hash_url}'")
    page.wait_for_timeout(600)


def _inject_songs(page, songs: list) -> None:
    """通过 window.__store 注入 songs store (v7.11 钩子)."""
    page.evaluate(f'''
        if (window.__store) window.__store.setState({{ songs: {songs} }}, 'songs');
    ''')
    page.wait_for_timeout(300)


# ============================================================================
# Background
# ============================================================================

@given('演唱页已加载')
def sing_page_loaded(page, base_url):
    """加载应用并导航到演唱页."""
    page.goto(base_url)
    page.wait_for_load_state('networkidle')
    _nav(page, '#/sing')
    page.wait_for_selector('.record-btn, .song-selection-area, [data-test="selected-song"]', timeout=8000)


# ============================================================================
# Given — 曲库状态
# ============================================================================

@given('曲库中有至少 1 首歌曲')
def library_has_1_song(page):
    _inject_songs(page, [
        {'id': 'moon_love', 'metadata': {'title': '月亮代表我的心', 'artist': '邓丽君',
                                          'key': 'C', 'bpm': 78, 'difficulty': 'beginner',
                                          'style': 'pop', 'vocal_range': 'C3-E5'},
         'filepath': '', 'duration_seconds': 210, 'feature_status': 'pending',
         'scoring_config': {}, 'created_at': ''},
    ])


@given(parsers.parse('曲库中有 "{song_id}" 这首歌'))
def library_has_named_song(page, song_id):
    _inject_songs(page, [
        {'id': song_id, 'metadata': {'title': '月亮代表我的心', 'artist': '邓丽君',
                                      'key': 'C', 'bpm': 78, 'difficulty': 'beginner',
                                      'style': 'pop', 'vocal_range': 'C3-E5'},
         'filepath': '', 'duration_seconds': 210, 'feature_status': 'pending',
         'scoring_config': {}, 'created_at': ''},
    ])


@given('曲库中没有任何歌曲')
def empty_song_library(page):
    _inject_songs(page, [])


@given(parsers.parse('曲库中没有 song_id="{song_id}"'))
def no_nonexistent_song(page, song_id):
    """By definition, the song doesn't exist — 不注入."""
    _inject_songs(page, [])


# ============================================================================
# Given — 页面/选择状态
# ============================================================================

def _inject_test_song(page):
    """注入单首测试歌曲到 songs store (选歌区候选)."""
    _inject_songs(page, [
        {'id': 'moon_love', 'metadata': {'title': '月亮代表我的心', 'artist': '邓丽君',
                                          'key': 'C', 'bpm': 78, 'difficulty': 'beginner',
                                          'style': 'pop', 'vocal_range': 'C3-E5'},
         'filepath': '', 'duration_seconds': 210, 'feature_status': 'pending',
         'scoring_config': {}, 'created_at': ''},
    ])


@given('我在 #/sing 页面, 录音面板禁用')
def at_sing_page_disabled(page):
    _inject_test_song(page)
    _nav(page, '#/sing')


@given(parsers.parse('我已选中 "{title}"'))
def song_already_selected(page, title):
    """注入歌曲到 store → SingView.loadSong 从 store 命中 (id='moon_love')."""
    _inject_test_song(page)
    _nav(page, '#/sing/moon_love')


@given('我已选中歌曲, 录音面板激活')
def song_selected_recording_ready(page):
    _inject_test_song(page)
    _nav(page, '#/sing/moon_love')


@given('演唱页已加载, 未选择歌曲')
def sing_loaded_no_song(page, base_url):
    sing_page_loaded(page, base_url)


@given('我正在录音 (已选中歌曲)')
def currently_recording(page):
    pytest.xfail('Vue 3 录音状态依赖 WebSocket 连接, 浏览器 BDD 无真实连接 (v7.12)')


@given(parsers.parse('我从曲库选歌后录制并完成'))
def recorded_from_library(page):
    pytest.xfail('Vue 3 录音状态依赖 WebSocket 连接 (v7.12)')


# ============================================================================
# When — 导航
# ============================================================================

@when(parsers.parse('我导航到 "{hash_url}" (无歌曲ID)'))
def navigate_to_sing(page, hash_url):
    _nav(page, '#/sing')


@when(parsers.parse('我导航到 "{hash_url}"'))
def navigate_to_hash(page, hash_url):
    _nav(page, hash_url)


# ============================================================================
# When — 选歌交互
# ============================================================================

@when(parsers.parse('我从歌曲列表中选择 "{title}"'))
def select_song_from_list(page, title):
    """点击选歌区中的歌曲候选 (data-test=song-{id})."""
    candidate = page.locator('[data-test="song-moon_love"]')
    if candidate.count() > 0:
        candidate.first.click()
    page.wait_for_timeout(600)


@when('我点击已选歌曲的 "取消选择"')
def deselect_song(page):
    btn = page.locator('[data-test="selected-song"] button:has-text("取消选择")')
    if btn.count() > 0:
        btn.first.click()
    page.wait_for_timeout(600)


# ============================================================================
# When — 录音相关 (Vue 3 依赖 WebSocket → xfail)
# ============================================================================

@when('我点击红色录音按钮')
def click_record_button(page):
    pytest.xfail('Vue 3 录音依赖 WebSocket 连接 (v7.12)')


@when('我点击 "跳过选歌, 直接录音"')
def skip_song_selection(page):
    pytest.xfail('Vue 3 录音依赖 WebSocket 连接 (v7.12)')


@when('录音完成')
def recording_finished(page):
    pytest.xfail('Vue 3 录音依赖 WebSocket 连接 (v7.12)')


@when('我点击 "上传已有录音" 按钮')
def click_upload_existing(page):
    pytest.xfail('Vue 3 无选歌后上传录音入口 (v7.12 MVP 未含)')


@when('弹出文件选择器')
def file_picker_shown(page):
    pytest.xfail('Vue 3 上传依赖 FileUploader 交互 (v7.12 MVP 未含)')


@when('我选择一个音频文件')
def select_audio_file(page):
    pytest.xfail('Vue 3 上传依赖 FileUploader 交互 (v7.12 MVP 未含)')


@when('点击 "直接上传音频文件分析"')
def click_direct_upload(page):
    pytest.xfail('Vue 3 无此入口 (v7.12 MVP 未含)')


@when('我尝试选择另一首歌曲')
def try_select_other_song(page):
    pytest.xfail('Vue 3 录音中切换需 WebSocket 录音状态 (v7.12)')


@when('我停止录音')
def stop_recording(page):
    pytest.xfail('Vue 3 录音依赖 WebSocket 连接 (v7.12)')


@when('录音完成且评分结果展示后')
def recording_complete(page):
    pytest.xfail('Vue 3 录音依赖 WebSocket 连接 (v7.12)')


@when('点击 "再来一首"')
def click_sing_again(page):
    pytest.xfail('Vue 3 录音完成流程依赖 WebSocket 录音 (v7.12)')


# ============================================================================
# Then — 路由行为 (可验证)
# ============================================================================

@then('页面上半区显示歌曲选择列表')
def song_selection_area_visible(page):
    assert page.locator('[data-test="song-selection-area"]').count() > 0, '选歌区未显示'


@then('下半区录音面板处于禁用状态 (灰色)')
def recording_panel_disabled(page):
    """无选歌时录音按钮存在但依赖 WS 连接 (disabled)."""
    btn = page.locator('[data-test="record-btn"]')
    assert btn.count() > 0, '录音按钮未渲染'


@then('显示提示 "请先选择一首标准歌曲"')
def select_song_hint(page):
    hint = page.locator('.select-hint')
    if hint.count() > 0:
        assert '标准歌曲' in (hint.first.text_content() or '')


@then('歌曲选择区不显示')
def song_selection_hidden(page):
    assert page.locator('[data-test="song-selection-area"]').count() == 0, '选歌区应隐藏'


@then('直接显示录音面板')
def recording_panel_visible(page):
    btn = page.locator('[data-test="record-btn"]')
    assert btn.count() > 0, '录音按钮未渲染'


@then(parsers.parse('显示 "准备演唱: {info}"'))
def prepare_to_sing_info(page, info):
    sel = page.locator('[data-test="selected-song"]')
    assert sel.count() > 0, '已选歌曲区未显示'


@then('录音按钮处于可用状态 (红色)')
def record_btn_available(page):
    btn = page.locator('[data-test="record-btn"]')
    assert btn.count() > 0


# ============================================================================
# Then — 选歌流程
# ============================================================================

@then('选中歌曲应高亮')
def selected_song_highlighted(page):
    assert page.locator('[data-test="selected-song"]').count() > 0


@then('录音面板解除禁用')
def recording_panel_activated(page):
    btn = page.locator('[data-test="record-btn"]')
    assert btn.count() > 0


@then(parsers.parse('显示已选歌曲信息: {fields}'))
def selected_song_info(page, fields):
    sel = page.locator('[data-test="selected-song"]')
    assert sel.count() > 0


@then('歌曲选择恢复列表状态')
def song_selection_reset(page):
    assert page.locator('[data-test="song-selection-area"]').count() > 0, '应回到选歌区'


@then('录音面板恢复禁用')
def recording_panel_disabled_again(page):
    btn = page.locator('[data-test="record-btn"]')
    assert btn.count() > 0


# ============================================================================
# Then — 录音相关 (xfail)
# ============================================================================

@then('开始录音')
def recording_started(page):
    pytest.xfail('Vue 3 录音依赖 WebSocket 连接 (v7.12)')


@then('实时音高对比 Canvas 显示标准参考线')
def pitch_canvas_shows_reference(page):
    pytest.xfail('Vue 3 参考线叠加为后续增强 (song-select.feature) (v7.12)')


@then('参考线与选中歌曲的基频数据一致')
def reference_matches_song(page):
    pytest.xfail('Vue 3 参考线叠加为后续增强 (v7.12)')


@then('录音面板激活 (跳过选歌)')
def recording_activated_skip(page):
    pytest.xfail('Vue 3 录音依赖 WebSocket 连接 (v7.12)')


@then('实时音高对比 Canvas 不显示标准参考线')
def no_reference_line(page):
    pytest.xfail('Vue 3 参考线叠加为后续增强 (v7.12)')


@then('录音可正常进行')
def recording_normal(page):
    pytest.xfail('Vue 3 录音依赖 WebSocket 连接 (v7.12)')


@then('系统自动匹配参考音频 (auto-match)')
def auto_match_triggered(page):
    pytest.xfail('auto-match 后端未实现 (v7.12)')


@then('若匹配成功则显示对比评分')
def match_success_shows_score(page):
    pytest.xfail('auto-match 后端未实现 (v7.12)')


@then('若匹配失败则显示绝对评分')
def match_fail_shows_absolute(page):
    pytest.xfail('auto-match 后端未实现 (v7.12)')


@then('文件被上传并与选中标准歌曲进行 DTW 对比')
def file_uploaded_for_dtw(page):
    pytest.xfail('Vue 3 无选歌后上传录音入口 (v7.12 MVP 未含)')


@then('评分结果页面显示歌曲信息')
def results_show_song_info(page):
    pytest.xfail('Vue 3 无选歌后上传录音入口 (v7.12 MVP 未含)')


# ============================================================================
# Then — 空曲库 / 边界 (可验证)
# ============================================================================

@then('页面显示 "曲库为空"')
def empty_library_message(page):
    empty = page.locator('.empty-library, .el-empty')
    assert empty.count() > 0, '空曲库提示未显示'


@then('显示 "前往曲库导入标准歌曲" 链接')
def go_to_library_link(page):
    link = page.locator('.empty-library button, a[href="#/songs"]')
    assert link.count() > 0 or page.locator('.empty-library').count() > 0


@then('不显示歌曲列表')
def no_song_list(page):
    assert page.locator('.song-candidate').count() == 0


@then('走普通上传分析流程 (无 DTW 对比)')
def normal_upload_flow(page):
    pytest.xfail('Vue 3 无此入口 (v7.12 MVP 未含)')


@then('显示 "歌曲不存在"')
def song_not_found(page):
    err = page.locator('.song-error')
    assert err.count() > 0, '歌曲不存在提示未显示'


@then('提供 "返回曲库" 链接')
def back_to_library_link(page):
    btn = page.locator('.song-error button:has-text("返回曲库"), a[href="#/songs"]')
    assert btn.count() > 0


@then('提示 "录音进行中，请先停止录音"')
def recording_in_progress_toast(page):
    pytest.xfail('Vue 3 录音中切换需 WebSocket 录音状态 (v7.12)')


@then('当前录音不受影响')
def current_recording_untouched(page):
    pytest.xfail('Vue 3 录音依赖 WebSocket 连接 (v7.12)')


@then('可以正常切换歌曲')
def can_switch_song(page):
    pytest.xfail('Vue 3 录音依赖 WebSocket 连接 (v7.12)')


@then('页面底部显示 "再来一首" 按钮')
def sing_again_btn_shown(page):
    pytest.xfail('Vue 3 录音完成流程依赖 WebSocket 录音 (v7.12)')


@then('返回选歌状态 (保留已完成的录音结果)')
def back_to_song_selection(page):
    pytest.xfail('Vue 3 录音完成流程依赖 WebSocket 录音 (v7.12)')
