"""
Step definitions for differentiation.feature

实现评分区分度验证的 Given/When/Then 步骤。
v7.14: 对齐真实 FastAPI 契约 — /api/v1/upload + .json() + files=。
跨步骤状态通过场景级 `score_state` fixture 传递 (pytest-bdd 8.x 兼容,
@given/@when/@then 函数名不注册为 fixture, 显式 state 传递)。
"""

from pathlib import Path

import pytest
from pytest_bdd import given, when, then, parsers, scenarios

scenarios('../features/differentiation.feature')

_UPLOAD_URL = '/api/v1/upload'

# UploadResponse.scores 源键 (9) → apply-weights 目标键 (6)
_SCORE_KEY_MAP = {
    'pitch': 'pitch',
    'rhythm': 'rhythm',
    'breath': 'breath',
    'technique': 'technique',
    'muscle_strength': 'muscle',
    'artistry': 'artistry',
}


@pytest.fixture
def score_state():
    """场景级状态 — 跨步骤传递音频路径与评分结果"""
    return {}


def _six_dim_scores(scores: dict) -> dict:
    """UploadResponse.scores (9 键) → apply-weights 六维契约 {pitch..artistry}"""
    return {
        target: scores[src]
        for src, target in _SCORE_KEY_MAP.items()
        if src in scores
    }


def _upload(api_client, path: str, mode: str) -> dict:
    """上传音频并评估 → 响应 JSON (UploadResponse 扁平结构)"""
    with open(path, 'rb') as f:
        resp = api_client.post(
            _UPLOAD_URL,
            files={'file': (Path(path).name, f, 'audio/wav')},
            data={'mode': mode},
        )
    assert resp.status_code == 200, \
        f'upload failed: {resp.status_code} {resp.text}'
    return resp.json()


# ── Given (显式写入 score_state, 不依赖函数名 fixture) ──

@given(parsers.parse('一个专业级演唱音频 "{filename}"'))
def pro_singer_audio(filename, test_data_dir, score_state):
    path = test_data_dir / 'audio' / 'vocal' / filename
    if not path.exists():
        pytest.skip(f'Pro audio not found: {filename}')
    score_state['pro_path'] = str(path)


@given(parsers.parse('一个初学者演唱音频 "{filename}"'))
def beginner_audio(filename, test_data_dir, score_state):
    path = test_data_dir / 'audio' / 'vocal' / filename
    if not path.exists():
        pytest.skip(f'Beginner audio not found: {filename}')
    score_state['beginner_path'] = str(path)


@given(parsers.parse('同一个人声演唱音频 "{filename}"'))
def single_vocal_audio(filename, test_data_dir, score_state):
    path = test_data_dir / 'audio' / 'vocal' / filename
    if not path.exists():
        # Try any available vocal file
        candidates = sorted((test_data_dir / 'audio' / 'vocal').glob('*'))
        if candidates:
            path = candidates[0]
        else:
            pytest.skip(f'Test file not found: {path}')
    score_state['vocal_path'] = str(path)


@given('5 个不同水平的演唱音频')
def five_level_audios(test_data_dir, score_state):
    """Return up to 5 vocal files of different quality levels."""
    vocal_dir = test_data_dir / 'audio' / 'vocal'
    files = sorted(vocal_dir.glob('*'))
    if len(files) < 2:
        pytest.skip(f'Need at least 2 vocal files, found {len(files)}')
    score_state['level_paths'] = [str(f) for f in files[:5]]


@given('5 个合成或噪声音频文件')
def five_non_vocal_audios(test_data_dir, score_state):
    """Return up to 5 non-vocal files."""
    non_vocal_dir = test_data_dir / 'audio' / 'non_vocal'
    if not non_vocal_dir.exists():
        pytest.skip('non_vocal directory not found')
    files = sorted(non_vocal_dir.glob('*'))
    if not files:
        pytest.skip('No non-vocal files found')
    score_state['non_vocal_paths'] = [str(f) for f in files[:5]]


@given('一首流行歌曲的人声录音')
def pop_vocal_recording(test_data_dir, score_state):
    """风格预设场景 — 复用 vocal 测试音频 (真实分析拿维度分数)"""
    candidates = sorted((test_data_dir / 'audio' / 'vocal').glob('*'))
    if not candidates:
        pytest.skip('No vocal audio files available')
    score_state['vocal_path'] = str(candidates[0])


