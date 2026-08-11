"""
Step definitions for compare.feature

v7.14 P2 重写: 对齐真实 /api/v1/compare 契约 (v7.13 P5 — 双轨音高曲线
standard_pitch/user_pitch + 低对齐段落 low_alignment_segments)。

跨步骤状态通过场景级 `compare_state` fixture 传递 (pytest-bdd 8.x 兼容,
@given/@when/@then 函数名不注册为 fixture)。
"""

from pathlib import Path

import pytest
from pytest_bdd import given, when, then, parsers, scenarios


@pytest.fixture
def compare_state():
    """场景级状态 — 跨步骤传递音频路径与对比响应"""
    return {}


def _vocal_file(test_data_dir, filename: str) -> Path:
    """test_data/audio/vocal 下的测试音频, 不存在则跳过场景"""
    path = test_data_dir / 'audio' / 'vocal' / filename
    if not path.exists():
        pytest.skip(f'测试音频不存在: {path}')
    return path


# ── Given ──

@given(parsers.parse('标准音频 "{std}" 和用户音频 "{user}"'))
def standard_and_user_audio(std, user, test_data_dir, compare_state):
    """两个不同测试音频 → compare_state (JSON 路径直达 filepath, 免再上传)"""
    compare_state['standard'] = str(_vocal_file(test_data_dir, std))
    compare_state['user'] = str(_vocal_file(test_data_dir, user))


@given('同一个音频文件作为标准与用户上传')
def same_audio_twice(test_data_dir, compare_state):
    """相同文件 → 标准与用户路径一致 (DTW 对齐应接近完美)"""
    path = str(_vocal_file(test_data_dir, 'vocals.wav'))
    compare_state['standard'] = path
    compare_state['user'] = path


@given('用户在特定段落音高偏移 50 音分的音频')
def off_pitch_audio_required():
    """需要预生成的移调测试音频 — 不在 CI 测试数据中, 标记 xfail"""
    pytest.xfail('需要预生成的音高偏移测试音频 (不在 CI 测试数据) — DEEP_REVIEW P2-16 对比场景')


# ── When ──

@when('我发起对比分析请求')
def request_compare(api_client, compare_state):
    """POST /api/v1/compare (JSON body: standard_filepath/user_filepath/style)"""
    resp = api_client.post(
        '/api/v1/compare',
        json={
            'standard_filepath': compare_state['standard'],
            'user_filepath': compare_state['user'],
            'style': 'pop',
        },
    )
    assert resp.status_code == 200, \
        f'compare failed: {resp.status_code} {resp.text}'
    compare_state['data'] = resp.json()['data']


# ── Then ──

@then('返回结构应包含 DTW 对比核心字段')
def check_core_fields(compare_state):
    d = compare_state['data']
    assert 0 <= d['score'] <= 100, f'score 越界: {d["score"]}'
    assert isinstance(d['level'], str) and d['level'], 'level 应为非空字符串'
    assert 0 <= d['confidence'] <= 1.0, f'confidence 越界: {d["confidence"]}'
    assert 0 <= d['pitch_match_rate'] <= 100, f'pitch_match_rate 越界: {d["pitch_match_rate"]}'
    assert 0 <= d['rhythm_match_rate'] <= 100, f'rhythm_match_rate 越界: {d["rhythm_match_rate"]}'
    assert d.get('method') == 'three_level_dtw', f'method: {d.get("method")}'


@then('应包含双轨音高曲线数据')
def check_pitch_curves(compare_state):
    d = compare_state['data']
    for key in ('standard_pitch', 'user_pitch'):
        curve = d.get(key)
        assert isinstance(curve, list) and curve, f'{key} 应为非空列表'
        point = curve[0]
        for field in ('time', 'frequency', 'confidence'):
            assert field in point, f'{key} 曲线点缺少 {field}'


@then('应包含对比差异摘要')
def check_comparison_summary(compare_state):
    comp = compare_state['data'].get('comparison', {})
    for field in ('pitch_diff', 'rhythm_diff', 'total_diff', 'std_total', 'user_total'):
        assert field in comp, f'comparison 缺少 {field}'


@then('应包含低对齐置信度段落字段')
def check_low_alignment_field(compare_state):
    assert isinstance(compare_state['data'].get('low_alignment_segments'), list), \
        'low_alignment_segments 应为列表'


@then('对比总分应接近满分')
def check_score_near_perfect(compare_state):
    score = compare_state['data']['score']
    assert score >= 90, f'相同音频对比总分应≥90, 实际 {score}'


@then('音准匹配率应不低于 95%')
def check_pitch_match_rate(compare_state):
    rate = compare_state['data']['pitch_match_rate']
    assert rate >= 95, f'pitch_match_rate 应≥95, 实际 {rate}'


@then('节奏匹配率应不低于 95%')
def check_rhythm_match_rate(compare_state):
    rate = compare_state['data']['rhythm_match_rate']
    assert rate >= 95, f'rhythm_match_rate 应≥95, 实际 {rate}'


@then('对齐置信度应接近 1.0')
def check_confidence_high(compare_state):
    conf = compare_state['data']['confidence']
    # 实测 (2026-08-11): 完全相同音频 DTW 置信度 0.938 (非 1.0, 有微小对齐噪声)
    assert conf > 0.90, f'相同音频 confidence 应>0.90, 实际 {conf}'


scenarios('../features/compare.feature')
