"""歌曲库 API 集成测试 — TDD RED

独立进程运行 (与 test_api_routes.py 相同约定)。
通过 VAS_SONGS_DB 指向临时文件隔离数据库。
"""

import io
import os
import tempfile
from pathlib import Path

# ── 隔离歌曲库 DB + 音频目录 — 必须在 create_app() 首次调用前设置 ──
_tmp_dir = tempfile.mkdtemp(prefix='vas_songs_test_')
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


def _fake_wav() -> bytes:
    """最小合法 WAV 文件 (44 字节头 + 静音数据)"""
    header = (
        b'RIFF' + (36).to_bytes(4, 'little') + b'WAVEfmt '
        + (16).to_bytes(4, 'little') + b'\x01\x00\x01\x00'
        + (22050).to_bytes(4, 'little') + (22050).to_bytes(4, 'little')
        + b'\x01\x00\x08\x00' + b'data' + (0).to_bytes(4, 'little')
    )
    return header + bytes(22050)  # 1 秒静音


def _post(client, title, artist='邓丽君', **overrides):
    data = {
        'title': title, 'artist': artist,
        'key': 'C', 'bpm': '78', 'difficulty': 'beginner', 'style': 'pop',
    }
    data.update(overrides)
    return client.post(
        '/api/v1/songs',
        data=data,
        files={'file': (f'{title}.wav', io.BytesIO(_fake_wav()), 'audio/wav')},
    )


class TestCreateSong:
    def test_create_song_returns_song(self, client):
        resp = _post(client, title='月亮代表我的心')
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data['success'] is True
        song = data['song']
        assert song['metadata']['title'] == '月亮代表我的心'
        assert song['metadata']['artist'] == '邓丽君'
        assert song['id']

    def test_create_duplicate_returns_409(self, client):
        _post(client, title='重复之歌')
        resp = _post(client, title='重复之歌')
        assert resp.status_code == 409
        # FastAPI HTTPException 约定: {"detail": ...}
        assert '已存在' in resp.json()['detail']

    def test_create_same_title_different_artist_ok(self, client):
        _post(client, title='同名歌曲', artist='邓丽君')
        resp = _post(client, title='同名歌曲', artist='王菲')
        assert resp.status_code == 200

    def test_create_missing_title_returns_400(self, client):
        resp = client.post(
            '/api/v1/songs',
            data={'artist': '邓丽君'},
            files={'file': ('a.wav', io.BytesIO(_fake_wav()), 'audio/wav')},
        )
        assert resp.status_code == 400

    def test_create_invalid_style_returns_400(self, client):
        resp = _post(client, title='无效风格', style='jazz')
        assert resp.status_code == 400

    def test_create_invalid_difficulty_returns_400(self, client):
        resp = _post(client, title='无效难度', difficulty='hacker_rank')
        assert resp.status_code == 400

    def test_duplicate_cleans_orphan_audio_file(self, client):
        """重复检测返回 409 时应清理已保存的孤立音频文件"""
        _post(client, title='清理测试')
        audio_dir = Path(os.environ['VAS_SONGS_DIR'])
        before = len(list(audio_dir.glob('*')))
        resp = _post(client, title='清理测试')  # 重复 → 409
        assert resp.status_code == 409
        after = len(list(audio_dir.glob('*')))
        assert after == before, f'重复创建遗留孤立文件: {before} → {after}'


class TestListSongs:
    def test_list_returns_created_songs(self, client):
        _post(client, title='列表测试甲')
        resp = client.get('/api/v1/songs')
        assert resp.status_code == 200
        data = resp.json()
        assert data['success'] is True
        assert 'songs' in data and 'total' in data
        titles = [s['metadata']['title'] for s in data['songs']]
        assert '列表测试甲' in titles

    def test_list_filter_by_style(self, client):
        _post(client, title='风格测试流行', style='pop')
        _post(client, title='风格测试美声', style='classical')
        resp = client.get('/api/v1/songs', params={'style': 'classical'})
        data = resp.json()
        titles = [s['metadata']['title'] for s in data['songs']]
        assert '风格测试美声' in titles
        assert '风格测试流行' not in titles

    def test_list_search_by_title(self, client):
        _post(client, title='搜索目标曲目')
        _post(client, title='无关曲目')
        resp = client.get('/api/v1/songs', params={'search': '搜索目标'})
        data = resp.json()
        titles = [s['metadata']['title'] for s in data['songs']]
        assert '搜索目标曲目' in titles
        assert '无关曲目' not in titles


class TestGetAndDeleteSong:
    def test_get_song_detail(self, client):
        created = _post(client, title='详情曲目').json()['song']
        resp = client.get(f"/api/v1/songs/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()['song']['metadata']['title'] == '详情曲目'

    def test_get_missing_returns_404(self, client):
        resp = client.get('/api/v1/songs/not-exist')
        assert resp.status_code == 404

    def test_delete_song_then_404(self, client):
        created = _post(client, title='待删除曲目').json()['song']
        resp = client.delete(f"/api/v1/songs/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()['deleted'] is True
        assert client.get(f"/api/v1/songs/{created['id']}").status_code == 404

    def test_delete_missing_returns_404(self, client):
        assert client.delete('/api/v1/songs/not-exist').status_code == 404