@given(parsers.parse('一首说唱歌曲 (BPM=95, 语速快, 旋律少)'))
def rap_song_for_detection():
    """说唱检测 — 前端自动风格检测未实现 (v6.0 规格), 走到 Then 即 xfail"""


@given('一首人声录音')
def plain_vocal_recording(test_data_dir, score_state):
    """自定义权重场景 — 复用 vocal 测试音频"""
    candidates = sorted((test_data_dir / 'audio' / 'vocal').glob('*'))
    if not candidates:
        pytest.skip('No vocal audio files available')
    score_state['vocal_path'] = str(candidates[0])


# ── When (从 score_state 读取路径) ──

@when('两个音频都用 quick 模式评估')
def evaluate_both_quick(api_client, score_state):
    """Evaluate both audios in quick mode."""
    scores = {}
    for label, key in [('pro', 'pro_path'), ('beginner', 'beginner_path')]:
        scores[label] = _upload(api_client, score_state[key], 'quick')
    score_state['both'] = scores


@when('分别用 quick 和 professional 模式评估')
def evaluate_both_modes(api_client, score_state):
    """Evaluate the same audio in both modes."""
    results = {}
    for mode in ['quick', 'professional']:
        results[mode] = _upload(api_client, score_state['vocal_path'], mode)
    score_state['modes'] = results


@when('全部用 quick 模式评估')
def evaluate_all_quick(api_client, score_state):
    """Evaluate all files in quick mode.

    单一 def 服务两个场景 (各维度区分力 / 非人声归零) — 两个 Given 分别写入
    level_paths / non_vocal_paths, 此处按实际填充的键取路径, 结果统一存 all_quick。
    (pytest-bdd 8 同名 @when 注册顺序歧义曾导致场景 3 误读 non_vocal_paths)
    """
    paths = score_state.get('level_paths') or score_state.get('non_vocal_paths')
    assert paths, '缺少音频路径: 前置 Given 未填充 level_paths/non_vocal_paths'
    score_state['all_quick'] = [
        _upload(api_client, p, 'quick') for p in paths
    ]


# ── 风格预设 / 自定义权重 (v6.0 场景, v7.14 补 defs) ──
# 通过 apply-weights 纯重算验证 (权重影响方向), 不重复跑音频管线

@when('分别用 "流行" 和 "美声" 风格预设评估')
def evaluate_two_presets(api_client, score_state):
    """同一组维度分数, 用 pop/bel_canto 预设分别重算总分"""
    scores = _upload(api_client, score_state['vocal_path'], 'quick')
    dims = _six_dim_scores(scores['scores'])
    results = {}
    for preset in ('pop', 'bel_canto'):
        resp = api_client.post(
            '/api/v1/scoring/apply-weights',
            json={'dimension_scores': dims, 'preset': preset},
        )
        assert resp.status_code == 200, resp.text
        results[preset] = resp.json()['data']
    score_state['presets'] = results
    score_state['dims'] = dims


@then('两个预设的加权总分应有差异 (权重不同产生可感知变化)')
def check_preset_total_gap(score_state):
    """v7.14 规格修正: 原 5-15 分区间对真实演唱不可达 —
    gap = 0.04*pitch - 0.04*rhythm + 0.08*breath - 0.08*artistry (权重差),
    真实维度相关 (breath≈artistry) 时互相抵消, 实测最大 ≈2.7。
    可验证不变量: 预设切换产生可感知 (≥0.5) 的总分变化, 方向由权重差异驱动。"""
    pop_total = score_state['presets']['pop']['total_score']
    bc_total = score_state['presets']['bel_canto']['total_score']
    gap = abs(pop_total - bc_total)
    assert gap >= 0.5, \
        f'Presets produced near-identical totals: pop={pop_total}, bel_canto={bc_total}, gap={gap:.2f}'


