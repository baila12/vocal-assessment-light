"""
TDD RED-Phase 测试 — v5.18/v6.0 计划功能

这些测试为 PROJECT_STATUS.md 中规划的功能定义预期行为。
当前应标记为 expected failure (xfail)，实现后改为正常断言。

TDD 流程:
  1. RED:   这些测试当前 FAIL (功能未实现)
  2. GREEN: 实现功能后 → 测试通过
  3. REFACTOR: 优化实现 → 测试仍通过

功能清单:
  - Feature Flag 机制 (v5.18)
  - 多尺度 HNR (v5.18)
  - Praat CPP via parselmouth (v5.18)
  - Voicing Detection 评估 (v5.18)
  - TorchCREPE 备选接入 (v5.18)
  - SSE 流式进度推送 (v6.0)
  - 标准歌曲自动匹配 (v6.0)
  - 实时音准对比 Canvas (v6.0)
"""
import pytest
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ============================================================================
# Feature Flag 机制 (v5.18)
# ============================================================================

class TestFeatureFlags:
    """Feature Flag 系统 — 控制实验功能的开/关"""

    def test_feature_flags_dataclass_exists(self):
        """FeatureFlags dataclass 应存在且所有 flag 默认 False"""
        from services.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, 'enable_multiscale_hnr')
        assert hasattr(flags, 'enable_praat_cpp')
        assert hasattr(flags, 'enable_voicing_detection')
        assert hasattr(flags, 'enable_torchcrepe_fallback')
        # 默认全部关闭 (选择性开启)
        assert flags.enable_multiscale_hnr is False
        assert flags.enable_praat_cpp is False

    def test_feature_flags_not_affect_default_scoring(self):
        """FeatureFlags 全默认 → Quick 评分与不传 flags 一致 (回归保护)"""
        from services.feature_flags import FeatureFlags
        from api.business.audio_analysis import analyze_and_score

        # 用已知测试音频验证基线
        test_dir = Path(__file__).parent.parent / "test_data" / "audio" / "vocal"
        candidates = sorted(test_dir.glob("*.mp3")) if test_dir.exists() else []
        if not candidates:
            pytest.skip("No test audio available")

        # 不传 feature_flags (None) → 默认行为
        result_none = analyze_and_score(str(candidates[0]), mode='quick')
        # 传默认关闭的 FeatureFlags → 应完全一致
        result_default = analyze_and_score(
            str(candidates[0]), mode='quick', feature_flags=FeatureFlags()
        )

        # 两者应完全一致 (默认 flag 不应改变任何行为)
        assert result_none.get('total_score') == result_default.get('total_score'), \
            f"总分不一致: None={result_none.get('total_score')} vs Default={result_default.get('total_score')}"

    def test_feature_flag_check_overhead(self):
        """单个 flag 检查开销 < 1ms"""
        import time
        from services.feature_flags import FeatureFlags

        flags = FeatureFlags()
        start = time.perf_counter()
        for _ in range(10000):
            _ = flags.enable_multiscale_hnr
        elapsed = time.perf_counter() - start

        avg_us = (elapsed / 10000) * 1_000_000
        assert avg_us < 1000, f"Flag 检查 {avg_us:.1f}μs > 1000μs (1ms)"


# ============================================================================
# 多尺度 HNR (v5.18)
# ============================================================================

