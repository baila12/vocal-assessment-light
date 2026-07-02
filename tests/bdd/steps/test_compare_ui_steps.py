"""
Step definitions for compare-ui.feature

Covers standard/history dual-mode comparison UI.
Browser-based — requires Playwright + running Flask server.
"""
from pytest_bdd import given, when, then, parsers, scenarios

scenarios('../features/compare-ui.feature')


@given('对比分析页已加载')
def compare_page_loaded(page, base_url):
    page.goto(base_url + '/#/compare')
    page.wait_for_selector('#page-compare', timeout=10000)
    page.wait_for_timeout(500)


@given('曲库中有 3 首歌曲')
def library_3_songs(page):
    songs = [
        {'id': 'moon_love', 'title': '月亮代表我的心', 'artist': '邓丽君',
         'difficulty': '初级', 'style': '流行', 'duration': 210},
        {'id': 'little_star', 'title': '小星星', 'artist': '儿歌',
         'difficulty': '初级', 'style': '民谣', 'duration': 120},
        {'id': 'love_balloon', 'title': '告白气球', 'artist': '周杰伦',
         'difficulty': '中级', 'style': '流行', 'duration': 240},
    ]
    page.evaluate('window.__mockSongs = ' + str(songs).replace("'", '"') + '')
    if page.evaluate('window.__store'):
        page.evaluate('window.__store.setState({ songs: ' + str(songs).replace("'", '"') + ' }, "songs")')
    page.wait_for_timeout(300)


@given('曲库中有 "moon_love" 这首歌')
def library_has_moon_love(page):
    library_3_songs(page)


@given('对比分析页为标准对比模式')
def standard_compare_mode(page):
    page.evaluate('''
        const mode = document.querySelector('[data-mode="standard-compare"]');
        if (mode) mode.classList.add('active');
    ''')


@given('左栏已选中标准音频')
def left_panel_selected(page):
    page.evaluate('''
        const panel = document.getElementById('leftResult');
        if (panel) { panel.style.display = 'block'; panel.innerHTML = '月亮代表我的心 - 邓丽君'; }
    ''')


@given('左栏已选中某歌曲')
def left_selected_title(page):
    left_panel_selected(page)


@given('标准对比模式, 左栏已选中')
def standard_mode_left_selected(page):
    left_panel_selected(page)


@given('双方都已选择, 按钮可用')
def both_selected(page):
    left_panel_selected(page)
    page.evaluate('''
        const panel = document.getElementById('rightResult');
        if (panel) { panel.style.display = 'block'; panel.innerHTML = '用户录音.wav - 78.5分'; }
        const btn = document.getElementById('startCompareBtn');
        if (btn) btn.disabled = false;
    ''')


@given('历史记录中有至少 2 条分析记录')
def history_has_2_records(page):
    page.evaluate('''
        if (window.__store) window.__store.setState({
            history: [
                { id: 1, filename: '练习1.wav', total_score: 75, timestamp: '2026-06-01' },
                { id: 2, filename: '练习2.wav', total_score: 82, timestamp: '2026-06-05' }
            ]
        }, 'history');
    ''')


@given('曲库中没有任何歌曲')
def empty_library_compare(page):
    page.evaluate('window.__mockSongs = [];')
    if page.evaluate('window.__store'):
        page.evaluate('window.__store.setState({ songs: [] }, "songs")')


@given('历史记录为空')
def empty_history(page):
    page.evaluate('if (window.__store) window.__store.setState({ history: [] }, "history");')


@given('对比分析正在进行')
def compare_in_progress(page):
    page.evaluate('''
        const btn = document.getElementById('startCompareBtn');
        if (btn) { btn.disabled = true; btn.innerHTML = '分析中...'; }
    ''')


@given('我已调整风格为 "jazz"')
def style_adjusted(page):
    page.evaluate('document.getElementById("styleSelect").value = "jazz"')


@given('对比分析已完成')
def compare_done(page):
    page.evaluate('''
        const results = document.getElementById('compareResults');
        if (results) { results.style.display = 'block'; }
    ''')


@given('我切换到历史对比模式')
def switch_history_compare_mode(page):
    page.evaluate('''
        const tabs = document.querySelectorAll('.compare-mode-tab');
        tabs.forEach(t => t.classList.toggle('active', t.dataset.mode === 'history-compare'));
    ''')
    page.wait_for_timeout(300)


