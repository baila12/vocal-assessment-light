"""
测试优化后的评估算法 v5.3

验证：
1. 快速模式评分公正性
2. 专业模式详细反馈
3. 两种模式评分一致性
"""

import os
import sys
import time
import io

# 设置环境
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.business.audio_analysis import analyze_and_score
from services.dl_services.enhanced_dl_assessor import get_enhanced_assessor, ScoreCalibrator


def test_evaluation_modes():
    """测试快速模式和专业模式"""
    print("\n" + "=" * 70)
    print("评估模式对比测试")
    print("=" * 70)

    test_files = [
        'tests/test_data/audio/vocal/恋人.mp3',
        'tests/test_data/audio/vocal/手写的从前.mp3'
    ]

    for filepath in test_files:
        if not os.path.exists(filepath):
            print(f"\n文件不存在: {filepath}")
            continue

        print(f"\n{'='*60}")
        print(f"文件: {os.path.basename(filepath)}")
        print(f"{'='*60}")

        # 快速模式
        print("\n【快速模式】")
        start_time = time.time()
        quick_result = analyze_and_score(filepath, mode='quick')
        quick_time = time.time() - start_time

        if quick_result.get('success', False):
            scores = quick_result.get('scores', {})
            print(f"  耗时: {quick_time:.1f}秒")
            print(f"  总分: {scores.get('total', 0):.1f}")
            print(f"  等级: {quick_result.get('level', 'N/A')}")
            print(f"  音准: {scores.get('pitch', 0):.1f}")
            print(f"  节奏: {scores.get('rhythm', 0):.1f}")
            print(f"  气息: {scores.get('breath', 0):.1f}")
            print(f"  技术: {scores.get('technique', 0):.1f}")
            print(f"  艺术: {scores.get('artistry', 0):.1f}")
        else:
            print(f"  失败: {quick_result.get('error', 'Unknown')}")

        # 专业模式
        print("\n【专业模式】")
        start_time = time.time()
        prof_result = analyze_and_score(filepath, mode='professional')
        prof_time = time.time() - start_time

        if prof_result.get('success', False):
            scores = prof_result.get('scores', {})
            print(f"  耗时: {prof_time:.1f}秒")
            print(f"  总分: {scores.get('total', 0):.1f}")
            print(f"  等级: {prof_result.get('level', 'N/A')}")
            print(f"  音准: {scores.get('pitch', 0):.1f}")
            print(f"  节奏: {scores.get('rhythm', 0):.1f}")
            print(f"  气息: {scores.get('breath', 0):.1f}")
            print(f"  技术: {scores.get('technique', 0):.1f}")
            print(f"  艺术: {scores.get('artistry', 0):.1f}")

            # DL评估信息
            dl_info = prof_result.get('dl', {})
            if dl_info.get('available', False):
                print(f"\n  【DL评估】")
                print(f"    MOS: {dl_info.get('mos_score', 0):.2f}/5.0")
                print(f"    方法: {dl_info.get('method', 'N/A')}")
                print(f"    置信度: {dl_info.get('confidence', 0):.2f}")
        else:
            print(f"  失败: {prof_result.get('error', 'Unknown')}")

        # 对比分析
        if quick_result.get('success') and prof_result.get('success'):
            quick_total = quick_result.get('scores', {}).get('total', 0)
            prof_total = prof_result.get('scores', {}).get('total', 0)
            diff = quick_total - prof_total

            print(f"\n【对比分析】")
            print(f"  分数差异: {diff:+.1f}分")
            if abs(diff) <= 5:
                print(f"  ✓ 两种模式评分一致")
            elif abs(diff) <= 10:
                print(f"  ⚠ 两种模式评分略有差异（可接受）")
            else:
                print(f"  ✗ 两种模式评分差异较大（需调整）")


def test_score_calibrator():
    """测试评分校准器"""
    print("\n" + "=" * 70)
    print("评分校准器测试")
    print("=" * 70)

    calibrator = ScoreCalibrator()

    # 测试不同分数的校准效果
    test_scores = [30, 50, 70, 85, 95]

    print("\n快速模式校准效果:")
    print(f"{'原始分数':>10} | {'校准后':>10} | {'变化':>10}")
    print("-" * 40)
    for score in test_scores:
        calibrated = calibrator.calibrate_score(score, 'pitch', 'quick')
        change = calibrated - score
        print(f"{score:>10.1f} | {calibrated:>10.1f} | {change:>+10.1f}")

    print("\n专业模式校准效果:")
    print(f"{'原始分数':>10} | {'校准后':>10} | {'变化':>10}")
    print("-" * 40)
    for score in test_scores:
        calibrated = calibrator.calibrate_score(score, 'pitch', 'professional')
        change = calibrated - score
        print(f"{score:>10.1f} | {calibrated:>10.1f} | {change:>+10.1f}")


def test_enhanced_assessor():
    """测试增强的DL评估器"""
    print("\n" + "=" * 70)
    print("增强DL评估器测试")
    print("=" * 70)

    assessor = get_enhanced_assessor()

    print(f"\n评估器状态:")
    print(f"  CREPE可用: {assessor._crepe.is_available if assessor._crepe else False}")
    print(f"  SpeechBrain可用: {assessor._speechbrain_mos.is_available if assessor._speechbrain_mos else False}")
    print(f"  SingMOS可用: {assessor._singmos._model_available if assessor._singmos else False}")

    # 测试音频
    test_file = 'tests/test_data/audio/vocal/恋人.mp3'
    if os.path.exists(test_file):
        import librosa

        print(f"\n测试音频: {test_file}")
        audio, sr = librosa.load(test_file, sr=16000, duration=30)

        # 快速模式评估
        print("\n快速模式评估:")
        result = assessor.assess(audio, sr, mode='quick')
        print(f"  基频方法: {result.f0_method}")
        print(f"  MOS分数: {result.mos_score:.2f}")
        print(f"  MOS方法: {result.mos_method}")
        print(f"  处理时间: {result.processing_time:.2f}秒")
        print(f"  使用模型: {result.models_used}")

        # 专业模式评估
        print("\n专业模式评估:")
        result = assessor.assess(audio, sr, mode='professional', filepath=test_file)
        print(f"  基频方法: {result.f0_method}")
        print(f"  MOS分数: {result.mos_score:.2f}")
        print(f"  MOS方法: {result.mos_method}")
        print(f"  处理时间: {result.processing_time:.2f}秒")
        print(f"  使用模型: {result.models_used}")


def main():
    print("\n" + "=" * 70)
    print("评估算法优化测试 v5.3")
    print("=" * 70)

    # 测试评分校准器
    test_score_calibrator()

    # 测试增强DL评估器
    test_enhanced_assessor()

    # 测试评估模式
    test_evaluation_modes()

    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)


if __name__ == '__main__':
    main()
