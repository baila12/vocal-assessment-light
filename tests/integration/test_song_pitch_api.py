"""歌曲音高 API 集成测试 — v7.13 参考音高

GET /api/v1/songs/{id}/pitch — 歌曲 F0 曲线 (选歌录音参考线数据源)。
独立进程运行, VAS_SONGS_DB/VAS_SONGS_DIR 指向临时目录隔离。
"""

import io
import os
import tempfile
import wave
import numpy as np
from pathlib import Path

# ── 隔离歌曲库 DB + 音频目录 — 必须在 create_app() 首次调用前设置 ──
_tmp_dir = tempfile.mkdtemp(prefix='vas_pitch_test_')
os.environ['VAS_SONGS_DB'] = str(Path(_tmp_dir) / 'test_songs.db')
os.environ['VAS_SONGS_DIR'] = str(Path(_tmp_dir) / 'audio')

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


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


def _create_song(client, title, audio: bytes | None = None) -> dict:
    data = {'title': title, 'artist': '邓丽君', 'key': 'C', 'bpm': '78',
            'difficulty': 'beginner', 'style': 'pop'}
    files = {}
    if audio is not None:
        files['file'] = (f'{title}.wav', io.BytesIO(audio), 'audio/wav')
    resp = client.post('/api/v1/songs', data=data, files=files or None)
    assert resp.status_code == 200, resp.text
    return resp.json()['song']


class TestSongPitchApi:
    """GET /api/v1/songs/{id}/pitch — F0 曲线"""

    def test_get_pitch_returns_curve(self, client):
        """带音频歌曲 → 返回 F0 曲线 (song_id/frequencies/times/confidence)"""
        song = _create_song(client, '音高测试', audio=_sine_wav())
        resp = client.get(f"/api/v1/songs/{song['id']}/pitch")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data['success'] is True
        curve = data['data']
        assert curve['song_id'] == song['id']
        assert curve['frame_count'] > 0
        assert len(curve['frequencies']) == len(curve['times']) == len(curve['confidence'])
        assert curve['duration_seconds'] > 0
        # 正弦波 → 存在非零频率
        assert any(f > 0 for f in curve['frequencies']), '正弦波应检出 F0'

    def test_get_pitch_cached_returns_same(self, client):
        """重复请求 → 同样曲线 (缓存命中)"""
        song = _create_song(client, '缓存测试', audio=_sine_wav())
        first = client.get(f"/api/v1/songs/{song['id']}/pitch").json()['data']
        second = client.get(f"/api/v1/songs/{song['id']}/pitch").json()['data']
        assert first['frame_count'] == second['frame_count']
        assert first['frequencies'] == second['frequencies']

    def test_get_pitch_unknown_song_404(self, client):
        """不存在歌曲 → 404"""
        resp = client.get('/api/v1/songs/not-exist/pitch')
        assert resp.status_code == 404

    def test_get_pitch_song_without_file_400(self, client):
        """歌曲无音频文件 → 400"""
        song = _create_song(client, '无文件歌曲', audio=None)
        resp = client.get(f"/api/v1/songs/{song['id']}/pitch")
        assert resp.status_code == 400

    def test_get_pitch_missing_audio_file_404(self, client):
        """歌曲记录存在但音频文件被删除 → 404"""
        song = _create_song(client, '文件消失', audio=_sine_wav())
        Path(song['filepath']).unlink()
        resp = client.get(f"/api/v1/songs/{song['id']}/pitch")
        assert resp.status_code == 404


class TestSongCompareApi:
    """POST /api/v1/songs/{id}/compare — 上传录音与选中歌曲 DTW 对比 (选歌录音增强)"""

    def test_compare_user_audio_against_song(self, client):
        """上传同音高用户录音 → 200, 返回对比评分"""
        song = _create_song(client, '对比歌曲', audio=_sine_wav(freq=440))
        user_audio = _sine_wav(freq=440)  # 同音高 → 良好匹配
        resp = client.post(
            f"/api/v1/songs/{song['id']}/compare",
            files={'user_file': ('user.wav', io.BytesIO(user_audio), 'audio/wav')},
            data={'style': 'pop'},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data['success'] is True
        assert data['data']['score'] is not None
        assert 'pitch_match_rate' in data['data']

    def test_compare_missing_user_file_400(self, client):
        """缺用户文件 → 400"""
        song = _create_song(client, '对比缺文件', audio=_sine_wav())
        resp = client.post(f"/api/v1/songs/{song['id']}/compare", data={})
        assert resp.status_code == 400

    def test_compare_unknown_song_404(self, client):
        """不存在歌曲 → 404"""
        resp = client.post(
            '/api/v1/songs/nope/compare',
            files={'user_file': ('u.wav', io.BytesIO(_sine_wav()), 'audio/wav')},
        )
        assert resp.status_code == 404

    def test_compare_song_without_file_400(self, client):
        """歌曲无音频文件 → 400"""
        song = _create_song(client, '无文件对比', audio=None)
        resp = client.post(
            f"/api/v1/songs/{song['id']}/compare",
            files={'user_file': ('u.wav', io.BytesIO(_sine_wav()), 'audio/wav')},
        )
        assert resp.status_code == 400