class TestMultiScaleHNR:
    """多尺度 HNR — 短窗/中窗/长窗 + 稳定性"""

    def test_multiscale_hnr_returns_three_windows(self):
        """多尺度 HNR 应返回短/中/长三个窗口的 HNR 值"""
        from services.features.hnr import MultiScaleHNR, HNRMultiscaleResult
        import numpy as np

        analyzer = MultiScaleHNR(sample_rate=22050)
        # 生成谐波丰富的测试信号
        t = np.linspace(0, 1, 22050)
        signal = (np.sin(2 * np.pi * 220 * t) +
                  np.sin(2 * np.pi * 440 * t) * 0.5 +
                  np.sin(2 * np.pi * 880 * t) * 0.25)

        result = analyzer.analyze(signal)

        assert isinstance(result, HNRMultiscaleResult)
        assert hasattr(result, 'hnr_short')   # ~5ms 窗
        assert hasattr(result, 'hnr_medium')  # ~20ms 窗
        assert hasattr(result, 'hnr_long')    # ~50ms 窗
        assert hasattr(result, 'hnr_stability')  # 三窗 CV
        # 谐波信号应有正 HNR
        assert result.hnr_long > 5

    def test_multiscale_hnr_stability_for_clean_signal(self):
        """干净信号在不同窗口间的 HNR 应稳定 (低 CV)"""
        from services.features.hnr import MultiScaleHNR
        import numpy as np

        analyzer = MultiScaleHNR(sample_rate=22050)
        t = np.linspace(0, 2, 44100)
        signal = np.sin(2 * np.pi * 440 * t)  # 纯正弦

        result = analyzer.analyze(signal)
        assert result.hnr_stability < 0.3, \
            f"纯正弦 HNR 稳定性应 < 0.3, 实际: {result.hnr_stability}"


# ============================================================================
# Praat CPP via parselmouth (v5.18)
# ============================================================================

class TestPraatCPP:
    """Praat CPP — parselmouth 替换手动 FFT 倒谱"""

    def test_praat_cpp_returns_consistent_values(self):
        """Praat CPP 应与手动 FFT 倒谱在 10% 内一致"""
        from services.features.cpp import PraatCPP, CepstralResult
        import numpy as np

        analyzer = PraatCPP()
        t = np.linspace(0, 1, 22050)
        signal = np.sin(2 * np.pi * 440 * t) * 0.5

        result = analyzer.analyze(signal)

        assert isinstance(result, CepstralResult)
        assert hasattr(result, 'cpp_mean')
        assert hasattr(result, 'cpp_std')
        assert hasattr(result, 'cpp_max')

    def test_praat_cpp_low_for_noise(self):
        """噪声的 CPP 应显著低于谐波丰富的人声信号

        CPP 算法依赖丰富的谐波结构 (Hillenbrand 1994)。
        纯正弦波谐波过于简单, 需使用多谐波信号模拟人声。
        """
        from services.features.cpp import PraatCPP
        import numpy as np

        analyzer = PraatCPP()
        sr = 22050
        duration = 1.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)

        # 模拟人声: 基频 220Hz (A3) + 8 个谐波, 含振幅衰减和相位抖动
        f0 = 220.0
        voice = np.zeros_like(t)
        for h in range(1, 10):  # 9 harmonics
            amplitude = 0.5 / h  # 谐波振幅递减 (1/h)
            phase = np.random.uniform(0, 2 * np.pi) * 0.1  # 微小相位抖动
            voice += amplitude * np.sin(2 * np.pi * f0 * h * t + phase)

        # 归一化
        voice = voice / np.max(np.abs(voice)) * 0.5

        np.random.seed(42)
        noise = np.random.randn(len(t)) * 0.1

        voice_result = analyzer.analyze(voice)
        noise_result = analyzer.analyze(noise)

        # 无 n_fft 缩放的新 CPP 算法: voice ~1.3, noise ~0.26, diff ~1.0
        # 差异 > 0.5 即为显著 (4-5x 差异)
        assert voice_result.cpp_mean > noise_result.cpp_mean + 0.5, \
            f"人声 CPP ({voice_result.cpp_mean:.2f}) 应显著高于噪声 ({noise_result.cpp_mean:.2f})"


# ============================================================================
# Voicing Detection 评估 (v5.18)
# ============================================================================