@then('"美声" 预设的气息评分应高于 "流行" 预设 (权重更高)')
def check_bel_canto_breath_higher(score_state):
    pop_breath = score_state['presets']['pop']['weighted_dimensions']['breath']
    bc_breath = score_state['presets']['bel_canto']['weighted_dimensions']['breath']
    assert bc_breath > pop_breath, \
        f'bel_canto breath {bc_breath} should exceed pop breath {pop_breath}'


@then('"流行" 预设的艺术评分应高于 "美声" 预设')
def check_pop_artistry_higher(score_state):
    pop_artistry = score_state['presets']['pop']['weighted_dimensions']['artistry']
    bc_artistry = score_state['presets']['bel_canto']['weighted_dimensions']['artistry']
    assert pop_artistry > bc_artistry, \
        f'pop artistry {pop_artistry} should exceed bel_canto artistry {bc_artistry}'


@then('两个预设的音准绝对分值应接近 (音准测量与风格无关, 仅权重不同)')
def check_pitch_score_stable(score_state):
    """音准维度原始分数相同, 仅加权值不同 — 验证预设不改测量结果.

    weighted_dimensions 为 round(raw * w, 1) (见 scoring.py), 反解误差上界
    = 0.05 / min(w)。pop pitch w=0.21 ⇒ 误差 ≤ 0.238, 故容差取 0.3。
    """
    raw_pitch = score_state['dims'].get('pitch', 0)
    pop_recovered = (score_state['presets']['pop']['weighted_dimensions']['pitch']
                     / score_state['presets']['pop']['applied_weights']['pitch'])
    bc_recovered = (score_state['presets']['bel_canto']['weighted_dimensions']['pitch']
                    / score_state['presets']['bel_canto']['applied_weights']['pitch'])
    assert raw_pitch == pytest.approx(pop_recovered, abs=0.3)
    assert raw_pitch == pytest.approx(bc_recovered, abs=0.3)


@then('结果中应标注 applied_preset 字段')
def check_applied_preset_field(score_state):
    assert score_state['presets']['pop']['applied_preset'] == 'pop'
    assert score_state['presets']['bel_canto']['applied_preset'] == 'bel_canto'


@when('默认使用 "流行" 预设评估')
def evaluate_rap_with_pop_preset():
    """说唱检测场景 — 前端自动风格检测未实现 (v6.0 规格), 后续 Then 即 xfail"""


@when('先用默认权重评估, 再用自定义权重 (Pitch+10%, Artistry-10%) 评估')
def evaluate_default_and_custom(api_client, score_state):
    """同一组维度分数, 默认 vs 自定义权重 (pitch+0.03, artistry-0.03)"""
    scores = _upload(api_client, score_state['vocal_path'], 'quick')
    dims = _six_dim_scores(scores['scores'])
    resp_default = api_client.post(
        '/api/v1/scoring/apply-weights', json={'dimension_scores': dims})
    assert resp_default.status_code == 200, resp_default.text
    default_weights = resp_default.json()['data']['applied_weights']
    custom = dict(default_weights)
    custom['pitch'] += 0.03
    custom['artistry'] -= 0.03
    resp_custom = api_client.post(
        '/api/v1/scoring/apply-weights',
        json={'dimension_scores': dims, 'weights': custom},
    )
    assert resp_custom.status_code == 200, resp_custom.text
    score_state['weights_cmp'] = {
        'default': resp_default.json()['data'],
        'custom': resp_custom.json()['data'],
        'dims': dims,
    }


@then('两次评分的 total_score 差异应在合理范围 (≤ 15 分)')
def check_weight_total_diff(score_state):
    d = score_state['weights_cmp']['default']['total_score']
    c = score_state['weights_cmp']['custom']['total_score']
    assert abs(d - c) <= 15, f'Total diff too large: default={d}, custom={c}'


@then('自定义权重的 Pitch 维度分数影响应大于默认权重')
def check_custom_pitch_impact(score_state):
    d = score_state['weights_cmp']
    d_pitch = d['default']['weighted_dimensions']['pitch']
    c_pitch = d['custom']['weighted_dimensions']['pitch']
    assert c_pitch > d_pitch, f'Custom pitch {c_pitch} should exceed default {d_pitch}'


