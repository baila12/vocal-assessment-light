"""
测试风格自适应评分算法 v2.0
验证不同音乐风格的评分调整效果
"""

import os
import sys

# 解决OpenMP冲突
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

# 设置HF镜像
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'

# 添加项目路径
sys.path.insert(0, r'C:\Users\jack\Desktop\临时文件\声乐\vocal_assessment_light')

from services.style_aware_scorer import StyleAwareScorer, MusicStyle, STYLE_PROFILES
from services.score_service import ScoreServiceV4
from services.audio_features_service import AudioFeaturesResult
from services.audio_service import AudioService
from config import config


def test_style_adjustments():
    """测试各风格的评分调整效果"""
    print("=" * 60)
    print("风格自适应评分测试 v2.0")
    print("=" * 60)

    scorer = StyleAwareScorer()

    # 模拟基础分数（假设一个中等水平的演唱）
    base_scores = {
        'pitch': 75.0,
        'rhythm': 75.0,
        'breath': 75.0,
        'technique': 75.0,
        'artistry': 75.0
    }

    print("\n基础分数（统一）:")
    for dim, score in base_scores.items():
        print(f"  {dim}: {score:.1f}")

    print("\n" + "-" * 60)
    print("各风格调整结果:")
    print("-" * 60)

    for style in MusicStyle:
        profile = STYLE_PROFILES[style]

        # 计算调整后的分数
        adjusted_pitch = scorer.adjust_pitch_score(base_scores['pitch'], profile)
        adjusted_rhythm = scorer.adjust_rhythm_score(base_scores['rhythm'], profile)
        adjusted_breath = scorer.adjust_breath_score(base_scores['breath'], profile)
        adjusted_technique = scorer.adjust_technique_score(base_scores['technique'], profile)
        adjusted_artistry = scorer.adjust_artistry_score(base_scores['artistry'], profile)

        # 计算总分
        weights = scorer.get_adjusted_weights(profile)
        total = (
            adjusted_pitch * weights['pitch'] +
            adjusted_rhythm * weights['rhythm'] +
            adjusted_breath * weights['breath'] +
            adjusted_technique * weights['technique'] +
            adjusted_artistry * weights['artistry']
        )

        print(f"\n【{profile.style_cn}】({style.value})")
        print(f"  音准: {base_scores['pitch']:.1f} -> {adjusted_pitch:.1f} ({adjusted_pitch - base_scores['pitch']:+.1f})")
        print(f"  节奏: {base_scores['rhythm']:.1f} -> {adjusted_rhythm:.1f} ({adjusted_rhythm - base_scores['rhythm']:+.1f})")
        print(f"  气息: {base_scores['breath']:.1f} -> {adjusted_breath:.1f} ({adjusted_breath - base_scores['breath']:+.1f})")
        print(f"  技术: {base_scores['technique']:.1f} -> {adjusted_technique:.1f} ({adjusted_technique - base_scores['technique']:+.1f})")
        print(f"  艺术: {base_scores['artistry']:.1f} -> {adjusted_artistry:.1f} ({adjusted_artistry - base_scores['artistry']:+.1f})")
        print(f"  总分: {total:.1f}")
        print(f"  权重: 音准{weights['pitch']*100:.0f}% 节奏{weights['rhythm']*100:.0f}% 气息{weights['breath']*100:.0f}% 技术{weights['technique']*100:.0f}% 艺术{weights['artistry']*100:.0f}%")


