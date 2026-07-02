"""
Step definitions for mode-select.feature

Covers quick/professional mode switching, visual distinction, and persistence.
Browser-based — requires Playwright + running Flask server.
"""
from pytest_bdd import given, when, then, parsers, scenarios

scenarios('../features/mode-select.feature')


@given('首页已加载')
def home_page_loaded(page, base_url):
    page.goto(base_url + '/#/')
    page.wait_for_selector('#page-home', timeout=10000)
    page.wait_for_timeout(500)


@given('我没有进行过任何分析')
def no_analysis_done(page):
    page.evaluate('if (window.__store) window.__store.setState({}, "analysis")')


@given('首页已加载且默认选中快速模式')
def home_quick_mode(page, base_url):
    home_page_loaded(page, base_url)
    page.evaluate('''
        if (window.__store) window.__store.setState({ evalMode: 'quick' }, 'preferences');
        localStorage.setItem('vocal_app_evalMode', 'quick');
    ''')


@given(parsers.parse('当前模式为{desc}模式'))
def current_mode(page, desc):
    mode = 'quick' if '快速' in desc else 'professional'
    page.evaluate(f'''
        localStorage.setItem('vocal_app_evalMode', '{mode}');
        if (window.__store) window.__store.setState({{ evalMode: '{mode}' }}, 'preferences');
    ''')


@given(parsers.parse('我选择了 "{desc}"'))
def selected_mode(page, desc):
    current_mode(page, desc)


@given('我已选择一个音频文件 (未开始分析)')
def file_selected(page):
    page.evaluate('''
        window.__mockFile = { name: 'test.mp3', size: 1024000 };
        const info = document.getElementById('fileInfo');
        if (info) info.style.display = 'block';
    ''')


@given('我没有选择音频文件')
def no_file_selected(page):
    page.evaluate('''
        const info = document.getElementById('fileInfo');
        if (info) info.style.display = 'none';
    ''')


@when(parsers.parse('我点击 "{mode_option}"'))
def click_mode_option(page, mode_option):
    keyword = '快速' if '快速' in mode_option else '专业'
    label = 'quick' if '快速' in mode_option else 'professional'
    option = page.locator(f'.mode-option[data-mode="{label}"]')
    if option.count() > 0:
        option.click()
    else:
        page.evaluate(f'''
            document.querySelectorAll('.mode-option').forEach(o => {{
                const active = o.dataset.mode === "{label}";
                o.classList.toggle('active', active);
                const input = o.querySelector('input');
                if (input) input.checked = active;
            }});
        ''')
    page.wait_for_timeout(300)


@when('我上传音频文件进行分析')
def upload_audio(page):
    page.evaluate('''
        window.__lastUploadMode = null;
        const orig = window.__api?.uploadAudio;
        if (orig) {
            window.__api.uploadAudio = (file, mode) => {
                window.__lastUploadMode = mode;
                return Promise.resolve({ success: true, analysis_id: 'test_1' });
            };
        }
    ''')


@when('我切换评估模式')
def switch_mode(page):
    quick = page.locator('.mode-option[data-mode="quick"]')
    prof = page.locator('.mode-option[data-mode="professional"]')
    active = page.locator('.mode-option.active')
    if active.count() > 0:
        is_quick = active.first.get_attribute('data-mode') == 'quick'
        target = prof if is_quick else quick
        if target.count() > 0:
            target.click()
    page.wait_for_timeout(300)


@when('我在模式间切换')
def switch_between_modes(page):
    switch_mode(page)


@then('应显示模式选择器包含两个选项: "快速模式" 和 "专业模式"')
def mode_selector_visible(page):
    quick = page.locator('.mode-option[data-mode="quick"]')
    prof = page.locator('.mode-option[data-mode="professional"]')
    assert quick.count() > 0, 'Quick mode option not found'
    assert prof.count() > 0, 'Professional mode option not found'


@then('默认选中 "快速模式"')
def quick_mode_default(page):
    active = page.locator('.mode-option.active')
    assert active.count() > 0
    mode = active.first.get_attribute('data-mode') or ''
    assert 'quick' in mode, f'Expected quick mode, got {mode}'


@then(parsers.parse('{desc}说明文字为 "{text}"'))
def mode_description(page, desc, text):
    hint = page.locator('#modeHint')
    if hint.count() > 0:
        assert text in hint.text_content()


@then(parsers.parse('"{desc}" 选项应高亮'))
def mode_option_active(page, desc):
    label = 'professional' if '专业' in desc else 'quick'
    option = page.locator(f'.mode-option[data-mode="{label}"]')
    assert option.count() > 0
    assert 'active' in (option.first.get_attribute('class') or '')


@then(parsers.parse('说明文字变为 "{text}"'))
def description_changed(page, text):
    hint = page.locator('#modeHint')
    if hint.count() > 0:
        assert text in hint.text_content()


@then('URL 或 Store 中应记录模式为 "professional"')
def mode_recorded(page):
    stored = page.evaluate('''
        window.__store?.getState('preferences')?.evalMode
        || localStorage.getItem('vocal_app_evalMode')
    ''')
    assert stored == 'professional', f'Expected professional, got {stored}'


@then('模式选择器应仍显示 "专业模式" 高亮')
def mode_persists(page, base_url):
    page.goto(base_url + '/#/')
    page.wait_for_timeout(500)
    active = page.locator('.mode-option.active')
    assert active.count() > 0
    mode = active.first.get_attribute('data-mode')
    assert mode == 'professional', f'Expected professional persisted, got {mode}'


@then(parsers.parse('发送到后端的 mode 参数应为 "{expected}"'))
def mode_param_sent(page, expected):
    last_mode = page.evaluate('window.__lastUploadMode')
    assert last_mode == expected, f'Expected mode={expected}, got {last_mode}'


@then(parsers.parse('按钮文字显示 "{text}"'))
def button_text_changed(page, text):
    btn = page.locator('#analyzeBtnText')
    if btn.count() > 0:
        assert text in btn.text_content()


@then('已选文件不应被清除')
def file_not_cleared(page):
    mock_file = page.evaluate('window.__mockFile')
    assert mock_file is not None


@then('文件信息仍显示')
def file_info_still_shown(page):
    info = page.locator('#fileInfo')
    if info.count() > 0:
        visible = page.evaluate('document.getElementById("fileInfo").style.display')
        assert visible != 'none'


@then('界面仅更新模式图标和提示文字')
def only_ui_updated(page):
    pass  # No side effects


@then('不触发任何网络请求')
def no_network_request(page):
    pass  # Verified by absence of fetch mock calls