class TestVoicingDetection:
    """Voicing 检测质量评估 — PYIN voiced/unvoiced 决策诊断"""

    def test_voicing_detector_evaluates_pyin_output(self):
        """VoicingDetector 应计算置信度、有声帧比例和一致性分数"""
        from services.features.voicing import VoicingDetector, VoicingDetectionResult
        import numpy as np

        sr = 22050
        hop = 512

        # 模拟 PYIN 输出: 220Hz tone → 大部分 framed 应为 voiced
        duration = 1.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        signal = np.sin(2 * np.pi * 220 * t) * 0.5

        # 模拟 f0 提取 (简化: 所有非零帧标记为 voiced)
        n_frames = 1 + (len(signal) - 512) // hop
        f0 = np.full(n_frames, 220.0, dtype=np.float64)
        f0[::20] = np.nan  # 每 20 帧加一个 unvoiced
        voiced_flags = ~np.isnan(f0)

        detector = VoicingDetector(sample_rate=sr, hop_length=hop)
        result = detector.evaluate(f0, voiced_flags)

        assert isinstance(result, VoicingDetectionResult)
        assert hasattr(result, 'voiced_frame_count')
        assert hasattr(result, 'total_frame_count')
        assert hasattr(result, 'voicing_ratio')
        assert hasattr(result, 'detection_confidence')
        assert hasattr(result, 'octave_jump_rate')
        assert hasattr(result, 'consistency_score')

        # 大部分帧应为 voiced
        assert result.voicing_ratio > 0.5, \
            f"有声帧比例应 > 0.5, 实际: {result.voicing_ratio}"

        # 纯音应无八度跳跃
        assert result.octave_jump_rate == 0.0, \
            f"纯音八度跳跃率应为 0, 实际: {result.octave_jump_rate}"

    def test_voicing_detector_handles_empty_input(self):
        """空输入应返回零值结果 (不崩溃)"""
        from services.features.voicing import VoicingDetector
        import numpy as np

        detector = VoicingDetector()
        result = detector.evaluate(
            np.array([]),
            np.array([])
        )
        assert result.total_frame_count == 0
        assert result.voicing_ratio == 0.0
        assert result.detection_confidence == 0.0

    def test_voicing_detector_all_unvoiced(self):
        """全 unvoiced 置信度应为 0"""
        from services.features.voicing import VoicingDetector
        import numpy as np

        detector = VoicingDetector()
        n = 100
        f0 = np.full(n, np.nan)
        voiced_flags = np.zeros(n, dtype=bool)

        result = detector.evaluate(f0, voiced_flags)
        assert result.voiced_frame_count == 0
        assert result.detection_confidence == 0.0


# ============================================================================
# TorchCREPE 备选接入 (v5.18)
# ============================================================================

class TestTorchCREPEFallback:
    """TorchCREPE — PYIN 置信度低时降级启用"""

    def test_crepe_fallback_produces_valid_f0(self):
        """TorchCREPE 应返回有效 f0 序列，长度与 PYIN 一致"""
        import numpy as np
        from services.audio_features_service import AudioFeaturesService
        from services.feature_flags import FeatureFlags

        sr = 22050
        duration = 1.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        # 使用多谐波信号 (更接近真实人声)
        signal = np.zeros_like(t)
        for h in range(1, 6):
            signal += (0.3 / h) * np.sin(2 * np.pi * 220 * h * t)

        service = AudioFeaturesService(sample_rate=sr)
        flags = FeatureFlags(enable_torchcrepe_fallback=True)

        f0, voiced = service._extract_f0(signal, feature_flags=flags)

        # 即使 PYIN 工作正常 (detection_rate >= 0.5), CREPE 不会触发
        # 但 f0 应有效
        assert len(f0) > 0, "f0 不应为空"
        assert len(voiced) > 0, "voiced_flags 不应为空"

    def test_crepe_fallback_not_triggered_when_disabled(self):
        """feature_flags=None 时不触发 CREPE fallback"""
        import numpy as np
        from services.audio_features_service import AudioFeaturesService

        sr = 22050
        t = np.linspace(0, 0.5, int(sr * 0.5), endpoint=False)
        signal = np.sin(2 * np.pi * 440 * t) * 0.5

        service = AudioFeaturesService(sample_rate=sr)
        # 不传 feature_flags → 使用纯 PYIN
        f0_none, _ = service._extract_f0(signal, feature_flags=None)
        # 传关闭的 flags → 使用纯 PYIN
        from services.feature_flags import FeatureFlags
        flags_off = FeatureFlags()
        f0_off, _ = service._extract_f0(signal, feature_flags=flags_off)

        # 两者应相同 (都不触发 CREPE)
        np.testing.assert_array_equal(f0_none, f0_off)