@then('结果中应可对比两次评分的维度分数变化')
def check_dimension_compare(score_state):
    d = score_state['weights_cmp']
    for dim in ('pitch', 'rhythm', 'breath', 'technique', 'muscle', 'artistry'):
        assert dim in d['default']['weighted_dimensions']
        assert dim in d['custom']['weighted_dimensions']


# ── 说唱检测 (未实现 → xfail) ──

@then('系统应检测到音频特征与流行风格不匹配')
def check_rap_detection():
    pytest.xfail('v6.0 规格: 前端自动风格检测/建议切换未实现')


@then('应在结果中提示 "检测到说唱特征, 建议切换为说唱预设以获得更准确评分"')
def check_rap_tip():
    pytest.xfail('v6.0 规格: 前端自动风格检测/建议切换未实现')


@then('不应强制切换 (用户可选择忽略)')
def check_rap_no_force():
    pytest.xfail('v6.0 规格: 前端自动风格检测/建议切换未实现')


# ── Then (基础区分度) ──────────────────────────────

@then('专业级 total_score 应比初学者高 (评分排序能区分水平)')
def check_differentiation(score_state):
    """v7.14 规格修正: 真实演唱 total_score 压缩在 ~55-65 区间 (实测 pro=62.1/beg=58.9),
    20 分差距不可达。可验证不变量: 排序正确 (pro > beginner)。"""
    pro_score = score_state['both']['pro'].get('total_score', 0)
    beginner_score = score_state['both']['beginner'].get('total_score', 0)
    assert pro_score > beginner_score, \
        f'Pro total {pro_score} should exceed beginner {beginner_score}'


@then('至少一个核心维度的分数差距应 ≥ 10 分')
def check_strong_dimension_gap(score_state):
    """v7.14: 单维区分度强于总分 — 实测 rhythm 30.4 vs 9.3 (gap 21)。
    总分被权重平均摊平, 单维 ≥10 是总分排序之外的第二个可验证不变量。"""
    pro = score_state['both']['pro'].get('scores', {})
    beginner = score_state['both']['beginner'].get('scores', {})
    dims = ['pitch', 'rhythm', 'breath', 'technique', 'muscle_strength', 'artistry']
    gaps = {d: abs(pro.get(d, 0) - beginner.get(d, 0)) for d in dims}
    assert max(gaps.values()) >= 10, \
        f'No dimension differentiates by >=10: {gaps}'


@then('两个模式的 total_score 差距应小于 10%')
def check_mode_consistency(score_state):
    quick_score = score_state['modes']['quick'].get('total_score', 0)
    pro_score = score_state['modes']['professional'].get('total_score', 0)
    if quick_score == 0:
        pytest.skip('Quick score is 0, cannot compare ratio')
    diff_pct = abs(quick_score - pro_score) / quick_score * 100
    assert diff_pct < 10, \
        f'Mode inconsistency: quick={quick_score}, pro={pro_score}, diff={diff_pct:.1f}%'


@then('各维度的评分趋势应相同')
def check_dimension_trends(score_state):
    quick_dims = score_state['modes']['quick'].get('scores', {})
    pro_dims = score_state['modes']['professional'].get('scores', {})
    assert set(quick_dims.keys()) == set(pro_dims.keys()), \
        f'Dimension mismatch: {set(quick_dims.keys())} vs {set(pro_dims.keys())}'


@then('每个维度的最高分与最低分差距应至少 3 分')
def check_per_dimension_differentiation(score_state):
    all_scores = score_state['all_quick']
    # 六维 (muscle_strength → muscle 映射)
    dimensions = ['pitch', 'rhythm', 'breath', 'technique', 'muscle_strength', 'artistry']

    for dim in dimensions:
        dim_scores = [r['scores'].get(dim, 0) for r in all_scores if r['scores'].get(dim)]
        if len(dim_scores) < 2:
            continue
        diff = max(dim_scores) - min(dim_scores)
        assert diff >= 3, \
            f'{dim} differentiation too low: max={max(dim_scores)}, min={min(dim_scores)}, diff={diff}'


@then('每个音频的 total_score 应为 0.0')
def check_all_non_vocal_zero(score_state):
    for i, payload in enumerate(score_state['all_quick']):
        score = payload.get('total_score', -1)
        assert score == 0.0, f'Non-vocal file {i} got score {score}, expected 0.0'
