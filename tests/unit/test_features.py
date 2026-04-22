"""
单元测试 - 音频特征分析器测试
测试 services/features 模块的各维度分析器
"""
import pytest
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.features import (
    PitchDeviationResult,
    RhythmAlignmentResult,
    BreathStabilityResult,
    VocalTechniqueResult,
    AudioFeaturesResult,
    PitchAnalyzer,
    RhythmAnalyzer,
    BreathAnalyzer,
    TechniqueAnalyzer,
    AcousticAnalyzer
)


class TestPitchAnalyzer:
    """音准分析器测试"""

    def setup_method(self):
        self.sample_rate = 22050
        self.hop_length = 512
        self.analyzer = PitchAnalyzer(self.sample_rate, self.hop_length)

    def test_analyze_with_f0(self):
        """测试使用 f0 数据的音准分析"""
        # 创建模拟的 f0 数据（440Hz 稳定音高）
        frames = 100
        f0 = np.ones(frames) * 440.0
        voiced_flags = np.ones(frames, dtype=bool)

        result = self.analyzer.calculate_pitch_deviation_cents(f0, voiced_flags)

        assert isinstance(result, PitchDeviationResult)
        assert result.mae_cents >= 0
        assert result.detection_rate > 0

    def test_analyze_silent_audio(self):
        """测试静音（无声帧）"""
        frames = 100
        f0 = np.zeros(frames)
        voiced_flags = np.zeros(frames, dtype=bool)

        result = self.analyzer.calculate_pitch_deviation_cents(f0, voiced_flags)

        assert isinstance(result, PitchDeviationResult)
        # 静音情况下检测率应该很低
        assert result.detection_rate == 0

    def test_mae_cents_calculation(self):
        """测试音分偏差计算"""
        result = PitchDeviationResult(
            mae_cents=50.0,
            detection_rate=0.9,
            pitch_breaks=0,
            pitch_wobble=15.0,
            consecutive_off_notes=0
        )

        assert result.mae_cents == 50.0


class TestRhythmAnalyzer:
    """节奏分析器测试"""

    def setup_method(self):
        self.sample_rate = 22050
        self.hop_length = 512
        self.analyzer = RhythmAnalyzer(self.sample_rate, self.hop_length)

    def test_analyze_rhythmic_audio(self):
        """测试有节奏的音频"""
        # 生成简单的节拍音频（每0.5秒一个脉冲）
        duration = 4.0
        sample_count = int(self.sample_rate * duration)
        audio_data = np.zeros(sample_count)

        # 添加节拍脉冲
        beat_interval = int(0.5 * self.sample_rate)
        for i in range(0, sample_count, beat_interval):
            pulse_length = int(0.05 * self.sample_rate)
            end = min(i + pulse_length, sample_count)
            audio_data[i:end] = 0.5

        result = self.analyzer.calculate_rhythm_alignment(audio_data)

        assert isinstance(result, RhythmAlignmentResult)
        assert result.avg_deviation_ratio >= 0
        assert result.beats_per_second > 0
        assert result.onset_count > 0

    def test_analyze_silent_audio(self):
        """测试静音"""
        audio_data = np.zeros(self.sample_rate * 2)

        result = self.analyzer.calculate_rhythm_alignment(audio_data)

        assert isinstance(result, RhythmAlignmentResult)
        # 静音情况下节拍应该很少
        assert result.onset_count == 0 or result.beats_per_second == 0


class TestBreathAnalyzer:
    """气息分析器测试"""

    def setup_method(self):
        self.sample_rate = 22050
        self.hop_length = 512
        self.analyzer = BreathAnalyzer(self.sample_rate, self.hop_length)

    def test_analyze_stable_breath(self):
        """测试稳定气息"""
        # 生成稳定的音频（模拟稳定气息支撑）
        duration = 3.0
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        # 稳定的正弦波
        audio_data = 0.5 * np.sin(2 * np.pi * 440 * t)

        result = self.analyzer.calculate_breath_stability(audio_data)

        assert isinstance(result, BreathStabilityResult)
        assert result.rms_fluctuation >= 0
        assert result.breath_breaks >= 0
        assert 0 <= result.professional_breath_score <= 100

    def test_analyze_fluctuating_breath(self):
        """测试波动的气息"""
        duration = 3.0
        sample_count = int(self.sample_rate * duration)
        t = np.linspace(0, duration, sample_count)

        # 创建波动较大的音频
        envelope = 0.3 + 0.5 * np.sin(2 * np.pi * 2 * t)  # 2Hz 波动
        audio_data = envelope * np.sin(2 * np.pi * 440 * t)

        result = self.analyzer.calculate_breath_stability(audio_data)

        assert isinstance(result, BreathStabilityResult)
        # 波动应该较高
        assert result.rms_fluctuation > 0.1


