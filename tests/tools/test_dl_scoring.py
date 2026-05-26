"""
测试深度学习评分体系 v5.0
验证SingMOS等模型的评分效果
"""

import os
import sys

# 解决OpenMP冲突
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

# 设置HF镜像
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

# 添加项目路径
sys.path.insert(0, r'C:\Users\jack\Desktop\临时文件\声乐\vocal_assessment_light')

from services.dl_services.dl_quality_assessor import create_dl_assessor, DLQualityAssessor
from services.score_service import ScoreServiceV4
from services.audio_service import AudioService
from config import config


def test_dl_assessor():
    """测试深度学习质量评估器"""
    print("=" * 60)
    print("深度学习质量评估测试")
    print("=" * 60)

    assessor = create_dl_assessor()

    test_files = [
        'tests/test_data/audio/vocal/恋人.mp3',
        'tests/test_data/audio/vocal/手写的从前.mp3'
    ]

    for filepath in test_files:
        if not os.path.exists(filepath):
            print(f"\n文件不存在: {filepath}")
            continue

        print(f"\n--- {filepath} ---")

        result = assessor.assess(filepath)

        print(f"  MOS分数: {result.mos_score:.2f} / 5.0")
        print(f"  归一化分数: {result.mos_normalized:.1f} / 100")
        print(f"  自然度: {result.naturalness:.1f}")
        print(f"  清晰度: {result.clarity:.1f}")
        print(f"  音色质量: {result.timbre_quality:.1f}")
        print(f"  置信度: {result.confidence:.2f}")
        print(f"  方法: {result.method}")

        level, color = assessor.get_quality_level(result.mos_score)
        print(f"  等级: {level}")


def test_full_scoring():
    """测试完整评分流程（传统+DL融合）"""
    print("\n" + "=" * 60)
    print("完整评分测试（传统+DL融合）")
    print("=" * 60)

    audio_service = AudioService(config)
    score_service = ScoreServiceV4()
    dl_assessor = create_dl_assessor()

    test_files = [
        'tests/test_data/audio/vocal/恋人.mp3',
        'tests/test_data/audio/vocal/手写的从前.mp3'
    ]

    for filepath in test_files:
        if not os.path.exists(filepath):
            print(f"\n文件不存在: {filepath}")
            continue

        print(f"\n--- {filepath} ---")

        # 1. 音频分析
        audio_result = audio_service.analyze(filepath)
        if not audio_result.success:
            print(f"  分析失败: {audio_result.error}")
            continue

        # 2. DL质量评估
        dl_result = dl_assessor.assess(filepath)
        print(f"  DL MOS: {dl_result.mos_score:.2f} ({dl_result.method})")

        # 3. 获取风格信息
        style_profile = getattr(audio_result, '_style_profile', None)
        music_mood = getattr(audio_result, '_music_mood', None)

        if style_profile:
            print(f"  风格: {style_profile.style_cn}")

        # 4. 传统评分（无DL）
        from services.audio_features_service import AudioFeaturesResult
        advanced_features = audio_result._advanced_features
        if advanced_features is None:
            advanced_features = AudioFeaturesResult()

        traditional_result = score_service.calculate(
            features=advanced_features,
            emotion_confidence=0.5,
            emotions={},
            voice_quality_score=100.0,
            style_profile=style_profile,
            music_mood=music_mood,
            dl_mos_score=0,
            dl_mos_normalized=0
        )

        print(f"\n  传统评分:")
        print(f"    音准: {traditional_result.pitch_score:.1f}")
        print(f"    节奏: {traditional_result.rhythm_score:.1f}")
        print(f"    气息: {traditional_result.breath_score:.1f}")
        print(f"    技术: {traditional_result.technique_score:.1f}")
        print(f"    艺术: {traditional_result.artistry_score:.1f}")
        print(f"    总分: {traditional_result.total_score:.1f}")

        # 5. DL融合评分
        fused_result = score_service.calculate(
            features=advanced_features,
            emotion_confidence=0.5,
            emotions={},
            voice_quality_score=100.0,
            style_profile=style_profile,
            music_mood=music_mood,
            dl_mos_score=dl_result.mos_score,
            dl_mos_normalized=dl_result.mos_normalized,
            dl_method=dl_result.method,
            dl_confidence=dl_result.confidence
        )

        print(f"\n  DL融合评分:")
        print(f"    音准: {fused_result.pitch_score:.1f}")
        print(f"    节奏: {fused_result.rhythm_score:.1f}")
        print(f"    气息: {fused_result.breath_score:.1f}")
        print(f"    技术: {fused_result.technique_score:.1f}")
        print(f"    艺术: {fused_result.artistry_score:.1f}")
        print(f"    总分: {fused_result.total_score:.1f}")
        print(f"    等级: {fused_result.level}")

        print(f"\n  改进: {fused_result.total_score - traditional_result.total_score:+.1f}分")


def test_threshold_adjustment():
    """测试阈值调整效果"""
    print("\n" + "=" * 60)
    print("阈值调整效果测试")
    print("=" * 60)

    score_service = ScoreServiceV4()

    print("\n评分阈值对比:")
    print(f"  音准满分阈值: {score_service.PITCH_EXCELLENT} 音分 (原10)")
    print(f"  音准良好阈值: {score_service.PITCH_GOOD} 音分 (原30)")
    print(f"  音准合格阈值: {score_service.PITCH_PASS} 音分 (原50)")
    print(f"  节奏满分阈值: {score_service.RHYTHM_EXCELLENT} (原0.1)")
    print(f"  节奏良好阈值: {score_service.RHYTHM_GOOD} (原0.2)")
    print(f"  节奏合格阈值: {score_service.RHYTHM_PASS} (原0.3)")
    print(f"  连续跑调阈值: {score_service.CONSECUTIVE_OFF_THRESHOLD} 音符 (原3)")

    # 模拟不同音分偏差的评分
    print("\n音准评分曲线:")
    for mae in [5, 10, 15, 20, 30, 40, 50, 60]:
        # 简化计算
        if mae <= score_service.PITCH_EXCELLENT:
            score = 100
        elif mae <= score_service.PITCH_GOOD:
            score = 100 - (mae - score_service.PITCH_EXCELLENT) / (score_service.PITCH_GOOD - score_service.PITCH_EXCELLENT) * 10
        elif mae <= score_service.PITCH_PASS:
            score = 90 - (mae - score_service.PITCH_GOOD) / (score_service.PITCH_PASS - score_service.PITCH_GOOD) * 20
        else:
            score = max(0, 70 - (mae - score_service.PITCH_PASS) * 0.5)

        print(f"  MAE={mae}音分 -> {score:.1f}分")


if __name__ == '__main__':
    # 测试DL评估器
    test_dl_assessor()

    # 测试阈值调整
    test_threshold_adjustment()

    # 测试完整评分
    test_full_scoring()