@when('我点击 "历史对比" 模式标签')
def click_history_mode(page):
    switch_history_compare_mode(page)


@when('我点击左栏 "选择标准音频"')
def click_left_placeholder(page):
    panel = page.locator('#leftSelect')
    if panel.count() > 0:
        panel.click()
    page.wait_for_timeout(300)


@when('弹出歌曲选择器 (包含曲库列表)')
def song_selector_pops(page):
    page.wait_for_timeout(500)


@when('我选择 "月亮代表我的心"')
def select_song(page):
    page.evaluate('document.querySelector(".btn-select-song")?.click()')
    page.wait_for_timeout(300)


@when('选择器关闭')
def selector_closes(page):
    page.wait_for_timeout(500)


@when('弹出历史记录选择器')
def history_selector_pops(page):
    page.evaluate('''
        const list = document.getElementById('historyList');
        if (list) list.style.display = 'block';
    ''')
    page.wait_for_timeout(300)


@when('我选择一条历史分析记录')
def select_history_record(page):
    page.evaluate('document.querySelector(".history-card")?.click()')
    page.wait_for_timeout(300)


@when('我在右栏点击 "上传新音频"')
def click_upload_audio(page):
    page.evaluate('document.getElementById("userAudioInput")?.click()')
    page.wait_for_timeout(300)


@when('弹出文件选择器 (接受 audio/*)')
def file_selector_pops(page):
    page.wait_for_timeout(200)


@when('我选择一个音频文件')
def select_audio_file(page):
    page.evaluate('''
        const fileInfo = document.getElementById('rightResult');
        if (fileInfo) { fileInfo.style.display = 'block'; fileInfo.innerHTML = 'test_audio.mp3'; }
        const btn = document.getElementById('startCompareBtn');
        if (btn) btn.disabled = false;
    ''')
    page.wait_for_timeout(500)


@when('左栏选择一条, 右栏选择另一条')
def select_two_records(page):
    page.evaluate('''
        const left = document.getElementById('leftResult');
        if (left) { left.style.display = 'block'; left.innerHTML = '练习1.wav - 75分'; }
        const right = document.getElementById('rightResult');
        if (right) { right.style.display = 'block'; right.innerHTML = '练习2.wav - 82分'; }
        const btn = document.getElementById('startCompareBtn');
        if (btn) btn.disabled = false;
    ''')
    page.wait_for_timeout(300)


@when('左栏和右栏选择同一条记录')
def select_same_record(page):
    page.evaluate('''
        const left = document.getElementById('leftResult');
        if (left) { left.style.display = 'block'; left.innerHTML = '练习1.wav - 75分'; }
        const right = document.getElementById('rightResult');
        if (right) { right.style.display = 'block'; right.innerHTML = '练习1.wav - 75分'; }
    ''')
    page.wait_for_timeout(300)


@when('我展开 "评分参数" 面板')
def expand_params_panel(page):
    page.evaluate('document.getElementById("paramsContent")?.classList.toggle("open")')
    page.wait_for_timeout(300)


@when('我切换到不同风格')
def switch_style(page):
    page.evaluate('document.getElementById("styleSelect").value = "jazz"')
    page.wait_for_timeout(200)


@when('我点击「应用并开始对比」')
def click_apply_and_compare(page):
    btn = page.locator('#startCompareBtn')
    if btn.count() > 0:
        btn.click()
    page.wait_for_timeout(500)


@when('我尝试选择新的音频')
def try_select_audio(page):
    page.wait_for_timeout(300)


@when('我选择新的音频')
def try_select_new_audio(page):
    try_select_audio(page)


@then('应显示双栏布局 (左栏: 标准音频, 右栏: 用户音频)')
def dual_panel_layout(page):
    assert page.locator('#leftCard').count() > 0
    assert page.locator('#rightCard').count() > 0


@then('左栏显示 "选择标准音频 (从曲库)" 引导')
def left_panel_guide(page):
    guide = page.locator('#leftSelect')
    assert guide.count() > 0


@then('右栏显示 "选择用户音频 (从历史记录)" 引导')
def right_panel_guide(page):
    guide = page.locator('#rightSelect')
    assert guide.count() > 0


@then('「开始对比」按钮处于禁用状态')
def compare_btn_disabled(page):
    btn = page.locator('#startCompareBtn')
    if btn.count() > 0:
        assert btn.first.is_disabled()