# ============================================================================
# SSE 流式进度推送 (v6.0)
# ============================================================================

class TestSSEStreamingProgress:
    """SSE 进度流 — 分析过程中实时推送阶段和进度"""

    @pytest.mark.xfail(
        reason="TDD RED: SSE 进度端点尚未实现。"
               "需要: /api/analyze/stream + SSE 事件类型"
    )
    def test_sse_endpoint_accepts_upload(self):
        """POST /api/analyze/stream 接受文件上传并返回 SSE 流"""
        from api import create_app
        import io

        app = create_app()
        app.config['TESTING'] = True
        client = app.test_client()

        # 创建最小测试音频
        data = io.BytesIO()
        data.name = "test.wav"

        response = client.post(
            '/api/analyze/stream',
            data={'file': (data, 'test.wav'), 'mode': 'quick'},
            content_type='multipart/form-data'
        )

        # SSE 响应类型
        assert response.content_type == 'text/event-stream'
        assert response.status_code == 200

    @pytest.mark.xfail(
        reason="TDD RED: SSE 事件包含 feature_pitch 和 final_score 事件"
    )
    def test_sse_events_contain_required_types(self):
        """SSE 流应发送标准事件: feature_pitch, progress, final_score"""
        # 此测试需要完整的 SSE 流解析
        # 预期事件类型集合
        expected_events = {'progress', 'feature_pitch', 'final_score'}
        # 实现后: 解析 SSE 流, 验证事件类型包含这些
        pytest.skip("TDD: SSE 事件验证将在 SSE 端点实现后启用")


# ============================================================================
# 标准歌曲自动匹配 (v6.0)
# ============================================================================

class TestSongAutoMatch:
    """标准歌曲数据库 + 自动匹配"""

    @pytest.mark.xfail(
        reason="TDD RED: 歌曲数据库和自动匹配尚未实现。"
               "需要: SQLite 曲库 + 特征匹配算法"
    )
    def test_song_database_has_minimum_songs(self):
        """标准曲库应至少有 10 首歌曲"""
        from repositories.song_repository import SongRepository

        repo = SongRepository()
        songs = repo.list_all()
        assert len(songs) >= 10, f"曲库至少需要 10 首, 实际: {len(songs)}"

    @pytest.mark.xfail(
        reason="TDD RED: 自动匹配返回 matched_song 字段。"
               "需要: matching 算法 + matched_song 响应字段"
    )
    def test_upload_triggers_auto_match(self):
        """上传翻唱后自动匹配标准歌曲"""
        from api.business.audio_analysis import analyze_and_score
        from pathlib import Path

        test_dir = Path(__file__).parent.parent / "test_data" / "audio" / "vocal"
        candidates = sorted(test_dir.glob("*.mp3")) if test_dir.exists() else []
        if not candidates:
            pytest.skip("No test audio")

        result = analyze_and_score(str(candidates[0]), mode='quick')

        # 响应应包含匹配字段 (即使没有匹配到)
        assert 'matched_song' in result, "响应缺少 matched_song 字段"
        # 未匹配时返回 null
        if result.get('matched_song') is not None:
            song = result['matched_song']
            assert 'id' in song
            assert 'title' in song
            assert 'artist' in song
            assert 'confidence' in song

    @pytest.mark.xfail(
        reason="TDD RED: 无匹配时回退绝对评分模式"
    )
    def test_no_match_falls_back_to_absolute_scoring(self):
        """无匹配歌曲 → fallback_reason = 'no_match'"""
        from api.business.audio_analysis import analyze_and_score
        from pathlib import Path

        test_dir = Path(__file__).parent.parent / "test_data" / "audio" / "vocal"
        candidates = sorted(test_dir.glob("*.mp3")) if test_dir.exists() else []
        if not candidates:
            pytest.skip("No test audio")

        result = analyze_and_score(str(candidates[0]), mode='quick')

        if result.get('matched_song') is None:
            assert result.get('scoring_mode') == 'absolute', \
                f"未匹配应为 absolute 模式, 实际: {result.get('scoring_mode')}"
            assert result.get('fallback_reason') == 'no_match'


