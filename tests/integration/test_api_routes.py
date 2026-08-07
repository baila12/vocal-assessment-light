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


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["version"] == "7.13.0"
        assert "gpu" in data

    def test_docs_accessible(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_openapi_json(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["info"]["title"] == "VAS v7.13"
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
