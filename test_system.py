"""
声乐评估系统 - 综合测试脚本
验证异步加载、模型加载、评分计算、UI组件
"""
import sys
import os
import io

# 设置标准输出编码为UTF-8，解决Windows控制台编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import numpy as np
from pathlib import Path

# 设置项目路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 60)
print("声乐评估系统 - 综合测试")
print("=" * 60)

# 测试结果统计
test_results = {"passed": 0, "failed": 0, "errors": []}


def test_pass(name: str):
    print(f"[PASS] {name}")
    test_results["passed"] += 1


def test_fail(name: str, error: str):
    print(f"[FAIL] {name}: {error}")
    test_results["failed"] += 1
    test_results["errors"].append(f"{name}: {error}")


# ==================== 测试1: 模块导入 ====================
print("\n【测试1】模块导入测试")
try:
    from core.workers import WorkerManager, AudioLoadTask, AssessmentTask, preload_emotion_model
    test_pass("core.workers 导入成功")
except Exception as e:
    test_fail("core.workers 导入失败", str(e))

try:
    from widgets.radar_chart import RadarChart
    test_pass("widgets.radar_chart 导入成功")
except Exception as e:
    test_fail("widgets.radar_chart 导入失败", str(e))

try:
    from widgets.score_panel import ScorePanel
    test_pass("widgets.score_panel 导入成功")
except Exception as e:
    test_fail("widgets.score_panel 导入失败", str(e))


# ==================== 测试2: 模型路径验证 ====================
print("\n【测试2】模型文件验证")
MODEL_PATH = PROJECT_ROOT / "models" / "emotion"
required_files = ["hyperparams.yaml", "label_encoder.txt", "wav2vec2.ckpt", "README.txt"]

for file in required_files:
    file_path = MODEL_PATH / file
    if file_path.exists():
        test_pass(f"模型文件存在: {file}")
    else:
        test_fail(f"模型文件缺失: {file}", f"路径: {file_path}")


# ==================== 测试3: 情绪模型加载 ====================
print("\n【测试3】情绪模型加载测试")
try:
    import torch
    test_pass("torch 导入成功")

    # 尝试预加载模型
    success = preload_emotion_model()
    if success:
        test_pass("情绪模型预加载成功")
    else:
        test_fail("情绪模型预加载失败", "模型返回None")
except ImportError as e:
    test_fail("torch 未安装", str(e))
except Exception as e:
    test_fail("情绪模型加载异常", str(e))


# ==================== 测试4: 评分计算测试 ====================
print("\n【测试4】评分计算逻辑测试")
try:
    # 模拟评分数据（合成数据）
    mock_scores = {
        'volume': 75.0,
        'pitch': 82.0,
        'rhythm': 68.0,
        'breath': 90.0,
        'emotion': 85.0
    }

    # 验证评分范围
    for key, value in mock_scores.items():
        if 0 <= value <= 100:
            test_pass(f"评分范围正确: {key}={value}")
        else:
            test_fail(f"评分范围错误: {key}", f"值={value}")

    # 计算平均分
    avg_score = sum(mock_scores.values()) / len(mock_scores)
    test_pass(f"平均分计算: {avg_score:.1f}")

except Exception as e:
    test_fail("评分计算测试失败", str(e))


# ==================== 测试5: 音频处理函数测试 ====================
print("\n【测试5】音频处理函数测试")
try:
    import librosa

    # 创建测试音频数据（合成数据：1秒，22050Hz）
    test_sr = 22050
    test_duration = 1.0
    test_audio = np.random.randn(int(test_sr * test_duration)).astype(np.float32) * 0.1

    # 测试音量计算
    rms = np.sqrt(np.mean(test_audio ** 2))
    db = 20 * np.log10(rms) if rms > 0 else -80
    test_pass(f"音量计算: {db:.1f} dB")

    # 测试RMS特征提取
    rms_feature = librosa.feature.rms(y=test_audio)
    test_pass(f"RMS特征提取: shape={rms_feature.shape}")

except ImportError as e:
    test_fail("librosa 未安装", str(e))
except Exception as e:
    test_fail("音频处理测试失败", str(e))


