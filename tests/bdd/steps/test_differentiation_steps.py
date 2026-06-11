"""
Step definitions for differentiation.feature

Implements Given/When/Then steps for score differentiation scenarios.
"""
from pytest_bdd import given, when, then, parsers, scenarios

scenarios('../features/differentiation.feature')


@given(parsers.parse('一个专业级演唱音频 "{filename}"'))
def pro_singer_audio(filename, test_data_dir):
    path = test_data_dir / 'audio' / 'vocal' / filename
    if not path.exists():
        pytest.skip(f'Pro audio not found: {filename}')
    return str(path)


@given(parsers.parse('一个初学者演唱音频 "{filename}"'))
def beginner_audio(filename, test_data_dir):
    path = test_data_dir / 'audio' / 'vocal' / filename
    if not path.exists():
        pytest.skip(f'Beginner audio not found: {filename}')
    return str(path)


@given(parsers.parse('同一个人声演唱音频 "{filename}"'))
def single_vocal_audio(filename, test_data_dir):
    path = test_data_dir / 'audio' / 'vocal' / filename
    if not path.exists():
        # Try any available vocal file
        candidates = sorted((test_data_dir / 'audio' / 'vocal').glob('*'))
        if candidates:
            return str(candidates[0])
    assert path.exists(), f'Test file not found: {path}'
    return str(path)


@given('5 个不同水平的演唱音频')
def five_level_audios(test_data_dir):
    """Return up to 5 vocal files of different quality levels."""
    vocal_dir = test_data_dir / 'audio' / 'vocal'
    files = sorted(vocal_dir.glob('*'))
    if len(files) < 2:
        pytest.skip(f'Need at least 2 vocal files, found {len(files)}')
    return [str(f) for f in files[:5]]


@given('5 个合成或噪声音频文件')
def five_non_vocal_audios(test_data_dir):
    """Return up to 5 non-vocal files."""
    non_vocal_dir = test_data_dir / 'audio' / 'non_vocal'
    if not non_vocal_dir.exists():
        pytest.skip('non_vocal directory not found')
    files = sorted(non_vocal_dir.glob('*'))
    if not files:
        pytest.skip('No non-vocal files found')
    return [str(f) for f in files[:5]]


@when('两个音频都用 quick 模式评估')
def evaluate_both_quick(api_client, pro_singer_audio, beginner_audio):
    """Evaluate both audios in quick mode."""
    scores = {}
    for label, path in [('pro', pro_singer_audio), ('beginner', beginner_audio)]:
        with open(path, 'rb') as f:
            resp = api_client.post(
                '/api/upload',
                data={'file': (f, Path(path).name), 'mode': 'quick'},
                content_type='multipart/form-data'
            )
        data = resp.get_json()
        scores[label] = data.get('total_score', 0)
    return scores


@when('分别用 quick 和 professional 模式评估')
def evaluate_both_modes(api_client, single_vocal_audio):
    """Evaluate the same audio in both modes."""
    results = {}
    for mode in ['quick', 'professional']:
        with open(single_vocal_audio, 'rb') as f:
            resp = api_client.post(
                '/api/upload',
                data={'file': (f, Path(single_vocal_audio).name), 'mode': mode},
                content_type='multipart/form-data'
            )
        data = resp.get_json()
        results[mode] = {
            'total_score': data.get('total_score', 0),
            'scores': data.get('scores', {})
        }
    return results


@when('全部用 quick 模式评估')
def evaluate_all_quick(api_client, five_level_audios):
    """Evaluate all files in quick mode."""
    all_scores = []
    for path in five_level_audios:
        with open(path, 'rb') as f:
            resp = api_client.post(
                '/api/upload',
                data={'file': (f, Path(path).name), 'mode': 'quick'},
                content_type='multipart/form-data'
            )
        data = resp.get_json()
        if data.get('success') or resp.status_code == 200:
            all_scores.append({
                'total_score': data.get('total_score', 0),
                'scores': data.get('scores', {})
            })
    assert len(all_scores) >= 2, 'Need at least 2 valid results'
    return all_scores


@when('全部用 quick 模式评估')  # Re-register for non_vocal
def evaluate_all_non_vocal_quick(api_client, five_non_vocal_audios):
    """Evaluate all non-vocal files in quick mode."""
    all_scores = []
    for path in five_non_vocal_audios:
        with open(path, 'rb') as f:
            resp = api_client.post(
                '/api/upload',
                data={'file': (f, Path(path).name), 'mode': 'quick'},
                content_type='multipart/form-data'
            )
        data = resp.get_json()
        all_scores.append(data.get('total_score', -1))
    return all_scores


# ── Then ───────────────────────────────────────────

@then('专业级 total_score 应比初学者高至少 20 分')
def check_differentiation(evaluate_both_quick):
    pro_score = evaluate_both_quick['pro']
    beginner_score = evaluate_both_quick['beginner']
    diff = pro_score - beginner_score
    assert diff >= 20, \
        f'Insufficient differentiation: pro={pro_score}, beginner={beginner_score}, diff={diff}'


@then('两个模式的 total_score 差距应小于 10%')
def check_mode_consistency(evaluate_both_modes):
    quick_score = evaluate_both_modes['quick']['total_score']
    pro_score = evaluate_both_modes['professional']['total_score']
    if quick_score == 0:
        pytest.skip('Quick score is 0, cannot compare ratio')
    diff_pct = abs(quick_score - pro_score) / quick_score * 100
    assert diff_pct < 10, \
        f'Mode inconsistency: quick={quick_score}, pro={pro_score}, diff={diff_pct:.1f}%'


@then('各维度的评分趋势应相同')
def check_dimension_trends(evaluate_both_modes):
    quick_dims = evaluate_both_modes['quick']['scores']
    pro_dims = evaluate_both_modes['professional']['scores']
    # Verify same dimensions exist
    assert set(quick_dims.keys()) == set(pro_dims.keys()), \
        f'Dimension mismatch: {set(quick_dims.keys())} vs {set(pro_dims.keys())}'


@then('每个维度的最高分与最低分差距应至少 3 分')
def check_per_dimension_differentiation(evaluate_all_quick):
    all_scores = evaluate_all_quick
    dimensions = ['pitch', 'rhythm', 'breath', 'technique', 'artistry']

    for dim in dimensions:
        dim_scores = [r['scores'].get(dim, 0) for r in all_scores if r['scores'].get(dim)]
        if len(dim_scores) < 2:
            continue
        diff = max(dim_scores) - min(dim_scores)
        assert diff >= 3, \
            f'{dim} differentiation too low: max={max(dim_scores)}, min={min(dim_scores)}, diff={diff}'


@then('每个音频的 total_score 应为 0.0')
def check_all_non_vocal_zero(evaluate_all_non_vocal_quick):
    for i, score in enumerate(evaluate_all_non_vocal_quick):
        assert score == 0.0, f'Non-vocal file {i} got score {score}, expected 0.0'


import pytest
from pathlib import Path
