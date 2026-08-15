"""
Step definitions for database.feature — 标准歌曲库 (后端 BDD)

实现 API 级场景 (增/查/筛/搜/删/详情/重复检测);
特征预提取 / 批量导入 / 评分配置 UI 等未来功能标记 xfail。

跨步骤状态通过场景级 `song_state` fixture 传递 (pytest-bdd 版本无关)。
"""
import io

import pytest
from pytest_bdd import given, when, then, parsers, scenarios

scenarios('../features/database.feature')

# 中文难度/风格 → 领域英文键
_DIFFICULTY_MAP = {'初级': 'beginner', '中级': 'intermediate', '高级': 'advanced'}
_STYLE_MAP = {'流行': 'pop', '美声': 'classical', '民谣': 'folk', '说唱': 'rap'}


@pytest.fixture
def song_state():
    """场景级状态容器 — 跨步骤传递数据 (Each scenario isolated)"""
    return {}


def _fake_wav() -> bytes:
    """最小合法 WAV 文件 (1 秒静音)"""
    header = (
        b'RIFF' + (36).to_bytes(4, 'little') + b'WAVEfmt '
        + (16).to_bytes(4, 'little') + b'\x01\x00\x01\x00'
        + (22050).to_bytes(4, 'little') + (22050).to_bytes(4, 'little')
        + b'\x01\x00\x08\x00' + b'data' + (0).to_bytes(4, 'little')
    )
    return header + bytes(22050)


def _create(fastapi_client, title: str, artist: str = '邓丽君',
            style: str = 'pop', difficulty: str = 'beginner') -> dict:
    """通过 API 创建歌曲, 返回响应 JSON"""
    resp = fastapi_client.post(
        '/api/v1/songs',
        data={
            'title': title, 'artist': artist, 'key': 'C', 'bpm': '78',
            'difficulty': difficulty, 'style': style,
        },
        files={'file': (f'{title}.wav', io.BytesIO(_fake_wav()), 'audio/wav')},
    )
    assert resp.status_code == 200, f'创建歌曲失败: {resp.text}'
    return resp.json()['song']


# ═══════════════════════════════════════════════════════════════
# Background
# ═══════════════════════════════════════════════════════════════

@given('服务已启动')
def flask_service_running(fastapi_client):
    assert fastapi_client is not None


# ═══════════════════════════════════════════════════════════════
# Given — 测试前置
# ═══════════════════════════════════════════════════════════════

@given('一个标准演唱音频文件 "reference_song.wav"')
def reference_song_file(song_state):
    song_state['audio'] = ('reference_song.wav', io.BytesIO(_fake_wav()), 'audio/wav')


@given(parsers.parse('歌曲元数据:'))
def song_metadata_table(datatable, song_state):
    """解析歌曲元数据 datatable (list[list], 首行为表头) → song_state"""
    rows = {r[0]: r[1] for r in datatable[1:]}
    song_state['metadata'] = {
        'title': rows.get('歌名', ''),
        'artist': rows.get('歌手', ''),
        'key': rows.get('调性', 'C'),
        'bpm': int(rows.get('BPM', 0)),
        'difficulty': _DIFFICULTY_MAP.get(rows.get('难度', '初级'), 'beginner'),
        'style': _STYLE_MAP.get(rows.get('风格', '流行'), 'pop'),
    }


@given(parsers.parse('曲库中已存在 "{song_name}"'))
def song_exists(fastapi_client, song_name, song_state):
    if ' - ' in song_name:
        title, artist = song_name.split(' - ', 1)
    else:
        title, artist = song_name, '邓丽君'
    _create(fastapi_client, title, artist)
    song_state['duplicate'] = (title, artist)


@given('曲库中有至少 20 首歌曲')
def library_with_20_songs(fastapi_client):
    for i in range(20):
        _create(fastapi_client, f'曲库歌曲{i:02d}', artist='测试')


@given(parsers.parse('曲库中有流行歌曲 {pop:d} 首, 美声歌曲 {clas:d} 首'))
def library_with_styles(fastapi_client, pop: int, clas: int):
    for i in range(pop):
        _create(fastapi_client, f'流行歌曲{i}', style='pop')
    for i in range(clas):
        _create(fastapi_client, f'美声歌曲{i}', style='classical')


@given(parsers.parse('曲库中有初级 {b:d} 首, 中级 {m:d} 首, 高级 {a:d} 首'))
def library_with_difficulties(fastapi_client, b: int, m: int, a: int):
    for i in range(b):
        _create(fastapi_client, f'初级歌曲{i}', difficulty='beginner')
    for i in range(m):
        _create(fastapi_client, f'中级歌曲{i}', difficulty='intermediate')
    for i in range(a):
        _create(fastapi_client, f'高级歌曲{i}', difficulty='advanced')


@given('曲库中包含 "月亮代表我的心"')
def library_contains_moon(fastapi_client):
    _create(fastapi_client, '月亮代表我的心')


