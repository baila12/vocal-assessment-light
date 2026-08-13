"""
P2-15 Phase 3 — calculate_ddd 逐维诊断契约

旧 calculate() (死路径) 经 _make_diagnosis 输出 pitch/rhythm/breath/technique/artistry 五个
*_diagnosis 键; 但唯一生产路径 calculate_ddd() 完全省略 → 前端诊断 block 恒空。
本测试断言 calculate_ddd 输出包含诊断键 (score/level/issues/suggestions 结构 +
pitch 的 mae_cents + rhythm 的 deviation_ratio 额外字段)。
"""

import numpy as np

from backend.application.assessment.ddd_feature_orchestrator import (
    DddFeatureExtractionOrchestrator,
)
from backend.application.assessment.scoring_orchestrator import ScoringOrchestrator


def _make_test_audio(duration_s=2.0, sr=22050, freq=440.0):
    """生成测试音频 (带谐波的人声仿真, 带音量包络)"""
    n = int(sr * duration_s)
    t = np.linspace(0, duration_s, n, endpoint=False)
    y = np.zeros(n, dtype=np.float64)
    for h in range(1, 6):
        y += (0.6 / h) * np.sin(2 * np.pi * freq * h * t)
    envelope = np.ones(n)
    attack = int(sr * 0.1)
    release = int(sr * 0.2)
    envelope[:attack] = np.linspace(0, 1, attack)
    envelope[-release:] = np.linspace(1, 0, release)
    y *= envelope
    y /= np.max(np.abs(y))
    return (y * 0.8).astype(np.float32), sr


def _make_f0_from_audio(y, sr, hop_length=256):
    import librosa
    f0, voiced_flag, _ = librosa.pyin(
        y.astype(np.float64), fmin=65.0, fmax=1047.0, sr=sr,
        hop_length=hop_length, fill_na=0.0,
    )
    return f0, voiced_flag.astype(bool)


def _calculate_ddd_result():
    """用合成音频走完整 DDD 提取 + 评分路径"""
    y, sr = _make_test_audio(duration_s=2.0)
    f0, voiced = _make_f0_from_audio(y, sr)

    extractor = DddFeatureExtractionOrchestrator()
    features = extractor.extract_all(y, sr, f0, voiced, is_clean_vocal=True)

    scoring = ScoringOrchestrator()
    return scoring.calculate_ddd(
        pitch=features.pitch, rhythm=features.rhythm,
        breath=features.breath, technique=features.technique,
        muscle=features.muscle, artistry=features.artistry,
        timbre=features.timbre,
    )


DIAGNOSIS_KEYS = ("pitch_diagnosis", "rhythm_diagnosis", "breath_diagnosis",
                  "technique_diagnosis", "artistry_diagnosis")


class TestCalculateDddDiagnosis:
    def test_all_five_diagnosis_keys_present(self):
        result = _calculate_ddd_result()
        for key in DIAGNOSIS_KEYS:
            assert key in result, f"calculate_ddd 输出应含 {key}"

    def test_diagnosis_has_required_structure(self):
        result = _calculate_ddd_result()
        for key in DIAGNOSIS_KEYS:
            d = result[key]
            assert isinstance(d, dict), f"{key} 应为 dict"
            assert "score" in d and isinstance(d["score"], (int, float))
            assert "level" in d and d["level"]
            assert "issues" in d and isinstance(d["issues"], list)
            assert "suggestions" in d and isinstance(d["suggestions"], list)

    def test_pitch_diagnosis_has_mae_cents(self):
        result = _calculate_ddd_result()
        assert "mae_cents" in result["pitch_diagnosis"], (
            f"pitch_diagnosis 应含 mae_cents, 实际 keys={list(result['pitch_diagnosis'].keys())}"
        )

    def test_rhythm_diagnosis_has_deviation_ratio(self):
        result = _calculate_ddd_result()
        assert "deviation_ratio" in result["rhythm_diagnosis"], (
            f"rhythm_diagnosis 应含 deviation_ratio, 实际 keys={list(result['rhythm_diagnosis'].keys())}"
        )

    def test_diagnosis_score_matches_dimension_score(self):
        result = _calculate_ddd_result()
        assert result["pitch_diagnosis"]["score"] == pytest.approx(result["pitch_score"], rel=1e-6)
        assert result["artistry_diagnosis"]["score"] == pytest.approx(result["artistry_score"], rel=1e-6)


import pytest  # noqa: E402  (pytest.approx 用于诊断分数一致断言)