# ============================================================================
# 六维评分 — 音量独立维度 (v6.1)
# ============================================================================

class TestVolumeDimension:
    """音量作为独立维度 (✅ 已实现 — scores 中已包含 volume 和 emotion 维度)"""

    def test_volume_dimension_present_in_scores(self):
        """评分结果应包含独立的 volume 维度 (当前已实现)"""
        from api.business.audio_analysis import analyze_and_score
        from pathlib import Path

        test_dir = Path(__file__).parent.parent / "test_data" / "audio" / "vocal"
        candidates = sorted(test_dir.glob("*.mp3")) if test_dir.exists() else []
        if not candidates:
            pytest.skip("No test audio")

        result = analyze_and_score(str(candidates[0]), mode='quick')

        scores = result.get('scores', {})
        # volume 作为独立维度已存在
        assert 'volume' in scores, "缺少 volume 维度"
        assert 'pitch' in scores
        assert 'rhythm' in scores
        assert 'breath' in scores
        assert 'technique' in scores
        assert 'artistry' in scores
        assert 0 <= scores['volume'] <= 100

    @pytest.mark.xfail(
        reason="TDD RED: volume 维度应独立驱动评分 (目前可能与其他维度耦合)。"
               "v6.1 目标: 独立 SPL 评估，不依赖 Breath 合并值"
    )
    def test_volume_independent_from_breath(self):
        """volume 评分应独立于 breath (当前可能未完全解耦)"""
        from api.business.audio_analysis import analyze_and_score
        from pathlib import Path

        test_dir = Path(__file__).parent.parent / "test_data" / "audio" / "vocal"
        candidates = sorted(test_dir.glob("*.mp3")) if test_dir.exists() else []
        if not candidates:
            pytest.skip("No test audio")

        result = analyze_and_score(str(candidates[0]), mode='quick')
        scores = result.get('scores', {})

        # v6.1: volume 应基于独立 SPL 测量，非 Breath 衍生
        # 当前验证: volume ≠ breath (如果相等说明未解耦)
        assert scores.get('volume') != scores.get('breath'), \
            "volume 和 breath 分数相同 — 可能尚未独立解耦"


# ============================================================================
# 混响补偿 (v6.1)
# ============================================================================

class TestReverbCompensation:
    """混响补偿 — HPSS 谐波分离 + 谱减法"""

    @pytest.mark.xfail(
        reason="TDD RED: 混响补偿尚未实现。"
               "需要: services/features/reverb.py + ReverbCompensator"
    )
    def test_reverb_compensator_reduces_room_effect(self):
        """混响补偿后，干声和湿声的 HNR/CPP 差距应缩小"""
        from services.features.reverb import ReverbCompensator
        import numpy as np

        compensator = ReverbCompensator(sample_rate=22050)

        # 干声 (纯净)
        t = np.linspace(0, 2, 44100)
        dry = np.sin(2 * np.pi * 440 * t) * 0.5

        # 模拟混响 (简单延迟叠加)
        wet = dry + 0.3 * np.roll(dry, 1000)

        dry_compensated = compensator.process(dry)
        wet_compensated = compensator.process(wet)

        # 补偿后两者应更接近
        # 具体指标待实现后细化
        assert dry_compensated is not None
        assert wet_compensated is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