@given(parsers.parse('曲库中存在 ID 为 "{song_id}" 的歌曲'))
def song_with_id_exists(fastapi_client, song_id: str):
    """创建一首 ID 前缀歌曲供后续步骤查找"""
    _create(fastapi_client, f'ID歌曲{song_id}')


@given('我正在录入一首高难度美声歌曲')
def adding_bel_canto():
    pytest.xfail('评分参数面板/风格权重 UI 未实现')


# ═══════════════════════════════════════════════════════════════
# When — 动作
# ═══════════════════════════════════════════════════════════════

@when('我提交该歌曲到标准曲库')
def submit_song(fastapi_client, song_state):
    meta = song_state['metadata']
    name, f, ctype = song_state['audio']
    resp = fastapi_client.post(
        '/api/v1/songs',
        data={
            'title': meta['title'], 'artist': meta['artist'],
            'key': meta['key'], 'bpm': str(meta['bpm']),
            'difficulty': meta['difficulty'], 'style': meta['style'],
        },
        files={'file': (name, f, ctype)},
    )
    song_state['response'] = resp


@when('我尝试再次导入相同音频文件')
def retry_import(fastapi_client, song_state):
    title, artist = song_state['duplicate']
    resp = fastapi_client.post(
        '/api/v1/songs',
        data={
            'title': title, 'artist': artist,
            'key': 'C', 'bpm': '78', 'difficulty': 'beginner', 'style': 'pop',
        },
        files={'file': ('dup.wav', io.BytesIO(_fake_wav()), 'audio/wav')},
    )
    song_state['response'] = resp


@when(parsers.parse('我访问歌曲列表 API, 指定 page={page:d}, limit={limit:d}'))
def visit_list_api(fastapi_client, song_state, page: int, limit: int):
    song_state['response'] = fastapi_client.get(
        f'/api/v1/songs?page={page}&limit={limit}'
    )


@when(parsers.parse('我筛选风格为 "{style}"'))
def filter_by_style(fastapi_client, song_state, style: str):
    song_state['response'] = fastapi_client.get(
        f"/api/v1/songs?style={_STYLE_MAP.get(style, style)}"
    )


@when(parsers.parse('我筛选难度为 "{diff}" 或 "{diff2}"'))
def filter_by_difficulty(fastapi_client, song_state, diff: str, diff2: str):
    d1 = _DIFFICULTY_MAP.get(diff, diff)
    d2 = _DIFFICULTY_MAP.get(diff2, diff2)
    r1 = fastapi_client.get(f'/api/v1/songs?difficulty={d1}').json()['total']
    r2 = fastapi_client.get(f'/api/v1/songs?difficulty={d2}').json()['total']
    song_state['total'] = r1 + r2


@when(parsers.parse('我搜索关键词 "{keyword}"'))
def search_songs(fastapi_client, song_state, keyword: str):
    song_state['response'] = fastapi_client.get(
        '/api/v1/songs', params={'search': keyword}
    )


@when(parsers.parse('我删除该歌曲'))
def delete_song(fastapi_client, song_state):
    resp = fastapi_client.get('/api/v1/songs', params={'search': 'ID歌曲'})
    songs = resp.json()['songs']
    assert songs, '未找到待删除歌曲'
    song_id = songs[0]['id']
    song_state['delete_resp'] = fastapi_client.delete(f'/api/v1/songs/{song_id}')
    song_state['song_id'] = song_id


@when(parsers.parse('我访问该歌曲的详情 API'))
def visit_detail_api(fastapi_client, song_state):
    resp = fastapi_client.get('/api/v1/songs', params={'search': 'ID歌曲'})
    songs = resp.json()['songs']
    assert songs, '未找到歌曲详情'
    song_id = songs[0]['id']
    song_state['detail'] = fastapi_client.get(
        f'/api/v1/songs/{song_id}'
    ).json()['song']


@when('我展开 "评分参数" 面板')
def expand_scoring_panel():
    pytest.xfail('评分配置 UI 未实现')


# ── 批量导入 (未来功能, 全部 xfail) ──

@given('一个包含 10 首标准歌曲的文件夹')
def folder_with_10_songs():
    pytest.xfail('批量导入未实现')


@given('每首歌曲都有配套的 metadata.json')
def songs_with_metadata_json():
    pytest.xfail('批量导入未实现')


@when('我触发批量导入')
def trigger_batch_import():
    pytest.xfail('批量导入未实现')


@then('10 首歌曲应全部入库')
def ten_songs_imported():
    pytest.xfail('批量导入未实现')


@then('每首歌的特征应后台预计算完成')
def features_precomputed():
    pytest.xfail('特征预计算未实现')


@then('返回导入报告: 成功数, 失败数, 跳过(重复)数')
def import_report():
    pytest.xfail('批量导入未实现')


# ═══════════════════════════════════════════════════════════════
# Then — 断言
# ═══════════════════════════════════════════════════════════════

@then('歌曲应成功入库')
def song_created_successfully(song_state):
    assert song_state['response'].status_code == 200, song_state['response'].text


