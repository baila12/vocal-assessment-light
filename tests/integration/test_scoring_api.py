"""评分权重配置 API 集成测试 — v7.11 (scoring-config.feature)

GET  /api/v1/scoring/presets       — 默认权重 + 4 风格预设
POST /api/v1/scoring/apply-weights — 维度分数 + 权重 → 总分/等级
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope='module')
def client() -> TestClient:
    from backend.main import create_app
    app = create_app()
    with TestClient(app) as c:
        yield c


SCORES = {
    "pitch": 90.0, "rhythm": 50.0, "breath": 70.0,
    "technique": 70.0, "muscle": 70.0, "artistry": 70.0,
}


class TestScoringPresets:
    def test_presets_returns_default_and_four_styles(self, client):
        resp = client.get('/api/v1/scoring/presets')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert data['default']['name'] == 'default'
        names = [p['name'] for p in data['presets']]
        assert names == ['pop', 'bel_canto', 'ethnic', 'rap']

    def test_presets_each_sum_to_100(self, client):
        data = client.get('/api/v1/scoring/presets').json()['data']
        all_presets = [data['default']] + data['presets']
        for p in all_presets:
            total = sum(p['weights'].values())
            assert abs(total - 1.0) < 1e-9, f"{p['name']} 权重总和 {total} != 100%"

    def test_presets_include_labels(self, client):
        data = client.get('/api/v1/scoring/presets').json()['data']
        labels = {p['name']: p['label'] for p in data['presets']}
        assert labels == {'pop': '流行', 'bel_canto': '美声', 'ethnic': '民族', 'rap': '说唱'}

    def test_default_preset_is_pop(self, client):
        data = client.get('/api/v1/scoring/presets').json()['data']
        assert data['default_preset'] == 'pop'


class TestApplyWeights:
    def test_apply_default_weights(self, client):
        resp = client.post('/api/v1/scoring/apply-weights', json={
            'dimension_scores': SCORES,
        })
        assert resp.status_code == 200, resp.text
        data = resp.json()['data']
        assert data['applied_preset'] == 'default'
        # 0.13*90 + 0.12*50 + 0.22*70 + 0.25*70 + 0.15*70 + 0.13*70
        expected = 0.13*90 + 0.12*50 + 0.22*70 + 0.25*70 + 0.15*70 + 0.13*70
        assert data['total_score'] == round(expected, 1)
        assert data['level']

    def test_apply_preset_rap_pulls_toward_rhythm(self, client):
        resp = client.post('/api/v1/scoring/apply-weights', json={
            'dimension_scores': SCORES,
            'preset': 'rap',
        })
        assert resp.status_code == 200
        data = resp.json()['data']
        assert data['applied_preset'] == 'rap'
        default_total = 0.13*90 + 0.12*50 + 0.22*70 + 0.25*70 + 0.15*70 + 0.13*70
        assert data['total_score'] < round(default_total, 1)  # 低 rhythm 拉低总分

    def test_apply_custom_weights(self, client):
        # pitch 0.5 (单维上限) + 其余 0.1 → 合法权重 (总和 1.0)
        weights = {"pitch": 0.5, "rhythm": 0.1, "breath": 0.1,
                   "technique": 0.1, "muscle": 0.1, "artistry": 0.1}
        resp = client.post('/api/v1/scoring/apply-weights', json={
            'dimension_scores': SCORES,
            'weights': weights,
        })
        assert resp.status_code == 200
        # 0.5*90 + 0.1*(50+70+70+70+70) = 45 + 33 = 78
        assert resp.json()['data']['total_score'] == 78.0

    def test_apply_rejects_single_dim_over_50(self, client):
        bad = {"pitch": 1.0, "rhythm": 0.0, "breath": 0.0,
               "technique": 0.0, "muscle": 0.0, "artistry": 0.0}
        resp = client.post('/api/v1/scoring/apply-weights', json={
            'dimension_scores': SCORES, 'weights': bad,
        })
        assert resp.status_code == 400
        assert '50%' in resp.json()['detail']

    def test_apply_weights_validates_sum(self, client):
        bad = {"pitch": 0.3, "rhythm": 0.3, "breath": 0.25,
               "technique": 0.2, "muscle": 0.0, "artistry": 0.0}
        resp = client.post('/api/v1/scoring/apply-weights', json={
            'dimension_scores': SCORES, 'weights': bad,
        })
        assert resp.status_code == 400
        assert '100%' in resp.json()['detail']

    def test_apply_rejects_preset_and_weights_together(self, client):
        resp = client.post('/api/v1/scoring/apply-weights', json={
            'dimension_scores': SCORES,
            'preset': 'pop',
            'weights': {"pitch": 1.0, "rhythm": 0.0, "breath": 0.0,
                        "technique": 0.0, "muscle": 0.0, "artistry": 0.0},
        })
        assert resp.status_code == 400

    def test_apply_rejects_unknown_preset(self, client):
        resp = client.post('/api/v1/scoring/apply-weights', json={
            'dimension_scores': SCORES, 'preset': 'jazz',
        })
        assert resp.status_code == 400

    def test_apply_rejects_missing_dimension_scores(self, client):
        resp = client.post('/api/v1/scoring/apply-weights', json={
            'dimension_scores': {'pitch': 80, 'rhythm': 80},
        })
        assert resp.status_code == 400

    def test_apply_timbre_adjustment_clamped(self, client):
        # timbre +10 → 夹取到 +3
        resp = client.post('/api/v1/scoring/apply-weights', json={
            'dimension_scores': SCORES, 'timbre_adjustment': 10.0,
        })
        default_total = 0.13*90 + 0.12*50 + 0.22*70 + 0.25*70 + 0.15*70 + 0.13*70
        assert resp.json()['data']['total_score'] == round(default_total + 3.0, 1)

    def test_apply_returns_weighted_dimensions(self, client):
        resp = client.post('/api/v1/scoring/apply-weights', json={
            'dimension_scores': SCORES, 'preset': 'rap',
        })
        data = resp.json()['data']
        assert 'weighted_dimensions' in data
        assert set(data['weighted_dimensions'].keys()) == {
            'pitch', 'rhythm', 'breath', 'technique', 'muscle', 'artistry'
        }
        assert data['weighted_dimensions']['rhythm'] == round(50 * 0.30, 1)
