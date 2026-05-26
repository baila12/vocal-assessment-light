"""
测试真实音频的完整评分流程
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

def test_full_scoring(audio_path):
    """测试完整评分流程"""
    print("\n" + "="*70)
    print(f"完整评分测试: {os.path.basename(audio_path)}")
    print("="*70)

    try:
        from services.audio_service import AudioService
        from services.score_service import ScoreServiceV4
        from config import Config

        # 初始化服务
        config = Config()
        audio_service = AudioService(config)
        score_service = ScoreServiceV4()

        # 1. 音频分析
        print("\n【步骤1】音频分析...")
        analysis_result = audio_service.analyze(audio_path)

        if not analysis_result.success:
            print(f"❌ 音频分析失败: {analysis_result.error}")
            return False

        print(f"  文件: {analysis_result.filename}")
        print(f"  时长: {analysis_result.duration:.2f}s")
        print(f"  采样率: {analysis_result.sample_rate}Hz")

        # 音量信息
        vol = analysis_result.volume_info
        print(f"\n  音量: 平均{vol.get('avg_db', 0):.1f}dB, 峰值{vol.get('peak_db', 0):.1f}dB")

        # 音高信息
        pitch = analysis_result.pitch_info
        print(f"  音高稳定性: {analysis_result._pitch_stability:.2%}")
        if 'warning' in pitch:
            print(f"  ⚠️ 警告: {pitch['warning']}")

        # 深度学习分析结果
        if analysis_result._voice_quality:
            vq = analysis_result._voice_quality
            print(f"\n  【DL】人声质量:")
            print(f"    是否有人声: {vq.get('has_voice', False)}")
            print(f"    人声占比: {vq.get('voice_ratio', 0):.2%}")
            print(f"    适合分析: {vq.get('is_valid', False)}")
            print(f"    检测方法: {vq.get('method', 'N/A')}")

        if analysis_result._singing_style:
            ss = analysis_result._singing_style
            print(f"\n  【DL】唱法识别:")
            print(f"    风格: {ss.get('style', 'unknown')}")
            print(f"    置信度: {ss.get('confidence', 0):.2%}")
            print(f"    检测方法: {ss.get('method', 'N/A')}")

        if analysis_result._pitch_stability_dl:
            ps = analysis_result._pitch_stability_dl
            print(f"\n  【DL】音准稳定性:")
            print(f"    整体稳定性: {ps.get('overall_stability', 0):.1f}/100")
            print(f"    稳定音符占比: {ps.get('stable_note_ratio', 0):.2%}")
            print(f"    平均音分偏差: {ps.get('avg_deviation_cents', 0):.1f}音分")
            print(f"    有意波动: {ps.get('intentional_variations', 0)}")
            print(f"    无意跑调: {ps.get('unintentional_drifts', 0)}")

        # 2. 评分计算
        print("\n【步骤2】评分计算...")

        # 获取高级特征
        features = analysis_result._advanced_features

        if features:
            score_result = score_service.calculate(
                features=features,
                emotion_confidence=0.5,
                voice_quality_score=100.0 if (analysis_result._voice_quality and analysis_result._voice_quality.get('is_valid', True)) else 50.0
            )

            # 输出评分结果
            print("\n" + "-"*50)
            print("【评分结果】")
            print("-"*50)

            print(f"\n  五维评分:")
            print(f"    音准: {score_result.pitch_score:.1f}/100")
            print(f"    节奏: {score_result.rhythm_score:.1f}/100")
            print(f"    气息: {score_result.breath_score:.1f}/100")
            print(f"    技术: {score_result.technique_score:.1f}/100")
            print(f"    艺术: {score_result.artistry_score:.1f}/100")

            print(f"\n  总分: {score_result.total_score:.1f}/100")
            print(f"  等级: {score_result.level} {score_result.stars}")

            # 详细诊断
            if score_result.pitch_diagnosis:
                pd = score_result.pitch_diagnosis
                print(f"\n  【音准诊断】")
                print(f"    等级: {pd.level}")
                print(f"    平均偏差: {pd.mae_cents:.1f}音分")
                if pd.issues:
                    print(f"    问题: {', '.join(pd.issues[:3])}")
                if pd.suggestions:
                    print(f"    建议: {pd.suggestions[0]}")

            if score_result.breath_diagnosis:
                bd = score_result.breath_diagnosis
                print(f"\n  【气息诊断】")
                print(f"    等级: {bd.level}")
                print(f"    波动系数: {bd.fluctuation:.3f}")
                print(f"    长音支撑: {bd.long_note_support:.1f}")
                print(f"    动态控制: {bd.dynamic_control:.1f}")
                if bd.is_artistic:
                    print(f"    ✅ 检测到艺术化处理")
                if bd.has_controlled_breathiness:
                    print(f"    ✅ 检测到可控气声")

            if score_result.technique_diagnosis:
                td = score_result.technique_diagnosis
                print(f"\n  【技术诊断】")
                print(f"    等级: {td.level}")
                print(f"    HNR: {td.hnr:.1f}dB")
                print(f"    CPP: {td.cpp:.1f}dB")
                print(f"    颤音质量: {td.vibrato_quality:.1f}")

            # 底线规则
            if score_result.critical_issues:
                print(f"\n  ⚠️ 关键问题: {', '.join(score_result.critical_issues)}")
            if score_result.is_disqualified:
                print(f"  ❌ 不合格: 存在严重问题")

            return True
        else:
            print("❌ 无法提取高级特征")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "="*70)
    print("真实音频完整评分测试")
    print("="*70)

    # 测试音频列表
    test_audios = [
        'tests/test_data/audio/vocal/恋人.mp3',
        'tests/test_data/audio/vocal/手写的从前.mp3',
        'tests/test_data/audio/non_vocal/simulated_voice.wav',
    ]

    # 过滤存在的文件
    existing_audios = [f for f in test_audios if os.path.exists(f)]

    if not existing_audios:
        print("\n未找到测试音频文件")
        return False

    print(f"\n找到 {len(existing_audios)} 个测试音频")

    results = {}
    for audio_path in existing_audios:
        results[audio_path] = test_full_scoring(audio_path)

    # 汇总
    print("\n" + "="*70)
    print("测试结果汇总")
    print("="*70)

    for audio_path, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {os.path.basename(audio_path)}")

    return all(results.values())


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
