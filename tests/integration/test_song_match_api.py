"""歌曲自动匹配 API 集成测试 — TDD RED (v7.14 auto-match)

/songs/match 核心场景用真实 librosa 提取 (合成 WAV);
upload auto_match flag 用 monkeypatch 验证路由层注入逻辑 (不跑完整分析管线)。
独立进程运行 (与 test_songs_api.py 相同约定)。
"""

import io
import os
import tempfile
import wave
from pathlib import Path

# ── 隔离歌曲库 DB + 音频目录 — 必须在 create_app() 首次调用前设置 ──
_tmp_dir = tempfile.mkdtemp(prefix='vas_songmatch_')
os.environ['VAS_SONGS_DB'] = str(Path(_tmp_dir) / 'test_songs.db')
os.environ['VAS_SONGS_DIR'] = str(Path(_tmp_dir) / 'audio')

import numpy as np  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

SR = 22050


def _make_wav(duration, signal='sine', freq=440.0):
    """合成 16-bit PCM WAV 字节"""
    n = int(SR * duration)
    if signal == 'sine':
        t = np.linspace(0, duration, n, endpoint=False)
        y = np.sin(2 * np.pi * freq * t) * 0.8
    elif signal == 'metronome':
        y = np.zeros(n)
        hop = int(0.05 * SR)
        for start in np.arange(0.0, duration, 0.5):
            i0 = int(start * SR)
            i1 = min(i0 + hop, n)
            tt = np.arange(i1 - i0) / SR
            y[i0:i1] += np.sin(2 * np.pi * 1000 * tt) * np.exp(-tt * 40) * 0.8
    elif signal == 'silence':
        y = np.zeros(n)
    else:
        raise ValueError(f'unknown signal: {signal}')
    y16 = (y * 32767).astype('<i2')
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(y16.tobytes())
    return buf.getvalue()


@pytest.fixture(scope='module')
def client() -> TestClient:
    from backend.main import create_app
    app = create_app()
    with TestClient(app) as c:
        yield c


def _add_song(client, title, wav_bytes) -> str:
    """预置标准歌曲, 返回 song_id"""
    resp = client.post(
        '/api/v1/songs',
        data={'title': title, 'artist': '测试歌手'},
        files={'file': (f'{title}.wav', io.BytesIO(wav_bytes), 'audio/wav')},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()['song']['id']


def _match(client, wav_bytes, top_n=None):
    data = {'top_n': str(top_n)} if top_n is not None else None
    return client.post(
        '/api/v1/songs/match',
        files={'file': ('user.wav', io.BytesIO(wav_bytes), 'audio/wav')},
        data=data,
    )


class TestMatchEndpoint:
    def test_match_success(self, client):
        """同源音频 → 命中歌曲, 返回候选"""
        metronome = _make_wav(6.0, 'metronome')
        _add_song(client, '节拍歌', metronome)
        resp = _match(client, metronome)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data['success'] is True
        assert data['matched'] is True
        assert data['matched_song'] is not None
        assert data['matched_song']['title'] == '节拍歌'
        assert len(data['candidates']) >= 1

    def test_match_returns_top_n(self, client):
        metronome = _make_wav(6.0, 'metronome')
        for i in range(3):
            _add_song(client, f'节拍歌{i}', metronome)
        resp = _match(client, metronome, top_n=2)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert len(data['candidates']) == 2
        confs = [c['confidence'] for c in data['candidates']]
        assert confs == sorted(confs, reverse=True)

    def test_match_no_match_fallback(self, client):
        _add_song(client, '节拍歌NMF', _make_wav(6.0, 'metronome'))
        resp = _match(client, _make_wav(4.0, 'silence'))
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data['matched'] is False
        assert data['matched_song'] is None
        assert data['fallback_reason'] == 'no_match'

    def test_match_invalid_format_400(self, client):
        resp = client.post(
            '/api/v1/songs/match',
            files={'file': ('user.txt', io.BytesIO(b'not audio'), 'text/plain')},
        )
        assert resp.status_code == 400


class TestUploadAutoMatchFlag:
    """upload 路由层注入逻辑 — monkeypatch 隔离分析管线"""

    def _fake_analyze(self, *args, **kwargs):
        return {
            'success': True,
            'total_score': 70.0,
            'scores': {'pitch': 70},
            'level': 'B',
            'grade': 'B',
            'mode': 'quick',
            'is_voice': True,
        }

    def test_upload_auto_match_off_no_match_fields(self, client, monkeypatch):
        """auto_match 默认关 → matched_song 为 None, 不注入候选"""
        monkeypatch.setattr('api.business.analyze_and_score', self._fake_analyze)
        resp = client.post(
            '/api/v1/upload',
            files={'file': ('user.wav', io.BytesIO(_make_wav(4.0, 'sine')), 'audio/wav')},
            data={'mode': 'quick'},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data['matched_song'] is None
        assert data['matched_candidates'] == []
        assert data['fallback_reason'] == ''
        # v7.14 审查 TEST_GAP: HTTP 响应契约字段 scoring_warnings 恒存在 (成功时为空)
        assert data['scoring_warnings'] == []

    def test_upload_auto_match_on_injects_fields(self, client, monkeypatch):
        """auto_match=true → 注入匹配结果字段 (同源音频确定命中, 标题不保证唯一)"""
        monkeypatch.setattr('api.business.analyze_and_score', self._fake_analyze)
        metronome = _make_wav(6.0, 'metronome')
        _add_song(client, '匹配歌Upload', metronome)
        resp = client.post(
            '/api/v1/upload',
            files={'file': ('user.wav', io.BytesIO(metronome), 'audio/wav')},
            data={'mode': 'quick', 'auto_match': 'true'},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data['matched_song'] is not None
        assert set(data['matched_song'].keys()) == {'id', 'title', 'artist', 'confidence'}
        assert data['matched_song']['confidence'] >= 0.6
        assert data['fallback_reason'] == ''