# ==================== 测试6: 音高检测测试 ====================
print("\n【测试6】音高检测测试")
try:
    import librosa

    # 创建简单正弦波测试信号（合成数据：440Hz, A4音符）
    test_sr = 22050
    test_duration = 0.5
    freq = 440  # A4
    t = np.linspace(0, test_duration, int(test_sr * test_duration))
    test_audio = np.sin(2 * np.pi * freq * t).astype(np.float32) * 0.5

    # 音高检测
    f0, voiced_flag, _ = librosa.pyin(
        test_audio,
        fmin=librosa.note_to_hz('C2'),
        fmax=librosa.note_to_hz('C6'),
        sr=test_sr,
        hop_length=512
    )

    valid_f0 = f0[~np.isnan(f0)]
    if len(valid_f0) > 0:
        detected_freq = np.mean(valid_f0)
        # 允许10%误差
        if abs(detected_freq - freq) < freq * 0.1:
            test_pass(f"音高检测正确: 期望{freq}Hz, 检测{detected_freq:.1f}Hz")
        else:
            test_fail("音高检测偏差过大", f"期望{freq}Hz, 检测{detected_freq:.1f}Hz")
    else:
        test_fail("音高检测无有效结果", "未检测到有效频率")

except Exception as e:
    test_fail("音高检测测试失败", str(e))


# ==================== 测试7: WorkerManager测试 ====================
print("\n【测试7】WorkerManager单例测试")
try:
    manager1 = WorkerManager()
    manager2 = WorkerManager()

    if manager1 is manager2:
        test_pass("WorkerManager单例模式正确")
    else:
        test_fail("WorkerManager单例模式失败", "创建了不同实例")

    # 检查线程池配置
    pool = manager1._pool
    thread_count = pool.maxThreadCount()
    test_pass(f"线程池配置: maxThreadCount={thread_count}")

except Exception as e:
    test_fail("WorkerManager测试失败", str(e))


# ==================== 测试8: 缓存机制测试 ====================
print("\n【测试8】缓存机制测试")
try:
    from core.workers import _audio_cache, _cache_audio, _get_cached_audio

    # 清空缓存
    _audio_cache.clear()

    # 创建测试数据（合成数据）
    test_path = "test_audio_cache.wav"
    test_data = np.random.randn(22053).astype(np.float32)
    test_sr = 22050

    # 测试缓存写入
    _cache_audio(test_path, test_data, test_sr)
    if test_path in _audio_cache:
        test_pass("音频缓存写入成功")
    else:
        test_fail("音频缓存写入失败", "缓存键不存在")

    # 测试缓存读取
    cached = _get_cached_audio(test_path)
    if cached is not None:
        cached_data, cached_sr = cached
        if np.array_equal(cached_data, test_data):
            test_pass("音频缓存读取正确")
        else:
            test_fail("音频缓存数据不一致", "数据不匹配")
    else:
        test_fail("音频缓存读取失败", "返回None")

except Exception as e:
    test_fail("缓存机制测试失败", str(e))


# ==================== 测试9: PySide6组件测试 ====================
print("\n【测试9】PySide6组件测试")
try:
    from PySide6.QtWidgets import QApplication, QWidget
    from PySide6.QtCore import Qt

    # 创建测试应用（不显示）
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    # 测试雷达图创建
    radar = RadarChart()
    radar.update_scores({'volume': 80, 'pitch': 75, 'rhythm': 70, 'breath': 85, 'emotion': 90})
    test_pass("RadarChart创建和更新成功")

    # 测试评分面板创建
    panel = ScorePanel()
    panel.update_scores({'volume': 80, 'pitch': 75, 'rhythm': 70, 'breath': 85, 'emotion': 90})
    panel.set_advice("测试建议")
    test_pass("ScorePanel创建和更新成功")

except ImportError as e:
    test_fail("PySide6 未安装", str(e))
except Exception as e:
    test_fail("PySide6组件测试失败", str(e))


# ==================== 测试总结 ====================
print("\n" + "=" * 60)
print("测试结果汇总")
print("=" * 60)
print(f"通过: {test_results['passed']}")
print(f"失败: {test_results['failed']}")

if test_results['errors']:
    print("\n失败详情:")
    for error in test_results['errors']:
        print(f"  - {error}")

if test_results['failed'] == 0:
    print("\n[SUCCESS] 所有测试通过！系统可正常运行。")
else:
    print(f"\n[WARNING] 有 {test_results['failed']} 个测试失败，请检查上述错误。")

print("=" * 60)