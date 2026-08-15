"""
ONNX 模型可加载性 + 推理健全性测试

背景 (v7.19 整理):
- 原 tests/tools/test_onnx_models.py 是开发脚本: 测试函数用 `return False` 而非 assert,
  模型加载失败也静默"通过" (无声失败); 且模块级 `sys.stdout = io.TextIOWrapper(...)`
  破坏 pytest capture (实测导致整个会话 "ValueError: I/O operation on closed file")。
- 重写为真实断言测试, 迁入 tests/extended/ (需真实 ONNX 模型, 属扩展/集成级)。
- 这些模型仍被生产路径使用: api/business/audio_analysis.analyze_and_score
  → audio_service.analyze → audio_dl_helpers (VoiceQualityDetector 人声检测)。
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("onnxruntime")

from onnxruntime import InferenceSession  # noqa: E402

PROJECT_ROOT = Path(__file__).parent.parent.parent

# 生产路径引用的模型 (services/audio_dl_helpers.py)
SILERO_VAD_PATH = PROJECT_ROOT / "models" / "voice_quality" / "silero_vad.onnx"
STYLE_MODEL_PATH = PROJECT_ROOT / "models" / "style_classifier" / "model_quantized.onnx"
STYLE_CONFIG_PATH = PROJECT_ROOT / "models" / "style_classifier" / "config.json"

pytestmark = pytest.mark.slow


def _session(path: Path) -> InferenceSession:
    assert path.exists(), f"模型文件缺失: {path} (生产代码 audio_dl_helpers 依赖它)"
    return InferenceSession(str(path), providers=["CPUExecutionProvider"])


class TestSileroVAD:
    """Silero VAD (人声检测) 模型 — 生产路径 VoiceQualityDetector 核心"""

    def test_model_file_exists(self):
        assert SILERO_VAD_PATH.exists(), f"缺失: {SILERO_VAD_PATH}"

    def test_inference_outputs_voice_probability(self):
        """推理输出应为 [0,1] 概率 — 原测试 return False 静默通过, 此处真实断言"""
        session = _session(SILERO_VAD_PATH)

        sr = 16000
        chunk = np.random.randn(512).astype(np.float32)
        state = np.zeros((2, 1, 128), dtype=np.float32)

        out, state_new = session.run(
            ["output", "stateN"],
            {
                "input": chunk[np.newaxis, :],  # [1, 512]
                "state": state,
                "sr": np.array(sr, dtype=np.int64),
            },
        )

        # 概率应在 [0,1]; 状态张量应为有限值 (无 NaN/Inf — 防 audiofeat 类垃圾值)
        prob = float(out[0][0])
        assert 0.0 <= prob <= 1.0, f"VAD 概率越界: {prob}"
        assert np.isfinite(state_new).all(), "VAD state 含非有限值"

    def test_empty_chunk_does_not_crash(self):
        """边界: 短输入不抛异常 (生产处理静音/短音频时依赖容错)"""
        session = _session(SILERO_VAD_PATH)
        chunk = np.zeros(512, dtype=np.float32)
        state = np.zeros((2, 1, 128), dtype=np.float32)
        out, _ = session.run(
            ["output", "stateN"],
            {
                "input": chunk[np.newaxis, :],
                "state": state,
                "sr": np.array(16000, dtype=np.int64),
            },
        )
        assert out is not None


class TestStyleClassifier:
    """AST 音乐风格分类模型 — 生产 SingingStyleClassifier"""

    def test_model_and_config_exist(self):
        assert STYLE_MODEL_PATH.exists(), f"缺失: {STYLE_MODEL_PATH}"
        assert STYLE_CONFIG_PATH.exists(), f"缺失: {STYLE_CONFIG_PATH}"

    def test_inference_logits_sane(self):
        """logits 形状 [1,10] + softmax 概率和 = 1 — 防模型输出维度漂移"""
        session = _session(STYLE_MODEL_PATH)
        test_input = np.random.randn(1, 1024, 128).astype(np.float32)

        logits = session.run(["logits"], {"input_values": test_input})[0][0]
        assert logits.shape == (10,), f"logits 形状异常: {logits.shape}"

        exp = np.exp(logits - np.max(logits))
        probs = exp / np.sum(exp)
        assert np.isclose(np.sum(probs), 1.0, atol=1e-4), "softmax 概率和 != 1"

    def test_config_has_10_labels(self):
        """config id2label 应有 10 个标签 — 与模型输出维度一致"""
        with open(STYLE_CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        id2label = config.get("id2label", {})
        assert len(id2label) == 10, f"标签数 {len(id2label)} != 10 (模型 logits 10 维)"


class TestDLServiceWrappers:
    """dl_services 封装类 — 生产 analyze_and_score 实际调用它们"""

    def test_voice_quality_detector_available(self):
        """VAD 检测器应可初始化 (librosa 基础, 恒可用)"""
        from services.dl_services.voice_quality_detector import VoiceQualityDetector

        detector = VoiceQualityDetector()
        assert detector._model_available is True

    def test_singing_style_classifier_loads_model(self):
        """风格分类器应成功加载 ONNX 模型 — 原测试未断言 _model_available
        (模型缺失时它为 False 但测试仍'通过', 属无声失败)"""
        from services.dl_services.singing_style_classifier import SingingStyleClassifier

        classifier = SingingStyleClassifier()
        assert classifier._model_available is True, \
            "SingingStyleClassifier 未能加载模型 (models/style_classifier/ 缺失或损坏)"
        assert len(classifier._id2label) == 10
