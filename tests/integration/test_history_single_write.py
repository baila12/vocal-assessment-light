"""
P2-15 Phase 0b — 历史双写 bug 回归测试

问题: audio_analysis.py import 时注册的 EventBus 订阅者 (HistoryEventSubscriber)
每次评分自动写"最小记录"(无 analysis_id/filename), 路由 _save_history 再写"完整记录"。
save() 无去重 → 每次上传产生 2 条记录, 垃圾记录挤占 HISTORY_MAX_RECORDS 槽位,
淘汰完整历史。实测 web_history.json: 50 条中 32 条为无 analysis_id 垃圾记录。

契约: 每次上传只写 1 条完整历史记录 (含 analysis_id/filename/filepath)。
修复: 移除 audio_analysis 的 EventBus 历史自动保存订阅 — 历史由路由 _save_history 单一负责。
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

import json
import pytest
from fastapi.testclient import TestClient

AUDIO_FILE = "tests/test_data/audio/vocal/vocals.wav"


@pytest.fixture(scope="module")
def client():
    from backend.main import create_app
    app = create_app()
    with TestClient(app) as c:
        yield c


def _read_records(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _point_history_at(client, tmp_path, monkeypatch):
    """路由 get_history_repo 指向临时历史文件 (FastAPI dependency_overrides 覆盖 DI)"""
    from repositories import JsonHistoryRepository
    from backend.interfaces.api import deps

    def _temp_repo():
        return JsonHistoryRepository(tmp_path / "history.json", 50, upload_dir=tmp_path)

    app = client.app
    overrides = {deps.get_history_repo: _temp_repo}
    app.dependency_overrides.update(overrides)
    monkeypatch.setattr(app, "dependency_overrides", app.dependency_overrides)


def _do_upload(client):
    with open(AUDIO_FILE, "rb") as f:
        return client.post(
            "/api/v1/upload",
            files={"file": ("vocals.wav", f, "audio/wav")},
            data={"mode": "quick"},
        )


def test_audio_analysis_has_no_event_bus_history_autosave():
    """P2-15: EventBus 历史自动保存订阅已从 audio_analysis 移除 (双写之源)

    RED (修复前): audio_analysis import 时构造 _history_repo +
    HistoryEventSubscriber 订阅 ScoreCalculated 事件 → 每次评分自动写垃圾记录。
    GREEN (修复后): 该订阅不存在, 历史由路由 _save_history 单一负责。
    """
    import api.business.audio_analysis as aa

    assert not hasattr(aa, "_history_repo"), "EventBus 历史自动保存订阅应已移除"
    assert not hasattr(aa, "history_subscriber"), "EventBus 历史订阅者应已移除"


def test_upload_writes_single_history_record(client, monkeypatch, tmp_path):
    """每次上传只写 1 条历史记录 (回归: EventBus 自动保存 + 路由保存 = 2 条)"""
    _point_history_at(client, tmp_path, monkeypatch)

    resp = _do_upload(client)
    assert resp.status_code == 200

    records = _read_records(tmp_path / "history.json")
    assert len(records) == 1, f"每次上传应仅 1 条历史, 实际 {len(records)}"


def test_history_record_has_full_fields(client, monkeypatch, tmp_path):
    """历史记录必须含完整字段 (analysis_id/filename/filepath) — 完整记录非垃圾最小记录"""
    _point_history_at(client, tmp_path, monkeypatch)

    resp = _do_upload(client)
    assert resp.status_code == 200

    records = _read_records(tmp_path / "history.json")
    assert len(records) == 1
    rec = records[0]
    assert rec.get("analysis_id"), "记录缺少 analysis_id (垃圾自动保存记录特征)"
    assert rec.get("filename"), "记录缺少 filename"
    assert rec.get("filepath"), "记录缺少 filepath"
    assert rec.get("total_score") is not None
    assert rec.get("scores")
    assert rec.get("level")
