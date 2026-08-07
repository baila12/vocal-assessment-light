"""对比分析 API 音高曲线扩展测试 — v7.13 Phase 5

POST /api/v1/compare 响应新增 standard_pitch / user_pitch / low_alignment_segments。
向后兼容: 既有 score/level 字段保持不变。

策略: monkeypatch 重计算部件 (CompareAudioUseCase.execute_lightweight + analyze_and_score),
保留真实 PitchExtractionService.extract (librosa.yin) 验证新契约 — 测试快且确定。
独立进程运行, VAS_SONGS_DB/VAS_SONGS_DIR 指向临时目录隔离。
"""

import io
import os
import tempfile
import wave
import numpy as np
from pathlib import Path

# ── 隔离歌曲库 DB + 音频目录 — 必须在 create_app() 首次调用前设置 ──
_tmp_dir = tempfile.mkdtemp(prefix='vas_compare_pitch_')
os.environ['VAS_SONGS_DB'] = str(Path(_tmp_dir) / 'test_songs.db')
os.environ['VAS_SONGS_DIR'] = str(Path(_tmp_dir) / 'audio')

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from backend.application.comparison.compare_audio import CompareAudioUseCase  # noqa: E402


@pytest.fixture(scope='module')
def client() -> TestClient:
    from backend.main import create_app
    app = create_app()
    with TestClient(app) as c:
        yield c


def _sine_wav(duration_s=1.0, sr=16000, freq=440.0) -> bytes:
    """正弦波 WAV — 保证 F0 检出非零"""
    n = int(sr * duration_s)
    t = np.linspace(0, duration_s, n, endpoint=False)
    samples = (np.sin(2 * np.pi * freq * t) * 0.5 * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(samples.tobytes())
    return buf.getvalue()


def _fake_dto(confidence: float) -> dict:
    """CompareAudioUseCase.execute_lightweight 的桩返回 (shape 与真实 DTO 一致)"""
    return {
        'success': True,
        'score': 78.5,
        'level': '良好',
        'confidence': confidence,
        'pitch_match_rate': 80.0,
        'rhythm_match_rate': 75.0,
        'avg_cents_error': 22.3,
        'diagnosis': ['音准整体良好'],
        'suggestions': ['注意长音保持'],
        'method': 'three_level_dtw',
    }


def _fake_analyze(*args, **kwargs) -> dict:
    """analyze_and_score 的桩返回 — 只保留 success 标志 (路由只检查它)"""
    return {'success': True, 'score': 75.0}


class TestComparePitchApi:
    """POST /api/v1/compare — 双轨音高曲线扩展"""

    def test_compare_returns_pitch_curves(self, client, monkeypatch):
        """高置信度对比 → 返回双轨 pitch 曲线 + 空低对齐段 + 既有字段保持"""
        monkeypatch.setattr(CompareAudioUseCase, 'execute_lightweight',
                            lambda self, std, user, style='pop': _fake_dto(confidence=0.9))
        monkeypatch.setattr('api.business.analyze_and_score', _fake_analyze)

        std = _sine_wav(freq=440.0)
        user = _sine_wav(freq=445.0)
        resp = client.post(
            '/api/v1/compare',
            files={
                'standard_file': ('std.wav', io.BytesIO(std), 'audio/wav'),
                'user_file': ('user.wav', io.BytesIO(user), 'audio/wav'),
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()['data']

        # 新契约: 双轨曲线
        for curve in (data['standard_pitch'], data['user_pitch']):
            assert isinstance(curve, list) and len(curve) > 0, '应返回非空 pitch 曲线'
            first = curve[0]
            assert set(first) >= {'time', 'frequency', 'confidence'}
            times = [p['time'] for p in curve]
            assert all(b >= a for a, b in zip(times, times[1:])), 'times 应单调非降'
            assert any(p['frequency'] > 0 for p in curve), '正弦波应检出 F0'

        # 高置信度 → 无低对齐段
        assert data['low_alignment_segments'] == []

        # 向后兼容: 既有字段保持
        assert data['score'] == 78.5
        assert data['level'] == '良好'
        assert data['pitch_match_rate'] == 80.0
        assert data['rhythm_match_rate'] == 75.0
        assert data['avg_cents_error'] == 22.3

    def test_compare_low_confidence_marks_segment(self, client, monkeypatch):
        """DTW 置信度 < 0.5 → 整段标记为低对齐段落"""
        monkeypatch.setattr(CompareAudioUseCase, 'execute_lightweight',
                            lambda self, std, user, style='pop': _fake_dto(confidence=0.3))
        monkeypatch.setattr('api.business.analyze_and_score', _fake_analyze)

        resp = client.post(
            '/api/v1/compare',
            files={
                'standard_file': ('std.wav', io.BytesIO(_sine_wav()), 'audio/wav'),
                'user_file': ('user.wav', io.BytesIO(_sine_wav()), 'audio/wav'),
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()['data']

        segments = data['low_alignment_segments']
        assert len(segments) == 1
        assert segments[0]['start'] == 0.0
        assert segments[0]['end'] > segments[0]['start']
        assert abs(segments[0]['avg_confidence'] - 0.3) < 1e-9

    def test_compare_missing_file_400(self, client):
        """缺文件 → 400 (回归保护, JSON 路径缺路径)"""
        resp = client.post('/api/v1/compare', json={})
        assert resp.status_code == 400
