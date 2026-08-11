"""FastAPI 集成测试 — TestClient 验证所有端点"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

import json
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from backend.main import create_app
    app = create_app()
    with TestClient(app) as c:
        yield c


# v7.14 审查 TEST_GAP: 版本断言引用单一来源 APP_VERSION, 而非硬编码字符串
# (防止未来升版本后此处静默失配)
from backend.main import APP_VERSION


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["version"] == APP_VERSION
        assert "gpu" in data

    def test_docs_accessible(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_openapi_json(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["info"]["title"] == "VAS v7.14"
        # 验证路由已注册
        paths = list(data["paths"].keys())
        assert any("/api/v1/upload" in p for p in paths)
        assert any("/api/v1/history" in p for p in paths)
        assert any("/api/v1/audio" in p for p in paths)
        assert any("/api/v1/flags" in p for p in paths)


class TestFlagsEndpoint:
    """v7.8: GET /api/v1/flags 反映运行时配置"""

    def test_flags_returns_audiofeat_enabled(self, client):
        """audiofeat 通过桥接层应显示为启用 (修复返回类默认值 False 的问题)"""
        resp = client.get("/api/v1/flags")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        payload = data["data"]
        # 运行时维度开关 + audiofeat 增强 (v7.7 默认启用)
        assert payload["enhancements"]["audiofeat"] is True
        assert payload["enhancements"]["praat_voice_quality"] is True
        assert "pitch" in payload["dimensions"]
        # 设备/模型状态字段齐全
        assert "gpu" in payload
        assert "models" in payload
        assert "dimension_weights" in payload
        assert payload["dimension_weights"]["technique"] == 25


class TestHistoryEndpoints:
    def test_list_history(self, client):
        resp = client.get("/api/v1/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "history" in data
        assert "total" in data

    def test_get_nonexistent_record(self, client):
        resp = client.get("/api/v1/history/nonexistent")
        assert resp.status_code == 404

    def test_delete_nonexistent_record(self, client):
        resp = client.request("DELETE", "/api/v1/history/nonexistent")
        assert resp.status_code == 404

    def test_batch_delete_empty_ids(self, client):
        resp = client.request("DELETE", "/api/v1/history/batch",
                              content=json.dumps({"ids": []}),
                              headers={"Content-Type": "application/json"})
        assert resp.status_code == 400

    def test_get_test_files(self, client):
        resp = client.get("/api/v1/test-files")
        assert resp.status_code == 200


class TestAssessmentEndpoints:
    def test_upload_no_file(self, client):
        resp = client.post("/api/v1/upload")
        assert resp.status_code == 422  # FastAPI validation

    def test_analyze_missing_filepath(self, client):
        resp = client.post("/api/v1/analyze", json={})
        assert resp.status_code == 422

    def test_extract_pitch_no_file(self, client):
        resp = client.post("/api/v1/extract-pitch")
        assert resp.status_code == 400

    def test_extract_pitch_positive_loads_at_target_sr(self, client, monkeypatch, tmp_path):
        """P2-11 + T3: /extract-pitch 正向路径 — librosa.load 以 sr=16000 一步加载 (非 sr=None 两次重采样)

        同时填补 T3 缺口 (该端点此前只有 400 负向测试)。上传写入重定向到 tmp_path 防污染 uploads/。
        """
        import io
        import wave
        import librosa
        import numpy as np
        from config import Config

        monkeypatch.setattr(Config, "get_upload_path", lambda self, name: tmp_path / name)

        captured: dict = {}

        def spy_load(path, **kwargs):
            captured["sr"] = kwargs.get("sr")
            n = 16000
            t = np.linspace(0, 1, n, endpoint=False)
            return (np.sin(2 * np.pi * 440 * t) * 0.5).astype(np.float32), 16000

        monkeypatch.setattr(librosa, "load", spy_load)

        n = 16000
        t = np.linspace(0, 1, n, endpoint=False)
        samples = (np.sin(2 * np.pi * 440 * t) * 0.5 * 32767).astype(np.int16)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(16000)
            w.writeframes(samples.tobytes())

        resp = client.post(
            "/api/v1/extract-pitch",
            files={"file": ("user.wav", buf.getvalue(), "audio/wav")},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["sample_rate"] == 16000
        assert captured["sr"] == 16000, \
            f"load 应直接以 sr=16000 加载 (内存峰值 ~2.7x 来源), 实际 {captured['sr']}"

    def test_separate_missing_filepath(self, client):
        resp = client.post("/api/v1/separate", json={})
        assert resp.status_code == 422

    def test_report_missing_result(self, client):
        resp = client.post("/api/v1/report", json={})
        assert resp.status_code == 422

    def test_separate_models(self, client):
        resp = client.get("/api/v1/separate/models")
        assert resp.status_code == 200


class TestAudioEndpoint:
    def test_audio_no_file_param(self, client):
        resp = client.get("/api/v1/audio")
        assert resp.status_code == 422  # missing required query param

    def test_audio_invalid_path(self, client):
        resp = client.get("/api/v1/audio?file=../../etc/passwd")
        assert resp.status_code == 403


class TestSongsEndpoint:
    def test_list_songs(self, client):
        resp = client.get("/api/v1/songs")
        assert resp.status_code == 200

    def test_get_nonexistent_song(self, client):
        resp = client.get("/api/v1/songs/999")
        assert resp.status_code == 404
