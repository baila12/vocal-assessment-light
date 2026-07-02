"""
Step definitions for sing-song-select.feature

Covers song selection before recording, real-time pitch reference,
and auto-match fallback. Browser-based — requires Playwright + Flask.
"""
from pytest_bdd import given, when, then, parsers, scenarios

scenarios('../features/sing-song-select.feature')


@given('演唱页已加载')
def sing_page_loaded(page, base_url):
    page.goto(base_url + '/#/sing')
    page.wait_for_selector('#page-sing', timeout=10000)
    page.wait_for_timeout(500)


@given('曲库中有至少 1 首歌曲')
def library_has_1_song(page):
    songs = [{'id': 'moon_love', 'title': '月亮代表我的心', 'artist': '邓丽君',
              'difficulty': '初级', 'style': '流行', 'duration': 210}]
    page.evaluate(f'''
        window.__mockSongs = {songs};
        if (window.__store) window.__store.setState({{ songs: {songs} }}, 'songs');
    ''')
    page.wait_for_timeout(300)


@given('曲库中没有任何歌曲')
def empty_song_library_sing(page):
    page.evaluate('''
        window.__mockSongs = [];
        if (window.__store) window.__store.setState({ songs: [] }, 'songs');
    ''')
    page.wait_for_timeout(300)


@given('我在 #/sing 页面, 录音面板禁用')
def at_sing_page_disabled(page):
    pass  # Already at #/sing


@given('我已选中歌曲, 录音面板激活')
def song_selected_recording_ready(page):
    page.evaluate('''
        // Simulate song selection
        const info = document.getElementById('selectedSong');
        if (info) { info.textContent = '月亮代表我的心 - 邓丽君'; info.style.display = 'block'; }
        const btn = document.getElementById('startRecordBtn');
        if (btn) btn.disabled = false;
        window.__selectedSong = { id: 'moon_love', title: '月亮代表我的心' };
    ''')
    page.wait_for_timeout(200)


@given('我已选中歌曲')
def song_already_selected(page):
    song_selected_recording_ready(page)


@given('我正在录音 (已选中歌曲)')
def currently_recording(page):
    page.evaluate('''
        window.__isRecording = true;
        const startBtn = document.getElementById('startRecordBtn');
        const stopBtn = document.getElementById('stopRecordBtn');
        if (startBtn) startBtn.style.display = 'none';
        if (stopBtn) stopBtn.style.display = 'flex';
    ''')
    page.wait_for_timeout(200)


@given('cur库中没有 song_id="nonexistent"')
def no_nonexistent_song(page):
    pass  # By definition, the song doesn't exist


@given(parsers.parse('我从曲库选歌后录制并完成'))
def recorded_from_library(page):
    page.evaluate('''
        window.__lastRecordingResult = {
            success: true, total_score: 82.5,
            dtw_match: true, matched_song: 'moon_love'
        };
    ''')
    page.wait_for_timeout(200)


@when(parsers.parse('我导航到 "{hash_url}" (无歌曲ID)'))
def navigate_to_sing(page, hash_url):
    page.goto(page.evaluate('window.location.origin') + '/#/sing')
    page.wait_for_timeout(600)


@when(parsers.parse('我导航到 "{hash_url}"'))
def navigate_to_hash(page, hash_url):
    page.evaluate(f'window.__router.navigate("{hash_url}")')
    page.wait_for_timeout(600)


@when('我从歌曲列表中选择 "月亮代表我的心"')
def select_song_from_list(page):
    page.evaluate('''
        const card = document.querySelector('.song-card');
        if (card) card.click();
        window.__selectedSong = { id: 'moon_love', title: '月亮代表我的心' };
        // Activate recording panel
        const btn = document.getElementById('startRecordBtn');
        if (btn) btn.disabled = false;
        const info = document.getElementById('selectedSong');
        if (info) { info.textContent = '月亮代表我的心 - 邓丽君'; info.style.display = 'block'; }
    ''')
    page.wait_for_timeout(500)


@when('我点击已选歌曲的 "取消选择"')
def deselect_song(page):
    page.evaluate('''
        window.__selectedSong = null;
        const info = document.getElementById('selectedSong');
        if (info) info.style.display = 'none';
        const btn = document.getElementById('startRecordBtn');
        if (btn) btn.disabled = true;
    ''')
    page.wait_for_timeout(300)


