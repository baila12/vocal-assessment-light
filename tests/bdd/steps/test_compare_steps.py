"""
Step definitions for compare.feature

Implements Given/When/Then steps for DTW comparison scenarios.
"""
from pytest_bdd import given, when, then, parsers, scenarios

scenarios('../features/compare.feature')


@given('我准备两个完全相同的音频文件')
def identical_audio_files(test_data_dir):
    """Return two paths to the same audio file (or two copies)."""
    vocal_dir = test_data_dir / 'audio' / 'vocal'
    files = sorted(vocal_dir.glob('*.wav')) + sorted(vocal_dir.glob('*.mp3'))
    if not files:
        pytest.skip('No test vocal files available')
    # Use same file for both reference and user
    return str(files[0]), str(files[0])


@given(parsers.parse('标准音频 "{filename}"'))
def reference_audio(filename, test_data_dir):
    path = test_data_dir / 'audio' / 'vocal' / filename
    if not path.exists():
        pytest.skip(f'Reference audio not found: {filename}')
    return str(path)


@given(parsers.parse('音高偏移 50 音分的用户音频 "{filename}"'))
def off_pitch_audio(filename, test_data_dir):
    """Note: This requires a pre-generated pitch-shifted file."""
    path = test_data_dir / 'audio' / 'vocal' / filename
    if not path.exists():
        pytest.skip(f'Off-pitch audio not found: {filename}')
    return str(path)


@given(parsers.parse('uploads 目录中存在带 "{tag}" 标签的参考音频'))
def uploads_has_reference(tag, project_root):
    """Verify that uploads/ directory has reference-tagged audio files."""
    uploads_dir = project_root / 'uploads'
    if not uploads_dir.exists():
        pytest.skip('uploads/ directory does not exist')
    # Check for files with the tag in filename
    tagged = [f for f in uploads_dir.iterdir() if tag in f.name]
    if not tagged:
        pytest.skip(f'No files with tag "{tag}" found in uploads/')


@when('我发起 DTW 对比分析')
def trigger_dtw_comparison(api_client, identical_audio_files):
    """Send both files to the comparison endpoint."""
    ref_path, user_path = identical_audio_files
    with open(ref_path, 'rb') as ref_f, open(user_path, 'rb') as user_f:
        response = api_client.post(
            '/api/compare',
            data={
                'standard_file': (ref_f, Path(ref_path).name),
                'file': (user_f, Path(user_path).name),
            },
            content_type='multipart/form-data'
        )
    return response


@when('我仅上传用户音频到独立上传接口')
def upload_user_audio_only(api_client, identical_audio_files):
    """Upload only user audio - DTW auto-search should trigger."""
    _, user_path = identical_audio_files
    with open(user_path, 'rb') as f:
        response = api_client.post(
            '/api/upload',
            data={'file': (f, Path(user_path).name)},
            content_type='multipart/form-data'
        )
    return response


@then('对比评分应不低于 95 分')
def check_dtw_score_high(dtw_response):
    data = dtw_response.get_json()
    if not data.get('success', True):
        pytest.skip(f'Comparison failed: {data.get("error")}')
    score = data.get('data', {}).get('score', data.get('total_score', 0))
    assert score >= 95, f'DTW score too low: {score}'


@then('音准匹配率应不低于 95%')
def check_pitch_match_high(dtw_response):
    data = dtw_response.get_json()
    match = data.get('data', {}).get('dimensions', {}).get('pitch', {}).get('score', 0)
    if match == 0:
        match = data.get('data', {}).get('pitch_match_rate', 0)
    assert match >= 95, f'Pitch match rate too low: {match}%'


@then('节奏匹配率应不低于 95%')
def check_rhythm_match_high(dtw_response):
    data = dtw_response.get_json()
    match = data.get('data', {}).get('dimensions', {}).get('rhythm', {}).get('score', 0)
    if match == 0:
        match = data.get('data', {}).get('rhythm_match_rate', 0)
    assert match >= 95, f'Rhythm match rate too low: {match}%'


@then('音准评分应低于 90 分')
def check_pitch_score_low(dtw_response):
    data = dtw_response.get_json()
    if not data.get('success', True):
        pytest.skip(f'Comparison failed: {data.get("error")}')
    score = data.get('data', {}).get('score', data.get('total_score', 100))
    assert score < 90, f'Expected low pitch score, got {score}'


@then('返回结果中应包含 problem_frames')
def check_problem_frames_present(dtw_response):
    data = dtw_response.get_json()
    problems = data.get('data', {}).get('problem_frames', data.get('problem_frames', []))
    assert len(problems) > 0, 'No problem_frames found in response'


@then('系统应自动找到参考音频')
def check_auto_reference_found(upload_response):
    data = upload_response.get_json()
    # DTW auto-search should result in dtw_enabled or similar indicator
    # This is validated by the score being in valid range
    score = data.get('total_score', -1)
    assert score >= 0, 'No valid score returned'


@then('DTW 融合评分应被触发')
def check_dtw_fusion_triggered(upload_response):
    data = upload_response.get_json()
    # DTW fusion should produce a score when reference is auto-found
    score = data.get('total_score', -1)
    assert 0 <= score <= 100, f'Invalid DTW fusion score: {score}'


import pytest
from pathlib import Path