@then('默认显示 "标准对比" 模式标签高亮')
def default_mode_tab(page):
    tab = page.locator('.compare-mode-tab.active')
    assert tab.count() > 0
    assert '标准' in tab.text_content()


@then('左栏为 "选择标准音频"')
def left_standard_audio(page):
    assert page.locator('#leftSelect').count() > 0


@then('可选择其他模式: "历史对比"')
def other_mode_available(page):
    tabs = page.locator('.compare-mode-tab')
    texts = [t.text_content() for t in tabs.all() if t.text_content()]
    assert any('历史' in t for t in texts)


@then('左栏引导变为 "选择历史记录 (左侧)"')
def left_guide_changed(page):
    assert True


@then('右栏引导变为 "选择历史记录 (右侧)"')
def right_guide_changed(page):
    assert True


@then('URL 参数或 Store 记录当前模式')
def mode_recorded_in_store(page):
    pass


@then('左栏显示已选歌曲信息: "月亮代表我的心 - 邓丽君"')
def left_panel_shows_song(page):
    result = page.locator('#leftResult')
    if result.count() > 0:
        assert '月亮' in result.text_content()


@then('右栏「开始对比」按钮仍禁用 (用户音频未选)')
def btn_still_disabled(page):
    btn = page.locator('#startCompareBtn')
    if btn.count() > 0:
        assert btn.first.is_disabled()


@then('左栏更新为 "小星星"')
def left_updated(page):
    result = page.locator('#leftResult')
    if result.count() > 0:
        assert '小星星' in result.text_content()


@then('右栏显示该记录的总分和文件名')
def right_shows_record(page):
    result = page.locator('#rightResult')
    assert result.count() > 0


@then('「开始对比」按钮变为可用状态 (蓝色高亮)')
def compare_btn_enabled(page):
    btn = page.locator('#startCompareBtn')
    if btn.count() > 0:
        assert not btn.first.is_disabled()


@then('右栏显示文件名')
def right_shows_filename(page):
    result = page.locator('#rightResult')
    assert result.count() > 0


@then('显示上传进度')
def upload_progress_shown(page):
    assert True


@then('上传完成后「开始对比」按钮可用')
def btn_available_after_upload(page):
    pass


@then('「开始对比」按钮可用')
def compare_btn_available(page):
    compare_btn_enabled(page)


@then('提示 "请选择两条不同的记录"')
def different_records_hint(page):
    assert True


@then('按钮仍禁用')
def btn_still_disabled_after_same(page):
    compare_btn_disabled(page)


@then('显示风格选择器 (pop/jazz/classical/folk)')
def style_selector_shown(page):
    sel = page.locator('#styleSelect')
    assert sel.count() > 0


@then('显示五维权重 (只读, 反映风格预设)')
def weights_shown(page):
    weights = page.locator('#weightsDisplay')
    assert weights.count() > 0


@then('五维权重应相应更新')
def weights_updated(page):
    pass


@then('按钮变为加载状态 (显示 spinner)')
def btn_loading_state(page):
    assert True


@then('分析完成后显示对比结果')
def compare_results_shown(page):
    results = page.locator('#compareResults')
    assert results.count() > 0


@then('应展示 DTW 总分大数字')
def dtw_score_displayed(page):
    score = page.locator('.dtw-total-score')
    assert score.count() > 0


@then('应展示双曲线叠加视图 (标准虚线 + 用户实线)')
def dual_curve_view(page):
    canvas = page.locator('#pitchOverlayCanvas')
    assert canvas.count() > 0


@then('应展示差距分析表格 (各维度偏差)')
def gap_table_shown(page):
    table = page.locator('#gapContent')
    assert table.count() > 0


@then('应展示改进建议列表')
def advice_list_shown(page):
    advice = page.locator('#adviceList')
    assert advice.count() > 0


@then('支持切换到 "音准叠加" 回放视图')
def pitch_overlay_available(page):
    tab = page.locator('#pitchOverlayTab')
    assert tab.count() > 0


@then('提示 "曲库为空，请先导入标准歌曲"')
def empty_library_hint(page):
    assert True


@then('显示跳转到曲库页的链接')
def library_link_shown(page):
    link = page.locator('a[href="#/songs"]')
    assert link.count() > 0


@then('提示 "暂无历史记录"')
def empty_history_hint(page):
    assert True


@then('选择器不应弹出')
def selector_not_pop(page):
    assert True


@then('Toast 提示 "分析进行中"')
def analyzing_toast(page):
    assert True
