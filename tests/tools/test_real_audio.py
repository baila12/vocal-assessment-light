"""
测试真实音频的ONNX模型推理
"""
import os
import sys
import io

# 设置环境变量解决OpenMP冲突
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

# 设置UTF-8编码输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import librosa

def test_voice_quality_on_real_audio(audio_path):
    """使用真实音频测试VoiceQualityDetector"""
    print("\n" + "="*60)
    print(f"测试 VoiceQualityDetector - {os.path.basename(audio_path)}")
    print("="*60)

    try:
        from services.dl_services.voice_quality_detector import VoiceQualityDetector

        detector = VoiceQualityDetector()
        print(f"模型可用: {detector._model_available}")

        result = detector.detect(audio_path)

        print(f"\n检测结果:")
        print(f"  是否包含人声: {result.has_voice}")
        print(f"  人声占比: {result.voice_ratio:.2%}")
        print(f"  是否纯伴奏: {result.is_accompaniment_only}")
        print(f"  是否噪声: {result.is_noise}")
        print(f"  适合声乐分析: {result.is_valid_for_analysis}")
        print(f"  置信度: {result.confidence:.2%}")
        print(f"  检测方法: {result.method}")

        recommendation = detector.get_analysis_recommendation(result)
        print(f"\n建议: {recommendation}")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_style_classifier_on_real_audio(audio_path):
    """使用真实音频测试SingingStyleClassifier"""
    print("\n" + "="*60)
    print(f"测试 SingingStyleClassifier - {os.path.basename(audio_path)}")
    print("="*60)

    try:
        from services.dl_services.singing_style_classifier import SingingStyleClassifier, SingingStyle

        classifier = SingingStyleClassifier()
        print(f"模型可用: {classifier._model_available}")

        result = classifier.classify(audio_path)

        print(f"\n分类结果:")
        print(f"  识别风格: {result.style.value}")
        print(f"  置信度: {result.confidence:.2%}")
        print(f"  检测方法: {result.method}")

        print(f"\n各风格概率:")
        for style_name, prob in sorted(result.probabilities.items(), key=lambda x: -x[1]):
            if prob > 0.001:
                bar = "█" * int(prob * 20)
                print(f"    {style_name:12s}: {prob:.2%} {bar}")

        description = classifier.get_style_description(result.style)
        print(f"\n风格描述: {description}")

        weights = classifier.get_scoring_weights(result.style)
        print(f"\n评分权重:")
        for key, value in weights.items():
            print(f"    {key}: {value:.2f}")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_self_referenced_dtw_on_real_audio(audio_path):
    """使用真实音频测试SelfReferencedDTW"""
    print("\n" + "="*60)
    print(f"测试 SelfReferencedDTW - {os.path.basename(audio_path)}")
    print("="*60)

    try:
        from services.dl_services.self_referenced_dtw import SelfReferencedDTW

        dtw = SelfReferencedDTW()

        result = dtw.analyze(audio_path)

        print(f"\n音准分析结果:")
        print(f"  整体稳定性: {result.overall_stability:.1f}/100")
        print(f"  稳定音符占比: {result.stable_note_ratio:.2%}")
        print(f"  平均音分偏差: {result.avg_deviation_cents:.1f} 音分")
        print(f"  最大音分偏差: {result.max_deviation_cents:.1f} 音分")
        print(f"  有意波动次数: {result.intentional_variations}")
        print(f"  无意跑调次数: {result.unintentional_drifts}")
        print(f"  检测方法: {result.method}")
        print(f"  音符数量: {len(result.notes)}")

        diagnosis = dtw.get_pitch_diagnosis(result)
        print(f"\n诊断报告:")
        for key, text in diagnosis.items():
            print(f"  {text}")

        return True

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "="*60)
    print("真实音频 ONNX 模型测试")
    print("="*60)

    # 测试音频列表
    test_audios = [
        'tests/test_data/audio/vocal/恋人.mp3',
        'tests/test_data/audio/vocal/手写的从前.mp3',
        'uploads/测试音频.wav',
        'tests/test_data/audio/non_vocal/simulated_voice.wav',
    ]

    # 过滤存在的文件
    existing_audios = [f for f in test_audios if os.path.exists(f)]

    if not existing_audios:
        print("\n未找到测试音频文件")
        return False

    print(f"\n找到 {len(existing_audios)} 个测试音频:")
    for audio in existing_audios:
        print(f"  - {audio}")

    results = {}

    for audio_path in existing_audios:
        print("\n" + "="*60)
        print(f"处理: {audio_path}")
        print("="*60)

        # 获取音频信息
        try:
            y, sr = librosa.load(audio_path, sr=None, mono=True, duration=30)
            duration = len(y) / sr
            print(f"采样率: {sr} Hz")
            print(f"时长: {duration:.2f} 秒")
            print(f"样本数: {len(y)}")
        except Exception as e:
            print(f"无法加载音频: {e}")
            continue

        audio_results = {}

        # 测试VoiceQualityDetector
        audio_results['voice_quality'] = test_voice_quality_on_real_audio(audio_path)

        # 测试SingingStyleClassifier
        audio_results['style_classifier'] = test_style_classifier_on_real_audio(audio_path)

        # 测试SelfReferencedDTW
        audio_results['self_referenced_dtw'] = test_self_referenced_dtw_on_real_audio(audio_path)

        results[audio_path] = audio_results

    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)

    total_tests = 0
    passed_tests = 0

    for audio_path, audio_results in results.items():
        print(f"\n{os.path.basename(audio_path)}:")
        for test_name, passed in audio_results.items():
            status = "✅" if passed else "❌"
            print(f"  {test_name}: {status}")
            total_tests += 1
            if passed:
                passed_tests += 1

    print(f"\n总计: {passed_tests}/{total_tests} 通过")

    return passed_tests == total_tests


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