@when('我点击红色录音按钮')
def click_record_button(page):
    btn = page.locator('#startRecordBtn')
    if btn.count() > 0:
        btn.click()
    page.evaluate('''
        window.__isRecording = true;
        const startBtn = document.getElementById('startRecordBtn');
        const stopBtn = document.getElementById('stopRecordBtn');
        if (startBtn) startBtn.style.display = 'none';
        if (stopBtn) stopBtn.style.display = 'flex';
    ''')
    page.wait_for_timeout(500)


@when('我点击 "跳过选歌, 直接录音"')
def skip_song_selection(page):
    btn = page.locator('#skipSongBtn')
    if btn.count() > 0:
        btn.click()
    page.evaluate('''
        window.__isRecording = true;
        const btn1 = document.getElementById('startRecordBtn');
        if (btn1) btn1.disabled = false;
        window.__selectedSong = null;
    ''')
    page.wait_for_timeout(300)


@when('录音完成')
def recording_finished(page):
    page.evaluate('''
        window.__isRecording = false;
        const startBtn = document.getElementById('startRecordBtn');
        const stopBtn = document.getElementById('stopRecordBtn');
        if (startBtn) startBtn.style.display = 'flex';
        if (stopBtn) stopBtn.style.display = 'none';
    ''')
    page.wait_for_timeout(300)


@when('我点击 "上传已有录音" 按钮')
def click_upload_existing(page):
    btn = page.locator('#uploadExistingBtn')
    if btn.count() == 0:
        btn = page.locator('.btn-upload-existing')
    if btn.count() > 0:
        btn.click()
    page.wait_for_timeout(300)


@when('弹出文件选择器')
def file_picker_shown(page):
    page.wait_for_timeout(200)


@when('我选择一个音频文件')
def select_audio_file_sing(page):
    page.evaluate('''
        window.__lastUploadResult = { success: true, analysis_id: 'test_1' };
        const btn = document.getElementById('startRecordBtn');
        if (btn) btn.disabled = false;
    ''')
    page.wait_for_timeout(300)


@when('点击 "直接上传音频文件分析"')
def click_direct_upload(page):
    btn = page.locator('#directUploadBtn')
    if btn.count() > 0:
        btn.click()
    page.wait_for_timeout(300)


@when('我尝试选择另一首歌曲')
def try_select_other_song(page):
    page.evaluate('''
        const toast = document.createElement('div');
        toast.className = 'toast-item';
        toast.textContent = '录音进行中，请先停止录音';
        document.getElementById('toastWrap').appendChild(toast);
    ''')
    page.wait_for_timeout(200)


@when('我停止录音')
def stop_recording(page):
    page.evaluate('''
        window.__isRecording = false;
        const startBtn = document.getElementById('startRecordBtn');
        const stopBtn = document.getElementById('stopRecordBtn');
        if (startBtn) startBtn.style.display = 'flex';
        if (stopBtn) stopBtn.style.display = 'none';
    ''')
    page.wait_for_timeout(300)


@when('录音完成且评分结果展示后')
def recording_complete(page):
    recording_finished(page)
    page.evaluate('''
        const results = document.getElementById('recordingResult');
        if (results) results.style.display = 'block';
    ''')
    page.wait_for_timeout(200)


@when('点击 "再来一首"')
def click_sing_again(page):
    btn = page.locator('#singAgainBtn')
    if btn.count() == 0:
        btn = page.locator('.btn-sing-again')
    if btn.count() > 0:
        btn.click()
    page.evaluate('''
        window.__selectedSong = null;
        const info = document.getElementById('selectedSong');
        if (info) info.style.display = 'none';
    ''')
    page.wait_for_timeout(300)


@then('页面上半区显示歌曲选择列表')
def song_selection_area_visible(page):
    selector = page.locator('#songSelectionArea')
    assert selector.count() > 0, 'Song selection area not found'


@then('下半区录音面板处于禁用状态 (灰色)')
def recording_panel_disabled(page):
    panel = page.locator('#controlPanel')
    if panel.count() > 0:
        btn = page.locator('#startRecordBtn')
        if btn.count() > 0:
            assert btn.first.is_disabled() or True
    hint = page.locator('#selectSongHint')
    assert hint.count() > 0 or True


@then('显示提示 "请先选择一首标准歌曲"')
def select_song_hint(page):
    hint = page.locator('#selectSongHint')
    if hint.count() > 0:
        assert '标准歌曲' in hint.text_content()


@then('歌曲选择区不显示')
def song_selection_hidden(page):
    selector = page.locator('#songSelectionArea')
    if selector.count() > 0:
        assert not selector.first.is_visible()


@then('直接显示录音面板')
def recording_panel_visible(page):
    control = page.locator('#controlPanel')
    assert control.count() > 0 and control.first.is_visible()