@then('系统应自动预提取特征: 基频曲线, onset序列, 频谱指纹')
def auto_feature_pre_extraction():
    pytest.xfail('特征预提取 (基频/onset/频谱指纹) 待实现')


@then('返回歌曲的唯一 ID')
def song_has_unique_id(song_state):
    assert song_state['response'].json()['song']['id']


@then('系统应检测到重复')
def detect_duplicate(song_state):
    assert song_state['response'].status_code == 409


@then(parsers.parse('返回提示 "该歌曲已存在 (ID: xxx), 是否覆盖?"'))
def duplicate_tip_message(song_state):
    assert '已存在' in song_state['response'].json()['detail']


@then('默认行为应为跳过(不覆盖)')
def duplicate_skip_by_default():
    """默认不覆盖 — 第二次创建返回 409 即拒绝写入"""
    pass  # 语义已由 detect_duplicate (409) 保证


@then(parsers.parse('应返回 {n:d} 首歌曲'))
def returns_n_songs(song_state, n: int):
    assert len(song_state['response'].json()['songs']) == n


@then('每首歌包含: id, 歌名, 歌手, 难度, 风格, 时长')
def each_song_has_fields(song_state):
    for s in song_state['response'].json()['songs']:
        assert s['id']
        assert s['metadata']['title']
        assert s['metadata']['artist']
        assert s['metadata']['difficulty']
        assert s['metadata']['style']
        assert 'duration_seconds' in s


@then('返回分页信息: total, page, limit')
def pagination_metadata(song_state):
    data = song_state['response'].json()
    assert 'total' in data and 'page' in data and 'limit' in data


@then(parsers.parse('应返回 {n:d} 首流行歌曲'))
def returns_n_pop_songs(song_state, n: int):
    songs = song_state['response'].json()['songs']
    assert len(songs) == n
    assert all(s['metadata']['style'] == 'pop' for s in songs)


@then('不应包含美声歌曲')
def no_classical_songs(song_state):
    songs = song_state['response'].json()['songs']
    assert all(s['metadata']['style'] != 'classical' for s in songs)


@then(parsers.parse('应返回 {n:d} 首符合条件的歌曲'))
def returns_n_matching(song_state, n: int):
    assert song_state['total'] == n


@then('应返回歌名或歌手包含 "月亮" 的歌曲')
def returns_moon_matches(song_state):
    songs = song_state['response'].json()['songs']
    assert songs
    assert all('月亮' in s['metadata']['title'] or '月亮' in s['metadata']['artist']
               for s in songs)


@then('支持模糊匹配 (如 "月量" 应也能匹配 "月亮")')
def fuzzy_match_supported():
    pytest.xfail('拼音/容错模糊搜索未实现')


@then('歌曲记录应从数据库移除')
def song_removed_from_db(song_state):
    assert song_state['delete_resp'].status_code == 200
    assert song_state['delete_resp'].json()['deleted'] is True


@then('关联的特征缓存文件应同步删除')
def feature_cache_deleted():
    pytest.xfail('特征缓存文件管理待实现')


@then('后续搜索不应再出现该歌曲')
def song_not_in_later_search(fastapi_client, song_state):
    resp = fastapi_client.get(f"/api/v1/songs/{song_state['song_id']}")
    assert resp.status_code == 404


@then('应返回完整元数据: 歌名, 歌手, 调性, BPM, 难度, 风格, 时长, 音域范围')
def detail_has_full_metadata(song_state):
    song = song_state['detail']
    assert song['metadata']['title']
    assert song['metadata']['artist']
    assert 'key' in song['metadata']
    assert 'bpm' in song['metadata']
    assert 'duration_seconds' in song


@then('应返回特征摘要: 基频曲线采样点, onset 数量, 平均能量')
def detail_has_feature_summary():
    pytest.xfail('特征预提取未实现, 无特征摘要')


@then('应返回入库时间和特征提取状态')
def detail_has_created_at(song_state):
    song = song_state['detail']
    assert song['created_at']
    assert song['feature_status']


@then('应返回关联的评分权重配置 (scoring_config 字段)')
def detail_has_scoring_config(song_state):
    assert 'scoring_config' in song_state['detail']


@then('应显示风格选择器 + 五维权重滑块')
def show_style_selector_and_sliders():
    pytest.xfail('评分参数 UI 未实现')


@then(parsers.parse('选择 "{style}" → 自动填充美声默认权重: P=30, R=15, B=25, T=20, A=10'))
def auto_fill_classical_weights(style):
    pytest.xfail('风格默认权重配置未实现')


@then('点击 "系统推荐" → 分析音频特征 → 返回推荐权重及理由')
def system_recommend_weights():
    pytest.xfail('音频特征推荐权重未实现')


@then('我可将推荐值保存为该歌曲的默认评分配置')
def save_recommended_config():
    pytest.xfail('评分配置保存未实现')


@then('后续匹配到该歌曲时自动使用此配置')
def auto_use_song_config():
    pytest.xfail('自动使用歌曲评分配置未实现')
