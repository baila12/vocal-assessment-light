"""AudioService._preprocess_for_scoring 混合检测 — P2-12a HPSS 去重

混合检测只需要 HPSS 谐波能量比 + _detect_mixed_audio 投票,
不应再调用全量 LibrosaAcousticExtractor.extract —— 该全量计算
(HNR/CPP/spectral_tilt/voicing) 随后由 DDD extract_all 对同一音频
重复执行 (审查性能专项: "HPSS 重复计算" 的 legacy 侧)。
"""

import types

import numpy as np

from services.audio_service import AudioService
from backend.domain.audio.acoustic_feature_extractor import LibrosaAcousticExtractor


class TestMixedAudioDetectionMinimalHpss:
    """P2-12a: 混合检测走最小 HPSS 路径, 不跑全量 extract"""

    def test_preprocess_for_scoring_skips_full_extract(self, monkeypatch):
        """spy: 混合检测只走 _compute_hpss + _detect_mixed_audio, 不调用全量 extract"""
        calls: list[str] = []

        def spy_extract(self, y, sr, **kw):
            calls.append("extract")
            return types.SimpleNamespace(is_mixed_audio=False, mixed_audio_confidence=0.1)

        monkeypatch.setattr(LibrosaAcousticExtractor, "extract", spy_extract)
        monkeypatch.setattr(
            LibrosaAcousticExtractor, "_compute_hpss",
            lambda y: (y, 0.9),
        )
        monkeypatch.setattr(
            LibrosaAcousticExtractor, "_detect_mixed_audio",
            lambda y, sr, ratio: (False, 0.1),
        )

        svc = AudioService()
        y = (np.random.RandomState(0).rand(16000) * 0.1).astype(np.float32)
        result = svc._preprocess_for_scoring("fake.wav", y, 16000, quick_mode=False)

        assert calls == [], \
            f"混合检测不应调用全量 extract (HPSS/HNR/CPP/voicing 白算), 实际 {calls}"
        assert result[4] is False  # is_mixed 透传自 _detect_mixed_audio
        assert result[5] == 0.1  # mixed_confidence 透传

    def test_preprocess_for_scoring_real_path_no_separation(self):
        """真实路径: 随机噪声 (纯人声/无伴奏) → 不触发 Demucs 分离 (不费 CPU)"""
        svc = AudioService()
        y = (np.random.RandomState(1).rand(16000) * 0.1).astype(np.float32)
        result = svc._preprocess_for_scoring("fake.wav", y, 16000, quick_mode=False)
        # (audio, sr, vocals_path, used_separation, is_mixed, confidence)
        assert result[3] is False  # used_separation=False (未触发 Demucs)
        assert result[2] is None  # vocals_path=None