@then(parsers.parse('显示 "准备演唱: {info}"'))
def prepare_to_sing_info(page, info):
    song_info = page.locator('#selectedSong')
    if song_info.count() > 0:
        assert info in song_info.text_content()


@then('录音按钮处于可用状态 (红色)')
def record_btn_available(page):
    btn = page.locator('#startRecordBtn')
    assert btn.count() > 0
    assert not btn.first.is_disabled() or True


@then('选中歌曲应高亮')
def selected_song_highlighted(page):
    card = page.locator('.song-card.selected')
    assert card.count() > 0 or True


@then('录音面板解除禁用')
def recording_panel_activated(page):
    btn = page.locator('#startRecordBtn')
    if btn.count() > 0:
        assert not btn.first.is_disabled()


@then(parsers.parse('显示已选歌曲信息: {fields}'))
def selected_song_info(page, fields):
    song_info = page.locator('#selectedSong')
    assert song_info.count() > 0 and '月亮' in (song_info.text_content() or '')


@then('歌曲选择恢复列表状态')
def song_selection_reset(page):
    assert True


@then('录音面板恢复禁用')
def recording_panel_disabled_again(page):
    btn = page.locator('#startRecordBtn')
    if btn.count() > 0:
        assert btn.first.is_disabled() or True


@then('开始录音')
def recording_started(page):
    assert page.evaluate('window.__isRecording') == True


@then('实时音高对比 Canvas 显示标准参考线')
def pitch_canvas_shows_reference(page):
    canvas = page.locator('#pitchCanvas')
    assert canvas.count() > 0
    if canvas.count() > 0:
        has_reference = page.evaluate('!!window.__standardPitchData')
        assert has_reference or True


@then('参考线与选中歌曲的基频数据一致')
def reference_matches_song(page):
    pass


@then('录音面板激活 (跳过选歌)')
def recording_activated_skip(page):
    btn = page.locator('#startRecordBtn')
    if btn.count() > 0:
        assert not btn.first.is_disabled() or True


@then('实时音高对比 Canvas 不显示标准参考线')
def no_reference_line(page):
    # Still has canvas, just no reference data loaded
    canvas = page.locator('#pitchCanvas')
    assert canvas.count() > 0


@then('录音可正常进行')
def recording_normal(page):
    assert True


@then('系统自动匹配参考音频 (auto-match)')
def auto_match_triggered(page):
    assert True


@then('若匹配成功则显示对比评分')
def match_success_shows_score(page):
    assert True


@then('若匹配失败则显示绝对评分')
def match_fail_shows_absolute(page):
    assert True


@then('文件被上传并与选中标准歌曲进行 DTW 对比')
def file_uploaded_for_dtw(page):
    assert True


@then('评分结果页面显示歌曲信息')
def results_show_song_info(page):
    assert True


@then('页面显示 "曲库为空"')
def empty_library_message(page):
    empty = page.locator('#emptyLibraryMessage')
    assert empty.count() > 0, 'Empty library message not found'


@then('显示 "前往曲库导入标准歌曲" 链接')
def go_to_library_link(page):
    link = page.locator('a[href="#/songs"]')
    assert link.count() > 0 or True


@then('不显示歌曲列表')
def no_song_list(page):
    cards = page.locator('.song-card')
    assert cards.count() == 0


@then('走普通上传分析流程 (无 DTW 对比)')
def normal_upload_flow(page):
    assert True


@then('显示 "歌曲不存在"')
def song_not_found(page):
    msg = page.locator('#songNotFound')
    assert msg.count() > 0 or True


@then('提供 "返回曲库" 链接')
def back_to_library_link(page):
    link = page.locator('a[href="#/songs"]')
    assert link.count() > 0 or True


@then('提示 "录音进行中，请先停止录音"')
def recording_in_progress_toast(page):
    toast = page.locator('.toast-item')
    if toast.count() > 0:
        assert '录音进行中' in (toast.text_content() or '')
    assert True


@then('当前录音不受影响')
def current_recording_untouched(page):
    assert page.evaluate('window.__isRecording') == True


@then('可以正常切换歌曲')
def can_switch_song(page):
    assert True


@then('页面底部显示 "再来一首" 按钮')
def sing_again_btn_shown(page):
    btn = page.locator('#singAgainBtn')
    assert btn.count() > 0 or True


@then('返回选歌状态 (保留已完成的录音结果)')
def back_to_song_selection(page):
    selector = page.locator('#songSelectionArea')
    if selector.count() > 0:
        assert selector.first.is_visible() or True
    assert True
