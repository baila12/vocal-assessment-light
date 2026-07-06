"""
TDD RED-Phase 测试 — 计划中但尚未实现的功能

这些测试为 PROJECT_STATUS.md 中规划的功能定义预期行为。
标记为 xfail (expected failure), 实现后改为正常断言。

TDD 流程:
  1. RED:   这些测试当前 FAIL (功能未实现)
  2. GREEN: 实现功能后 → 测试通过
  3. REFACTOR: 优化实现 → 测试仍通过

已完成的模块 (已拆分到独立文件):
  - test_acoustic_algorithms.py: Feature Flag + HNR/CPP/Voicing/CREPE (v5.18 GREEN)
  - test_mixed_audio.py: 混合音频检测 + 混响补偿 (v6.0 GREEN)
  - test_scoring_v6_1.py: 评分区分度修复 (v6.1 GREEN)

当前文件 (RED phase):
  - 🔴 SSE 流式进度推送
  - 🔴 标准歌曲自动匹配
"""
import pytest


# ═══════════════════════════════════════════════════════════════════════════
# SSE 流式进度推送 (v6.0 → v6.1 RED)
# ═══════════════════════════════════════════════════════════════════════════

class TestSSEStreamingProgress:
    """SSE 进度流 — 分析过程中实时推送阶段和进度"""

    @pytest.mark.xfail(
        reason="TDD RED: SSE 进度端点尚未实现。需要: /api/analyze/stream + SSE 事件类型"
    )
    def test_sse_endpoint_accepts_upload(self):
        """POST /api/analyze/stream 接受文件上传并返回 SSE 流"""
        from api import create_app
        import io

        app = create_app()
        app.config['TESTING'] = True
        client = app.test_client()

        data = io.BytesIO()
        data.name = "test.wav"

        response = client.post(
            '/api/analyze/stream',
            data={'file': (data, 'test.wav'), 'mode': 'quick'},
            content_type='multipart/form-data'
        )

        assert response.content_type == 'text/event-stream'
        assert response.status_code == 200

    @pytest.mark.xfail(
        reason="TDD RED: SSE 事件包含 feature_pitch 和 final_score 事件"
    )
    def test_sse_events_contain_required_types(self):
        """SSE 流应发送标准事件: progress, feature_pitch, final_score"""
        pytest.skip("TDD: SSE 事件验证将在 SSE 端点实现后启用")


# ═══════════════════════════════════════════════════════════════════════════
# 标准歌曲自动匹配 (v6.1 RED)
# ═══════════════════════════════════════════════════════════════════════════

class TestSongAutoMatch:
    """标准歌曲数据库 + 自动匹配"""

    @pytest.mark.xfail(
        reason="TDD RED: 歌曲数据库和自动匹配尚未实现。需要: SQLite 曲库 + 特征匹配算法"
    )
    def test_song_database_has_minimum_songs(self):
        """标准曲库应至少有 10 首歌曲"""
        from repositories.song_repository import SongRepository

        repo = SongRepository()
        songs = repo.list_all()
        assert len(songs) >= 10, f"曲库至少需要 10 首, 实际: {len(songs)}"

    @pytest.mark.xfail(
        reason="TDD RED: 自动匹配返回 matched_song 字段。需要: matching 算法 + matched_song 响应字段"
    )
    def test_upload_triggers_auto_match(self, good_vocal_file):
        """上传翻唱后自动匹配标准歌曲"""
        if good_vocal_file is None:
            pytest.skip("No test audio")

        from api.business.audio_analysis import analyze_and_score
        result = analyze_and_score(str(good_vocal_file), mode='quick')

        assert 'matched_song' in result, "响应缺少 matched_song 字段"
        if result.get('matched_song') is not None:
            song = result['matched_song']
            assert 'id' in song
            assert 'title' in song
            assert 'confidence' in song

    @pytest.mark.xfail(
        reason="TDD RED: 无匹配时回退绝对评分模式"
    )
    def test_no_match_falls_back_to_absolute_scoring(self, good_vocal_file):
        """无匹配歌曲 → fallback_reason = 'no_match'"""
        if good_vocal_file is None:
            pytest.skip("No test audio")

        from api.business.audio_analysis import analyze_and_score
        result = analyze_and_score(str(good_vocal_file), mode='quick')

        if result.get('matched_song') is None:
            assert result.get('scoring_mode') == 'absolute'
            assert result.get('fallback_reason') == 'no_match'
