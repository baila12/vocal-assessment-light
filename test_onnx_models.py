"""
测试ONNX模型是否正常工作
"""
import os
import sys
import numpy as np
import io

# 设置UTF-8编码输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_silero_vad():
    """测试Silero VAD模型"""
    print("\n" + "="*50)
    print("测试 Silero VAD 模型")
    print("="*50)

    model_path = 'models/voice_quality/silero_vad.onnx'

    if not os.path.exists(model_path):
        print(f"❌ 模型文件不存在: {model_path}")
        return False

    try:
        import onnxruntime as ort

        # 加载模型
        session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
        print(f"✅ 模型加载成功: {model_path}")

        # 打印输入输出信息
        print("\n输入:")
        for inp in session.get_inputs():
            print(f"  - {inp.name}: {inp.shape} ({inp.type})")

        print("\n输出:")
        for out in session.get_outputs():
            print(f"  - {out.name}: {out.shape} ({out.type})")

        # 模拟测试 - Silero VAD输入形状: [batch, samples] (rank 2)
        sr = 16000
        chunk = np.random.randn(512).astype(np.float32)
        state = np.zeros((2, 1, 128), dtype=np.float32)

        ort_inputs = {
            'input': chunk[np.newaxis, :],  # [1, 512] - rank 2
            'state': state,
            'sr': np.array(sr, dtype=np.int64)
        }

        out, state_new = session.run(['output', 'stateN'], ort_inputs)
        print(f"\n✅ 推理测试成功: 输出概率 = {out[0][0]:.4f}")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_ast_classifier():
    """测试AST音乐风格分类模型"""
    print("\n" + "="*50)
    print("测试 AST 音乐风格分类模型")
    print("="*50)

    model_path = 'models/style_classifier/model_quantized.onnx'
    config_path = 'models/style_classifier/config.json'

    if not os.path.exists(model_path):
        print(f"❌ 模型文件不存在: {model_path}")
        return False

    try:
        import onnxruntime as ort
        import json

        # 加载模型
        session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
        print(f"✅ 模型加载成功: {model_path}")

        # 打印输入输出信息
        print("\n输入:")
        for inp in session.get_inputs():
            print(f"  - {inp.name}: {inp.shape} ({inp.type})")

        print("\n输出:")
        for out in session.get_outputs():
            print(f"  - {out.name}: {out.shape} ({out.type})")

        # 加载配置
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"\n✅ 配置加载成功: {config_path}")
            print(f"  标签数量: {len(config.get('id2label', {}))}")
            print(f"  标签: {list(config.get('id2label', {}).values())}")

        # 模拟测试 - 创建随机频谱输入
        # AST期望输入形状: (batch, 1024, 128)
        test_input = np.random.randn(1, 1024, 128).astype(np.float32)

        result = session.run(['logits'], {'input_values': test_input})
        logits = result[0][0]

        # 应用softmax
        exp_logits = np.exp(logits - np.max(logits))
        probs = exp_logits / np.sum(exp_logits)

        print(f"\n✅ 推理测试成功")
        print(f"  输出logits形状: {logits.shape}")
        print(f"  概率分布: {probs}")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_voice_quality_detector():
    """测试VoiceQualityDetector类"""
    print("\n" + "="*50)
    print("测试 VoiceQualityDetector 类")
    print("="*50)

    try:
        from services.dl_services.voice_quality_detector import VoiceQualityDetector

        detector = VoiceQualityDetector()
        print(f"✅ VoiceQualityDetector 初始化成功")
        print(f"  模型可用: {detector._model_available}")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_singing_style_classifier():
    """测试SingingStyleClassifier类"""
    print("\n" + "="*50)
    print("测试 SingingStyleClassifier 类")
    print("="*50)

    try:
        from services.dl_services.singing_style_classifier import SingingStyleClassifier

        classifier = SingingStyleClassifier()
        print(f"✅ SingingStyleClassifier 初始化成功")
        print(f"  模型可用: {classifier._model_available}")
        print(f"  标签映射: {classifier._id2label}")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "="*60)
    print("ONNX 模型测试")
    print("="*60)

    results = {}

    # 测试原始ONNX模型
    results['Silero VAD'] = test_silero_vad()
    results['AST Classifier'] = test_ast_classifier()

    # 测试封装类
    results['VoiceQualityDetector'] = test_voice_quality_detector()
    results['SingingStyleClassifier'] = test_singing_style_classifier()

    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)

    for name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {name}: {status}")

    all_passed = all(results.values())
    print("\n" + ("🎉 所有测试通过！" if all_passed else "⚠️ 部分测试失败"))
    print("="*60)

    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
