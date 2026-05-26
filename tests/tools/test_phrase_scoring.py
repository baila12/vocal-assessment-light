"""
测试逐句评分系统

使用真实音频分析当前评分问题
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import librosa
from services.phrase_service import PhraseService

def test_phrase_scoring():
    """使用真实音频测试逐句评分"""

    # 测试音频文件列表
    test_files = [
        "tests/test_data/audio/vocal/恋人.mp3",
        "tests/test_data/audio/vocal/手写的从前.mp3",
        "tests/test_data/audio/non_vocal/test_audio__from_test_music.wav",
    ]

    service = PhraseService()

    print("=" * 80)
    print("逐句评分测试 - 真实音频分析")
    print("=" * 80)

    for audio_path in test_files:
        if not os.path.exists(audio_path):
            print(f"\n[跳过] 文件不存在: {audio_path}")
            continue

        print(f"\n{'='*60}")
        print(f"音频文件: {audio_path}")
        print("=" * 60)

        try:
            # 加载音频
            audio, sr = librosa.load(audio_path, sr=22050, duration=30)  # 限制30秒
            duration = len(audio) / sr
            print(f"时长: {duration:.1f}秒, 采样率: {sr}Hz")

            # 预计算 f0
            print("计算基频 (pYIN)...")
            f0, voiced_flags, _ = librosa.pyin(
                audio,
                fmin=65,
                fmax=1047,
                sr=sr,
                hop_length=512
            )
            valid_f0_count = np.sum(~np.isnan(f0))
            print(f"有效基频帧数: {valid_f0_count}")

            # 执行逐句分析
            print("\n执行逐句评分...")
            result = service.analyze_phrases(audio, f0=f0, enable_parallel=False)

            if not result.success:
                print(f"[错误] {result.error_message}")
                continue

            print(f"\n分段数量: {result.total_phrases}")
            print(f"平均分数: {result.avg_score}")
            print(f"最佳句子: #{result.best_phrase_id}")
            print(f"最差句子: #{result.worst_phrase_id}")

            # 详细输出每个分段
            print("\n" + "-" * 60)
            print("各分段评分详情:")
            print("-" * 60)
            print(f"{'ID':<4} {'时间':<12} {'音量':<8} {'音准':<8} {'节奏':<8} {'气息':<8} {'情绪':<8} {'总分':<8} {'等级':<8}")
            print("-" * 60)

            for p in result.phrases:
                time_str = f"{p.start_time:.1f}-{p.end_time:.1f}s"
                print(f"{p.phrase_id:<4} {time_str:<12} {p.volume:<8.1f} {p.pitch:<8.1f} {p.rhythm:<8.1f} {p.breath:<8.1f} {p.emotion:<8.1f} {p.total:<8.1f} {p.level:<8}")

            # 统计各分数段分布
            print("\n分数分布统计:")
            scores = [p.total for p in result.phrases]
            dims = {
                '音量': [p.volume for p in result.phrases],
                '音准': [p.pitch for p in result.phrases],
                '节奏': [p.rhythm for p in result.phrases],
                '气息': [p.breath for p in result.phrases],
                '情绪': [p.emotion for p in result.phrases],
            }

            for dim_name, dim_scores in dims.items():
                avg = np.mean(dim_scores)
                min_s = np.min(dim_scores)
                max_s = np.max(dim_scores)
                below_60 = sum(1 for s in dim_scores if s < 60)
                below_70 = sum(1 for s in dim_scores if s < 70)
                print(f"  {dim_name}: 平均 {avg:.1f}, 范围 [{min_s:.1f}-{max_s:.1f}], <60分: {below_60}个, <70分: {below_70}个")

        except Exception as e:
            print(f"[错误] 处理失败: {e}")
            import traceback
            traceback.print_exc()


def analyze_scoring_thresholds():
    """分析当前评分阈值的问题"""
    print("\n" + "=" * 80)
    print("评分阈值分析 (修复后)")
    print("=" * 80)

    # 音准评分阈值分析
    print("\n【音准评分】优化后阈值:")
    print("  relative_std < 0.08 (8%):  90-100分 (优秀)")
    print("  8% < relative_std < 20%:   70-90分 (良好)")
    print("  20% < relative_std < 35%:  50-70分 (中等)")
    print("  relative_std > 35%:        50分保底 (需改进)")
    print("\n改进: 阈值从 5%/15%/30% 调整为 8%/20%/35%，底分从 30 提升到 50")

    # 节奏评分阈值分析
    print("\n【节奏评分】优化后阈值:")
    print("  cv < 0.3:  70-85分 (稳定)")
    print("  0.3-1.5:  85-95分 (理想)")
    print("  cv > 1.5:  60-95分 (不稳定)")
    print("\n改进: 稳定节奏最低分从 60 提升到 70")

    # 气息评分阈值分析
    print("\n【气息评分】优化后阈值:")
    print("  relative_change < 8%:  90-100分")
    print("  8% < relative_change < 20%:  75-90分")
    print("  20% < relative_change < 35%: 50-75分")
    print("  relative_change > 35%:  50分保底")
    print("\n改进: 阈值从 5%/15%/30% 调整为 8%/20%/35%，底分从 40 提升到 50")

    # 情绪评分分析
    print("\n【情绪评分】优化后:")
    print("  基准分: 65分")
    print("  能量加分: 0-15分")
    print("  亮度加分: 0-10分")
    print("  动态变化加分: 0-10分")
    print("  总分范围: 50-100分")
    print("\n改进: 移除魔法数字，使用基准分+加分模式，底分 50")


if __name__ == "__main__":
    test_phrase_scoring()
    analyze_scoring_thresholds()