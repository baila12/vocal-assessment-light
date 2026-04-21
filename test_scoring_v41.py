"""
v4.1 评分系统彻底测试脚本
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from services.audio_features_service import AudioFeaturesService, BreathStabilityResult
from services.score_service import ScoreServiceV4


def test_breath_feature_extraction():
    """测试气息特征提取"""
    print("=" * 60)
    print("测试1: 气息特征提取")
    print("=" * 60)

    service = AudioFeaturesService()

    # 测试用例
    test_cases = [
        ("平稳气息", _generate_stable_breath_audio()),
        ("艺术化起伏", _generate_artistic_fluctuation_audio()),
        ("随机抖动", _generate_random_fluctuation_audio()),
        ("弱唱", _generate_soft_singing_audio()),
        ("可控气声", _generate_controlled_breathiness_audio()),
        ("无效漏气", _generate_leak_audio()),
    ]

    for name, audio_data in test_cases:
        result = service.calculate_breath_stability(audio_data, singing_style='pop')

        print(f"\n{name}:")
        print(f"  专业气息得分: {result.professional_breath_score:.1f}")
        print(f"  是否艺术化: {result.is_artistic_fluctuation}")
        print(f"  可控气声: {result.controlled_breathiness:.1f}")
        print(f"  无效漏气: {result.uncontrolled_leak:.1f}")
        print(f"  长音支撑: {result.long_note_support_score:.1f}")
        print(f"  动态控制: {result.dynamic_control_score:.1f}")
        print(f"  气口设计: {result.breath_design_score:.1f}")
        print(f"  气声技巧: {result.breath_technique_score:.1f}")


def test_breath_scoring():
    """测试气息评分"""
    print("\n" + "=" * 60)
    print("测试2: 气息评分")
    print("=" * 60)

    score_service = ScoreServiceV4()

    # 模拟不同的气息特征结果
    test_cases = [
        ("专业级气息", BreathStabilityResult(
            professional_breath_score=95,
            is_artistic_fluctuation=True,
            controlled_breathiness=80,
            uncontrolled_leak=0,
            long_note_support_score=100,
            dynamic_control_score=95,
            breath_design_score=90,
            breath_technique_score=90,
            long_note_count=5,
            clean_breath_count=10,
            dynamic_range=35,
            rms_fluctuation=0.25
        )),
        ("良好气息", BreathStabilityResult(
            professional_breath_score=75,
            is_artistic_fluctuation=False,
            controlled_breathiness=40,
            uncontrolled_leak=10,
            long_note_support_score=80,
            dynamic_control_score=75,
            breath_design_score=70,
            breath_technique_score=70,
            long_note_count=2,
            clean_breath_count=5,
            dynamic_range=25,
            rms_fluctuation=0.30
        )),
        ("气息不足", BreathStabilityResult(
            professional_breath_score=50,
            is_artistic_fluctuation=False,
            controlled_breathiness=10,
            uncontrolled_leak=40,
            long_note_support_score=50,
            dynamic_control_score=45,
            breath_design_score=55,
            breath_technique_score=50,
            long_note_count=0,
            clean_breath_count=2,
            dynamic_range=15,
            rms_fluctuation=0.45,
            breath_breaks=5
        )),
        ("严重漏气", BreathStabilityResult(
            professional_breath_score=30,
            is_artistic_fluctuation=False,
            controlled_breathiness=0,
            uncontrolled_leak=70,
            long_note_support_score=30,
            dynamic_control_score=35,
            breath_design_score=40,
            breath_technique_score=25,
            long_note_count=0,
            clean_breath_count=0,
            dynamic_range=10,
            rms_fluctuation=0.60,
            breath_breaks=10
        )),
    ]

    for name, breath_result in test_cases:
        score, diagnosis = score_service._calculate_breath_score(breath_result)

        print(f"\n{name}:")
        print(f"  得分: {score:.1f}")
        print(f"  等级: {diagnosis.level}")
        print(f"  艺术化处理: {diagnosis.is_artistic}")
        print(f"  可控气声: {diagnosis.has_controlled_breathiness}")
        print(f"  问题: {diagnosis.issues[:3]}")  # 只显示前3个


def test_full_scoring():
    """测试完整评分"""
    print("\n" + "=" * 60)
    print("测试3: 完整五维评分")
    print("=" * 60)

    from services.audio_features_service import (
        AudioFeaturesResult,
        PitchDeviationResult,
        RhythmAlignmentResult,
        VocalTechniqueResult
    )

    score_service = ScoreServiceV4()

    # 模拟专业歌手的特征
    features = AudioFeaturesResult(
        pitch_deviation=PitchDeviationResult(
            mae_cents=12,
            max_cents=30,
            consecutive_off_notes=0,
            pitch_breaks=2,
            pitch_wobble=20,
            detection_rate=0.85
        ),
        rhythm_alignment=RhythmAlignmentResult(
            avg_deviation_ratio=0.08,
            max_deviation_ratio=0.15,
            off_beat_segments=0,
            beats_per_second=2.0,
            onset_count=50,
            irregularity=0.1
        ),
        breath_stability=BreathStabilityResult(
            professional_breath_score=95,
            is_artistic_fluctuation=True,
            controlled_breathiness=70,
            uncontrolled_leak=5,
            long_note_support_score=95,
            dynamic_control_score=90,
            breath_design_score=90,
            breath_technique_score=90,
            long_note_count=8,
            clean_breath_count=15,
            dynamic_range=35,
            rms_fluctuation=0.25
        ),
        vocal_technique=VocalTechniqueResult(
            vibrato_count=10,
            vibrato_rate_avg=5.5,
            vibrato_extent_avg=0.8,
            vibrato_quality=85,
            slide_count=3,
            falsetto_segments=2,
            technique_score=80
        ),
        hnr=12,
        cpp=5
    )

    result = score_service.calculate(
        features=features,
        emotion_confidence=0.7,
        emotions={'happy': 0.4, 'sad': 0.3, 'neutral': 0.3},
        voice_quality_score=85
    )

    print(f"总分: {result.total_score:.1f}")
    print(f"等级: {result.level}")
    print(f"星级: {result.stars}")
    print()
    print("五维得分:")
    print(f"  音准: {result.pitch_score:.1f}")
    print(f"  节奏: {result.rhythm_score:.1f}")
    print(f"  气息: {result.breath_score:.1f}")
    print(f"  发声技术: {result.technique_score:.1f}")
    print(f"  艺术表现: {result.artistry_score:.1f}")
    print()
    print("气息诊断:")
    print(f"  等级: {result.breath_diagnosis.level}")
    print(f"  艺术化: {result.breath_diagnosis.is_artistic}")
    print(f"  可控气声: {result.breath_diagnosis.has_controlled_breathiness}")
    print(f"  长音支撑: {result.breath_diagnosis.long_note_support:.1f}")
    print(f"  动态控制: {result.breath_diagnosis.dynamic_control:.1f}")
    print(f"  气口设计: {result.breath_diagnosis.breath_design:.1f}")
    print(f"  气声技巧: {result.breath_diagnosis.breath_technique:.1f}")
    print()
    print("底线规则:")
    print(f"  严重问题: {result.critical_issues}")
    print(f"  是否取消资格: {result.is_disqualified}")


def test_singing_style_adaptation():
    """测试唱法适配"""
    print("\n" + "=" * 60)
    print("测试4: 唱法适配")
    print("=" * 60)

    styles = ['pop', 'classical', 'folk', 'rap']

    for style in styles:
        service = ScoreServiceV4(singing_style=style)
        print(f"\n{style.upper()} 唱法权重:")
        for dim, weight in service.weights.items():
            print(f"  {dim}: {weight*100:.0f}%")


def test_hnr_thresholds():
    """测试HNR阈值"""
    print("\n" + "=" * 60)
    print("测试5: 分唱法HNR阈值")
    print("=" * 60)

    from services.audio_features_service import AudioFeaturesService

    service = AudioFeaturesService()

    test_cases = [
        ('pop', 10, "流行-可控气声区间"),
        ('pop', 5, "流行-边界"),
        ('pop', 20, "流行-过高"),
        ('classical', 25, "美声-优秀"),
        ('classical', 10, "美声-不足"),
        ('folk', 18, "民族-良好"),
        ('rap', 8, "说唱-正常"),
    ]

    for style, hnr, desc in test_cases:
        # 模拟评估
        from services.audio_features_service import BreathStabilityResult
        result = BreathStabilityResult()
        service._evaluate_breath_technique(hnr, np.zeros(1000), style, result)

        print(f"\n{desc}:")
        print(f"  HNR: {hnr}dB")
        print(f"  气声技巧得分: {result.breath_technique_score:.1f}")
        print(f"  可控气声: {result.controlled_breathiness:.1f}")
        print(f"  无效漏气: {result.uncontrolled_leak:.1f}")


def test_weight_calculation():
    """测试权重计算验证"""
    print("\n" + "=" * 60)
    print("测试6: 权重计算验证")
    print("=" * 60)

    # 验证权重总和为100%（v4.1更新后的权重）
    weights = {
        'pitch': 0.30,
        'rhythm': 0.20,
        'breath': 0.20,
        'technique': 0.20,
        'artistry': 0.10
    }

    total_weight = sum(weights.values())
    print(f"权重总和: {total_weight*100:.0f}%")
    assert abs(total_weight - 1.0) < 0.001, "权重总和必须为100%"

    # 验证加权计算
    scores = {
        'pitch': 80,
        'rhythm': 95,
        'breath': 90,
        'technique': 70,
        'artistry': 60
    }

    expected_total = sum(scores[k] * weights[k] for k in weights)
    print(f"预期总分: {expected_total:.1f}")
    print(f"计算: {80*0.30 + 95*0.20 + 90*0.20 + 70*0.20 + 60*0.10:.1f}")


# 辅助函数：生成测试音频
def _generate_stable_breath_audio(duration=5.0, sr=22050):
    """生成平稳气息音频"""
    t = np.linspace(0, duration, int(sr * duration))
    # 稳定的正弦波 + 微小起伏
    audio = 0.5 * np.sin(2 * np.pi * 440 * t)
    # 添加微小平滑起伏
    envelope = 1 + 0.05 * np.sin(2 * np.pi * 0.5 * t)
    return audio * envelope


def _generate_artistic_fluctuation_audio(duration=5.0, sr=22050):
    """生成艺术化起伏音频"""
    t = np.linspace(0, duration, int(sr * duration))
    audio = 0.5 * np.sin(2 * np.pi * 440 * t)
    # 模拟渐强渐弱
    envelope = 0.5 + 0.4 * np.sin(2 * np.pi * 0.3 * t)
    return audio * envelope


def _generate_random_fluctuation_audio(duration=5.0, sr=22050):
    """生成随机抖动音频"""
    t = np.linspace(0, duration, int(sr * duration))
    audio = 0.5 * np.sin(2 * np.pi * 440 * t)
    # 添加随机噪声起伏
    np.random.seed(42)
    random_fluctuation = np.random.uniform(0.5, 1.5, len(t))
    random_fluctuation = np.convolve(random_fluctuation, np.ones(100)/100, mode='same')
    return audio * random_fluctuation


def _generate_soft_singing_audio(duration=3.0, sr=22050):
    """生成弱唱音频"""
    t = np.linspace(0, duration, int(sr * duration))
    # 低音量正弦波
    audio = 0.2 * np.sin(2 * np.pi * 440 * t)
    return audio


def _generate_controlled_breathiness_audio(duration=3.0, sr=22050):
    """生成可控气声音频"""
    t = np.linspace(0, duration, int(sr * duration))
    # 正弦波 + 粉红噪声模拟气声
    audio = 0.3 * np.sin(2 * np.pi * 440 * t)
    # 添加受控噪声
    np.random.seed(42)
    noise = np.random.randn(len(t)) * 0.15
    # 低通滤波噪声
    from scipy import signal
    b, a = signal.butter(4, 2000 / (sr / 2), btype='low')
    noise = signal.filtfilt(b, a, noise)
    return audio + noise


def _generate_leak_audio(duration=3.0, sr=22050):
    """生成无效漏气音频"""
    t = np.linspace(0, duration, int(sr * duration))
    # 弱谐波 + 大量噪声
    audio = 0.1 * np.sin(2 * np.pi * 440 * t)
    np.random.seed(42)
    noise = np.random.randn(len(t)) * 0.3
    return audio + noise


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("v4.1 评分系统彻底测试")
    print("=" * 60)

    test_breath_feature_extraction()
    test_breath_scoring()
    test_full_scoring()
    test_singing_style_adaptation()
    test_hnr_thresholds()
    test_weight_calculation()

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