class TestTechniqueAnalyzer:
    """发声技巧分析器测试"""

    def setup_method(self):
        self.sample_rate = 22050
        self.hop_length = 512
        self.analyzer = TechniqueAnalyzer(self.sample_rate, self.hop_length)

    def test_analyze_simple_tone(self):
        """测试简单音调"""
        duration = 2.0
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        audio_data = 0.5 * np.sin(2 * np.pi * 440 * t)

        # 创建稳定的 f0
        frames = 200
        f0 = np.ones(frames) * 440.0

        result = self.analyzer.detect_vocal_techniques(f0, audio_data)

        assert isinstance(result, VocalTechniqueResult)
        assert 0 <= result.technique_score <= 100
        assert result.vibrato_count >= 0
        assert result.vibrato_quality >= 0

    def test_vibrato_detection(self):
        """测试颤音检测"""
        duration = 2.0
        sample_count = int(self.sample_rate * duration)
        t = np.linspace(0, duration, sample_count)

        # 创建带颤音的音频（频率调制）
        vibrato_rate = 5.0  # 5Hz 颤音
        vibrato_depth = 10  # 音分
        mod_freq = 440 * (2 ** (vibrato_depth * np.sin(2 * np.pi * vibrato_rate * t) / 1200))
        phase = np.cumsum(2 * np.pi * mod_freq / self.sample_rate)
        audio_data = 0.5 * np.sin(phase)

        # 创建带颤音的 f0（模拟频率调制）
        frames = 200
        frame_times = np.linspace(0, duration, frames)
        f0 = 440 * (2 ** (vibrato_depth * np.sin(2 * np.pi * vibrato_rate * frame_times) / 1200))

        result = self.analyzer.detect_vocal_techniques(f0, audio_data)

        assert isinstance(result, VocalTechniqueResult)

    def test_empty_f0(self):
        """测试空 f0 数据"""
        audio_data = np.zeros(self.sample_rate * 2)
        f0 = np.array([])

        result = self.analyzer.detect_vocal_techniques(f0, audio_data)

        assert isinstance(result, VocalTechniqueResult)
        assert result.technique_score == 0


class TestAcousticAnalyzer:
    """声学特征分析器测试"""

    def setup_method(self):
        self.sample_rate = 22050
        self.hop_length = 512
        self.analyzer = AcousticAnalyzer(self.sample_rate, self.hop_length)

    def test_hnr_calculation(self):
        """测试 HNR 计算"""
        # 创建干净的谐波信号
        duration = 1.0
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        # 基频 + 泛音
        audio_data = (
            0.5 * np.sin(2 * np.pi * 440 * t) +
            0.3 * np.sin(2 * np.pi * 880 * t) +
            0.2 * np.sin(2 * np.pi * 1320 * t)
        )

        hnr = self.analyzer.calculate_hnr(audio_data)

        assert isinstance(hnr, float)
        assert hnr >= 0
        # 干净谐波信号应该有较高的 HNR
        assert hnr > 5

    def test_cpp_calculation(self):
        """测试 CPP 计算"""
        duration = 1.0
        t = np.linspace(0, duration, int(self.sample_rate * duration))
        audio_data = 0.5 * np.sin(2 * np.pi * 440 * t)

        cpp = self.analyzer.calculate_cpp(audio_data)

        assert isinstance(cpp, float)
        # CPP 可以是负值或正值
        assert -10 <= cpp <= 10

    def test_silent_audio_hnr(self):
        """测试静音 HNR"""
        audio_data = np.zeros(self.sample_rate)

        hnr = self.analyzer.calculate_hnr(audio_data)

        # 静音情况下 HNR 应该很低或为0
        assert hnr >= 0


class TestAudioFeaturesResult:
    """音频特征结果 DTO 测试"""

    def test_create_default_result(self):
        """测试创建默认结果"""
        result = AudioFeaturesResult()

        assert result.hnr == 0.0
        assert result.cpp == 0.0
        assert isinstance(result.pitch_deviation, PitchDeviationResult)
        assert isinstance(result.rhythm_alignment, RhythmAlignmentResult)
        assert isinstance(result.breath_stability, BreathStabilityResult)
        assert isinstance(result.vocal_technique, VocalTechniqueResult)

    def test_result_with_values(self):
        """测试带值的结果"""
        pitch = PitchDeviationResult(
            mae_cents=25.0,
            detection_rate=0.9,
            pitch_breaks=1,
            pitch_wobble=15.0,
            consecutive_off_notes=0
        )
        rhythm = RhythmAlignmentResult(
            avg_deviation_ratio=0.15,
            irregularity=0.2,
            beats_per_second=2.0,
            onset_count=100,
            off_beat_segments=10
        )

        result = AudioFeaturesResult(
            hnr=15.0,
            cpp=1.2,
            pitch_deviation=pitch,
            rhythm_alignment=rhythm
        )

        assert result.hnr == 15.0
        assert result.cpp == 1.2
        assert result.pitch_deviation.mae_cents == 25.0
        assert result.rhythm_alignment.avg_deviation_ratio == 0.15

    def test_result_error_state(self):
        """测试错误状态"""
        result = AudioFeaturesResult(
            success=False,
            error_message="分析失败"
        )

        assert result.success is False
        assert result.error_message == "分析失败"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