def test_real_audio():
    """测试真实音频的风格自适应评分"""
    print("\n" + "=" * 60)
    print("真实音频测试")
    print("=" * 60)

    audio_service = AudioService(config)
    score_service = ScoreServiceV4()

    test_files = [
        'tests/test_data/audio/vocal/恋人.mp3',
        'tests/test_data/audio/vocal/手写的从前.mp3'
    ]

    for filepath in test_files:
        if not os.path.exists(filepath):
            print(f"\n文件不存在: {filepath}")
            continue

        print(f"\n--- {filepath} ---")

        # 音频分析
        audio_result = audio_service.analyze(filepath)
        if not audio_result.success:
            print(f"  分析失败: {audio_result.error}")
            continue

        # 获取风格信息
        style = audio_result._music_style or 'unknown'
        style_cn = '未知'
        style_profile = getattr(audio_result, '_style_profile', None)
        if style_profile:
            style_cn = style_profile.style_cn

        mood = audio_result._music_mood or 'unknown'
        confidence = audio_result._style_confidence or 0

        print(f"  Style: {style} ({style_cn}) - {confidence*100:.1f}%")
        print(f"  Mood: {mood}")

        # 计算默认分数（无风格调整）
        from services.audio_features_service import AudioFeaturesResult
        advanced_features = audio_result._advanced_features
        if advanced_features is None:
            advanced_features = AudioFeaturesResult()

        default_result = score_service.calculate(
            features=advanced_features,
            emotion_confidence=0.5,
            emotions={},
            voice_quality_score=100.0,
            style_profile=None
        )

        # 计算风格自适应分数
        styled_result = score_service.calculate(
            features=advanced_features,
            emotion_confidence=0.5,
            emotions={},
            voice_quality_score=100.0,
            style_profile=style_profile,
            music_mood=mood
        )

        print(f"\n  默认评分:")
        print(f"    音准: {default_result.pitch_score:.1f}")
        print(f"    节奏: {default_result.rhythm_score:.1f}")
        print(f"    气息: {default_result.breath_score:.1f}")
        print(f"    技术: {default_result.technique_score:.1f}")
        print(f"    艺术: {default_result.artistry_score:.1f}")
        print(f"    总分: {default_result.total_score:.1f}")

        print(f"\n  风格自适应评分:")
        print(f"    音准: {styled_result.pitch_score:.1f} ({styled_result.pitch_score - default_result.pitch_score:+.1f})")
        print(f"    节奏: {styled_result.rhythm_score:.1f} ({styled_result.rhythm_score - default_result.rhythm_score:+.1f})")
        print(f"    气息: {styled_result.breath_score:.1f} ({styled_result.breath_score - default_result.breath_score:+.1f})")
        print(f"    技术: {styled_result.technique_score:.1f} ({styled_result.technique_score - default_result.technique_score:+.1f})")
        print(f"    艺术: {styled_result.artistry_score:.1f} ({styled_result.artistry_score - default_result.artistry_score:+.1f})")
        print(f"    总分: {styled_result.total_score:.1f} ({styled_result.total_score - default_result.total_score:+.1f})")


def test_mood_matching():
    """测试情绪匹配加分"""
    print("\n" + "=" * 60)
    print("情绪匹配测试")
    print("=" * 60)

    scorer = StyleAwareScorer()

    # 测试不同风格与情绪的组合
    test_cases = [
        (MusicStyle.BALLAD, 'romantic', '抒情歌 + 浪漫情绪'),
        (MusicStyle.BALLAD, 'happy', '抒情歌 + 欢快情绪'),
        (MusicStyle.FOLK, 'sentimental', '民谣 + 感性情绪'),
        (MusicStyle.ROCK, 'energetic', '摇滚 + 活力情绪'),
        (MusicStyle.ROCK, 'relaxing', '摇滚 + 放松情绪'),
        (MusicStyle.UPBEAT, 'happy', '快歌 + 欢快情绪'),
        (MusicStyle.RB_JAZZ, 'romantic', 'R&B + 浪漫情绪'),
    ]

    base_artistry = 70.0

    print(f"\n基础艺术表现分: {base_artistry:.1f}")
    print("\n情绪匹配效果:")

    for style, mood, desc in test_cases:
        profile = STYLE_PROFILES[style]
        adjusted = scorer.adjust_artistry_score(base_artistry, profile, mood)
        print(f"  {desc}: {base_artistry:.1f} -> {adjusted:.1f} ({adjusted - base_artistry:+.1f})")


if __name__ == '__main__':
    # 测试风格调整
    test_style_adjustments()

    # 测试情绪匹配
    test_mood_matching()

    # 测试真实音频
    test_real_audio()
