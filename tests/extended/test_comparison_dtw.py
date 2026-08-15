"""
单元测试 - 对比分析 DTW 对齐模块测试

测试 services/comparison 模块：
- DTWAligner: 三级DTW对齐
- BenchmarkService: 基准库预加工
- DeviationCalculator: 偏差计算
- ComparisonScoringService (DDD): 评分 (v7.19 E1 消双轨后唯一评分引擎)

核心验收标准：
- 相同音频得分 ≥ 95分
- 半音偏差音频得分 ≈ 60-70分
"""
import pytest
import numpy as np
from pathlib import Path
import tempfile
import os

from services.comparison.dtw_aligner import (
    DTWAligner,
    MultiFeatureSequence,
    AlignmentResult
)
from services.comparison.deviation_calculator import (
    DeviationCalculator,
    DeviationResult,
    FrameDeviation
)
from backend.domain.comparison.entities import DeviationData
from backend.domain.comparison.services import ComparisonScoringService


class TestDTWAligner:
    """DTW对齐器测试"""

    def setup_method(self):
        self.aligner = DTWAligner(sample_rate=22050, hop_length=512)

    def test_align_identical_audio(self):
        """测试相同音频的对齐 - 应该得到接近100%的置信度"""
        # 创建模拟特征
        n_frames = 100
        pitch = np.ones(n_frames) * 440.0
        energy = np.random.uniform(-30, -10, n_frames)
        zcr = np.random.uniform(0.01, 0.05, n_frames)
        times = np.arange(n_frames) * 512 / 22050

        features = MultiFeatureSequence(
            pitch=pitch,
            energy=energy,
            zcr=zcr,
            times=times,
            sample_rate=22050,
            hop_length=512
        )

        # 对齐相同音频
        result = self.aligner.align(features, features)

        assert isinstance(result, AlignmentResult)
        assert result.confidence > 0.8, f"相同音频置信度应>0.8, 实际: {result.confidence}"
        assert len(result.warp_path) > 0
        assert result.method in ['three_level_dtw', 'segment_based_dtw']

    def test_align_different_length_audio(self):
        """测试不同长度音频的对齐"""
        # 标准音频
        std_frames = 100
        std_features = MultiFeatureSequence(
            pitch=np.ones(std_frames) * 440.0,
            energy=np.random.uniform(-30, -10, std_frames),
            zcr=np.random.uniform(0.01, 0.05, std_frames),
            times=np.arange(std_frames) * 512 / 22050,
            sample_rate=22050,
            hop_length=512
        )

        # 用户音频（更长）
        user_frames = 150
        user_features = MultiFeatureSequence(
            pitch=np.ones(user_frames) * 440.0,
            energy=np.random.uniform(-30, -10, user_frames),
            zcr=np.random.uniform(0.01, 0.05, user_frames),
            times=np.arange(user_frames) * 512 / 22050,
            sample_rate=22050,
            hop_length=512
        )

        result = self.aligner.align(std_features, user_features)

        assert isinstance(result, AlignmentResult)
        assert len(result.warp_path) > 0

    def test_align_pitch_deviation(self):
        """测试有音高偏差的音频对齐"""
        n_frames = 100

        # 标准音频 (440Hz)
        std_features = MultiFeatureSequence(
            pitch=np.ones(n_frames) * 440.0,
            energy=np.zeros(n_frames),
            zcr=np.zeros(n_frames),
            times=np.arange(n_frames) * 512 / 22050,
            sample_rate=22050,
            hop_length=512
        )

        # 用户音频 (高半音，约466Hz)
        user_features = MultiFeatureSequence(
            pitch=np.ones(n_frames) * 466.16,  # A#4
            energy=np.zeros(n_frames),
            zcr=np.zeros(n_frames),
            times=np.arange(n_frames) * 512 / 22050,
            sample_rate=22050,
            hop_length=512
        )

        result = self.aligner.align(std_features, user_features)

        assert isinstance(result, AlignmentResult)
        # 即使音高不同，时间对齐仍应有效
        assert len(result.warp_path) > 0

    def test_extract_features_from_silent_audio(self):
        """测试从静音提取特征"""
        sr = 22050
        duration = 1.0
        y = np.zeros(int(sr * duration))

        features = self.aligner.extract_features_from_audio(y, sr)

        assert isinstance(features, MultiFeatureSequence)
        assert len(features.pitch) > 0
        assert len(features.energy) > 0
        # 静音的音高应该全是0或NaN处理后的0
        assert np.all(features.pitch == 0) or np.sum(features.pitch) == 0

    def test_detect_sentences(self):
        """测试句子检测"""
        n_frames = 200
        # 创建有能量变化的特征（模拟两个句子）
        energy = np.concatenate([
            np.random.uniform(-20, -10, 100),  # 第一句
            np.random.uniform(-40, -30, 10),   # 静音
            np.random.uniform(-20, -10, 90)    # 第二句
        ])

        features = MultiFeatureSequence(
            pitch=np.ones(n_frames) * 440.0,
            energy=energy,
            zcr=np.zeros(n_frames),
            times=np.arange(n_frames) * 512 / 22050,
            sample_rate=22050,
            hop_length=512
        )

        sentences = self.aligner._detect_sentences(features)

        assert len(sentences) >= 1  # 至少检测到一个句子
        # 每个句子应该是 (start, end) 元组
        for start, end in sentences:
            assert start < end


class TestDeviationCalculator:
    """偏差计算器测试"""

    def setup_method(self):
        self.calculator = DeviationCalculator(sample_rate=22050, hop_length=512)

    def test_calculate_identical_audio(self):
        """测试相同音频的偏差计算 - 偏差应为0"""
        n_frames = 100
        pitch = np.ones(n_frames) * 440.0
        energy = np.random.uniform(-30, -10, n_frames)

        # 对齐路径（完全对齐）
        warp_path = np.array([[i, i] for i in range(n_frames)])

        result = self.calculator.calculate(
            std_pitch=pitch,
            user_pitch=pitch,
            std_energy=energy,
            user_energy=energy,
            warp_path=warp_path
        )

        assert isinstance(result, DeviationResult)
        # 相同音频的音准偏差应该接近0
        assert result.avg_pitch_cents < 1.0, f"相同音频音分偏差应为0, 实际: {result.avg_pitch_cents}"

    def test_calculate_pitch_deviation(self):
        """测试音高偏差计算"""
        n_frames = 100
        std_pitch = np.ones(n_frames) * 440.0  # A4
        user_pitch = np.ones(n_frames) * 466.16  # A#4 (高半音)

        energy = np.zeros(n_frames)
        warp_path = np.array([[i, i] for i in range(n_frames)])

        result = self.calculator.calculate(
            std_pitch=std_pitch,
            user_pitch=user_pitch,
            std_energy=energy,
            user_energy=energy,
            warp_path=warp_path
        )

        # 半音约100音分
        assert 90 < result.avg_pitch_cents < 110, f"半音偏差应为~100cents, 实际: {result.avg_pitch_cents}"

    def test_problem_frame_detection(self):
        """测试问题帧检测"""
        n_frames = 100

        # 创建有问题的音频
        std_pitch = np.ones(n_frames) * 440.0
        user_pitch = std_pitch.copy()
        # 在某些帧添加大的音高偏差
        user_pitch[30:40] = 500.0  # 明显偏高

        energy = np.zeros(n_frames)
        warp_path = np.array([[i, i] for i in range(n_frames)])

        result = self.calculator.calculate(
            std_pitch=std_pitch,
            user_pitch=user_pitch,
            std_energy=energy,
            user_energy=energy,
            warp_path=warp_path
        )

        # 应该检测到问题帧
        assert len(result.problem_frames) > 0

    def test_calculate_pitch_cents(self):
        """测试音分计算"""
        # 测试相同频率
        cents = self.calculator._calculate_pitch_cents(440.0, 440.0)
        assert cents == 0.0

        # 测试高八度
        cents = self.calculator._calculate_pitch_cents(440.0, 880.0)
        assert 1190 < cents < 1210  # 应该约为1200音分

        # 测试半音
        cents = self.calculator._calculate_pitch_cents(440.0, 466.16)
        assert 90 < cents < 110  # 应该约为100音分

        # 测试无效值
        cents = self.calculator._calculate_pitch_cents(0.0, 440.0)
        assert cents == 0.0


class TestComparisonScoringDDD:
    """DDD 对比评分 (ComparisonScoringService) — v7.19 E1 消双轨后唯一评分引擎

    legacy services/comparison/scoring_engine.py 已删除, 评分统一走 DDD。
    """

    def setup_method(self):
        from backend.domain.comparison.services import ComparisonScoringService
        self.service = ComparisonScoringService()

    def test_score_identical_audio(self):
        """相同偏差 (全完美) → 总分 100 (≥95)"""
        dev = DeviationData()  # 默认全完美: 0 音分/0ms/0 音量/1.0 稳定
        result = self.service.score(dev, confidence=1.0)
        assert result.weighted_total() >= 95, \
            f"相同音频得分应≥95, 实际: {result.weighted_total()}"

    def test_score_large_deviation(self):
        """大偏差 → 总分 <70"""
        dev = DeviationData(
            avg_pitch_cents=100.0,
            max_pitch_cents=150.0,
            avg_rhythm_ms=200.0,
            avg_volume_percent=0.3,
            avg_breath_stability=0.5,
        )
        result = self.service.score(dev, confidence=1.0)
        assert result.weighted_total() < 70, \
            f"大偏差得分应<70, 实际: {result.weighted_total()}"

    def test_style_adaptive_weights(self):
        """风格权重单一来源: 各风格权重来自 ComparisonScoringService.STYLE_WEIGHTS"""
        from backend.domain.comparison.services import ComparisonScoringService
        weights = ComparisonScoringService.STYLE_WEIGHTS
        assert weights["pop"]["pitch"] == 0.40
        assert weights["classical"]["pitch"] == 0.50
        assert weights["rap"]["rhythm"] == 0.50

    def test_pitch_score_curve(self):
        """音准评分曲线 (分段线性, 与旧引擎行为一致)"""
        dev0 = DeviationData(avg_pitch_cents=0.0)
        dev50 = DeviationData(avg_pitch_cents=50.0)
        dev100 = DeviationData(avg_pitch_cents=100.0)
        assert self.service.score(dev0, confidence=1.0).pitch.score >= 95
        s50 = self.service.score(dev50, confidence=1.0).pitch.score
        s100 = self.service.score(dev100, confidence=1.0).pitch.score
        assert 60 < s50 < 90
        assert s100 < 50

    def test_suggestions_generation(self):
        """建议生成 (v7.19 E5: 复用 DDD AdviceGenerator, domain generate_suggestions 已删)"""
        from backend.application.assessment.advice_generator import AdviceGenerator
        adv = AdviceGenerator().generate(
            {'pitch_score': 80.0, 'rhythm_score': 70.0, 'volume_score': 75.0,
             'breath_score': 60.0, 'total_score': 72.0, 'total': 72.0},
            dimensions=('pitch', 'rhythm', 'volume', 'breath'),
        )
        # breath=60 最弱 (<75) → 应含针对性建议; 总体评价 (total 72) 亦在列
        assert len(adv.advice) >= 1
        assert any('建议' in s for s in adv.advice), (
            f"最弱维度应含改进建议, 实际 {adv.advice}"
        )


class TestIntegrationSameAudio:
    """集成测试：相同音频应该得到高分"""

    def test_same_audio_full_pipeline(self):
        """测试完整流水线：相同音频应得≥95分"""
        # 创建模拟音频特征
        n_frames = 200
        pitch = np.concatenate([
            np.ones(50) * 440.0,   # A4
            np.ones(50) * 493.88,  # B4
            np.ones(50) * 523.25,  # C5
            np.ones(50) * 440.0    # A4
        ])
        # 添加少量噪声
        pitch += np.random.normal(0, 2, n_frames)
        pitch = np.clip(pitch, 50, 1000)

        energy = np.random.uniform(-25, -15, n_frames)
        zcr = np.random.uniform(0.02, 0.04, n_frames)
        times = np.arange(n_frames) * 512 / 22050

        features = MultiFeatureSequence(
            pitch=pitch,
            energy=energy,
            zcr=zcr,
            times=times,
            sample_rate=22050,
            hop_length=512
        )

        # 1. 对齐
        aligner = DTWAligner()
        alignment = aligner.align(features, features)

        # 2. 计算偏差
        calculator = DeviationCalculator()
        deviation = calculator.calculate(
            std_pitch=features.pitch,
            user_pitch=features.pitch,
            std_energy=features.energy,
            user_energy=features.energy,
            warp_path=alignment.warp_path,
            std_times=features.times
        )

        # 3. 评分 (DDD ComparisonScoringService — v7.19 E1 唯一评分引擎)
        from backend.domain.comparison.entities import DeviationData
        from backend.domain.comparison.services import ComparisonScoringService
        dev = DeviationData(
            avg_pitch_cents=deviation.avg_pitch_cents,
            max_pitch_cents=deviation.max_pitch_cents,
            avg_rhythm_ms=deviation.avg_rhythm_ms,
            avg_volume_percent=deviation.avg_volume_percent,
            avg_breath_stability=deviation.avg_breath_stability,
            octave_error_rate=deviation.octave_error_rate,
            tempo_ratio=deviation.tempo_ratio,
        )
        scores = ComparisonScoringService().score(dev, confidence=alignment.confidence)

        # 验收标准：相同音频得分 ≥ 95分
        assert scores.weighted_total() >= 95, \
            f"相同音频得分应≥95, 实际: {scores.weighted_total()}"
        from backend.shared.domain_types import ScoreLevel
        level = ScoreLevel.from_score(scores.weighted_total()).label
        assert level in ['专业级', '优秀', '良好'], \
            f"相同音频等级应为专业级/优秀/良好, 实际: {level}"

        print(f"\n✅ 相同音频测试通过:")
        print(f"   得分: {scores.weighted_total()}")
        print(f"   等级: {level}")
        print(f"   置信度: {alignment.confidence}")


# ================================================================
# v7.18 P0 — 客观性/正确性修复回归 (C1 warp 分辨率 / C2 单位 / O1 voiced 掩码)
# ================================================================

class TestP0ObjectiveFixes:
    """P0 回归: 只评 23% 音频 (C1) / rhythm_ms 单位 4.3x (C2) / 无声帧稀释 (O1)"""

    def setup_method(self):
        self.aligner = DTWAligner(sample_rate=22050, hop_length=512)
        self.calculator = DeviationCalculator(sample_rate=22050, hop_length=512)

    def _features(self, n=200, freq=440.0, seed=0):
        rng = np.random.RandomState(seed)
        return MultiFeatureSequence(
            pitch=np.ones(n) * freq,
            energy=rng.uniform(-25, -15, n),
            zcr=np.zeros(n),
            times=np.arange(n) * 512 / 22050,
            sample_rate=22050,
            hop_length=512,
        )

    def test_c1_warp_path_covers_full_audio(self):
        """C1 CRITICAL: warp_path 应覆盖整首歌 (旧: 只到前 ~23%)"""
        feats = self._features(n=200)
        result = self.aligner.align(feats, feats)
        max_std = int(result.warp_path[:, 0].max())
        # 旧 bug: 10Hz 索引 max≈46/200=23%; 修复后应覆盖 ≥80%
        assert max_std > 0.8 * len(feats.pitch), \
            f"warp_path 应覆盖全歌, max_std={max_std}/{len(feats.pitch)} (旧 bug 只评前 23%)"

    def test_c2_rhythm_ms_uses_full_resolution_frame(self):
        """C2 CRITICAL: rhythm_ms = frame_diff × frame_duration (23.2ms), 非 10Hz 步长"""
        # warp_path 帧 5: std_idx-user_idx = 10 → 10 × 23.2ms = 232ms
        warp = np.array([[i + 10, i] for i in range(50)])  # std 恒超前 user 10 帧
        ms = self.calculator._calculate_rhythm_ms(5, warp)
        expected = 10 * (512 / 22050) * 1000  # 232ms
        assert abs(ms - expected) < 1.0, f"rhythm_ms={ms:.0f}ms, 应为 {expected:.0f}ms (非 4.3x 低估)"

    def test_o1_unvoiced_frames_excluded(self):
        """O1: 无声帧 (voiced=False) 不计入 avg_pitch_cents — 防稀释"""
        n = 100
        std_pitch = np.ones(n) * 440.0
        user_pitch = np.ones(n) * 440.0
        energy = np.zeros(n)
        warp = np.array([[i, i] for i in range(n)])
        std_voiced = np.ones(n, dtype=bool)
        user_voiced = np.ones(n, dtype=bool)
        # 前 50 帧用户无声 (但 pitch 有一八度偏差, 若被计入 avg 会巨大)
        user_voiced[:50] = False
        user_pitch[:50] = 880.0
        result = self.calculator.calculate(
            std_pitch, user_pitch, energy, energy, warp,
            std_voiced=std_voiced, user_voiced=user_voiced,
        )
        # 仅后 50 帧有声且偏差 0 → avg 应为 0
        assert result.avg_pitch_cents < 1.0, \
            f"无声帧不应计入平均, 实际 {result.avg_pitch_cents:.1f} (旧 bug: 无声帧 0 音分稀释)"

    def test_o1_all_unvoiced_safe(self):
        """O1: 全部无声帧 → 聚合安全不崩 (空列表 → 0)"""
        n = 20
        pitch = np.ones(n) * 440.0
        energy = np.zeros(n)
        warp = np.array([[i, i] for i in range(n)])
        result = self.calculator.calculate(
            pitch, pitch, energy, energy, warp,
            std_voiced=np.zeros(n, dtype=bool), user_voiced=np.zeros(n, dtype=bool),
        )
        assert result.avg_pitch_cents == 0.0

    def test_backward_compat_no_voiced_param(self):
        """向后兼容: 不传 voiced → 行为不变 (全部计入)"""
        n = 100
        std_pitch = np.ones(n) * 440.0
        user_pitch = np.ones(n) * 466.16  # 半音
        energy = np.zeros(n)
        warp = np.array([[i, i] for i in range(n)])
        result = self.calculator.calculate(std_pitch, user_pitch, energy, energy, warp)
        assert 90 < result.avg_pitch_cents < 110  # 半音 ~100c (与旧测试一致)


# ================================================================
# v7.18 P1 — 公正性回归 (F2 八度折叠 / F1 tempo 独立节奏)
# ================================================================

class TestP1FairnessFixes:
    """P1 公正性: 低八度不误伤 (F2) / 整体速度不惩罚节奏 (F1)"""

    def setup_method(self):
        self.calc = DeviationCalculator(sample_rate=22050, hop_length=512)

    def test_f2_fold_octave_unit(self):
        """F2: _fold_octave 把八度偏差折叠到 [-600, 600)"""
        assert self.calc._fold_octave(0.0) == 0.0
        assert self.calc._fold_octave(100.0) == 100.0   # 半音不变
        assert self.calc._fold_octave(-100.0) == -100.0
        assert abs(self.calc._fold_octave(1200.0)) < 0.01   # 低八度 → 0 (音级对)
        assert abs(self.calc._fold_octave(-1200.0)) < 0.01
        assert abs(self.calc._fold_octave(1300.0) - 100.0) < 0.01  # 八度+半音 → 半音

    def test_f2_octave_down_gets_credit(self):
        """F2: 用户低八度 (freq×0.5) → 折叠后偏差 ≈ 0 (音级匹配, 不误伤)"""
        raw = self.calc._calculate_pitch_cents(440.0, 220.0)
        assert abs(abs(raw) - 1200.0) < 1.0, f"低八度应 ≈1200c, 实际 {raw}"
        assert abs(self.calc._fold_octave(raw)) < 0.01, f"折叠后应 ≈0, 实际 {self.calc._fold_octave(raw)}"

    def test_f1_tempo_independent_residual(self):
        """F1: 整体速度不同 (快~11%) → 节奏偏差小 (tempo 已剥离), tempo_ratio 独立报告"""
        n = 100
        pitch = np.ones(n) * 440.0
        energy = np.zeros(n)
        warp = np.array([[int(i * 0.9), i] for i in range(90)])  # 用户快 ~11%
        result = self.calc.calculate(pitch, pitch, energy, energy, warp)
        assert result.tempo_ratio > 1.05, f"tempo_ratio 应≈1.11, 实际 {result.tempo_ratio}"
        assert result.avg_rhythm_ms < 100, \
            f"整体速度不应惩罚节奏, avg_rhythm_ms={result.avg_rhythm_ms:.0f}ms (旧对角线→巨大)"

    def test_f1_irregular_rhythm_penalized(self):
        """F1: 真节奏不准 (忽快忽慢 ±10 帧) → 残差大 → 节奏偏差大"""
        n = 100
        pitch = np.ones(n) * 440.0
        energy = np.zeros(n)
        warp = np.array([
            [i, i + (10 if i % 3 == 0 else -10 if i % 3 == 1 else 0)] for i in range(90)
        ])
        result = self.calc.calculate(pitch, pitch, energy, energy, warp)
        assert result.avg_rhythm_ms > 50, \
            f"节奏不准应产生偏差, avg_rhythm_ms={result.avg_rhythm_ms:.0f}ms"

    def test_f2_octave_error_rate_reported(self):
        """F2: 跨八度帧 → octave_error_rate 报告 (独立信号, 不并入折叠评分)"""
        n = 100
        std_pitch = np.ones(n) * 440.0
        user_pitch = np.ones(n) * 440.0
        energy = np.zeros(n)
        warp = np.array([[i, i] for i in range(n)])
        user_pitch[:40] = 220.0  # 前 40 帧低八度
        result = self.calc.calculate(std_pitch, user_pitch, energy, energy, warp)
        assert result.octave_error_rate > 0.3, f"八度错误率应≈0.4, 实际 {result.octave_error_rate}"
        assert result.avg_pitch_cents < 50, f"折叠后音准偏差应小, 实际 {result.avg_pitch_cents:.0f}c"

    def test_f2_octave_error_not_false_positive_on_big_error(self):
        """v7.19 整理: 601 音分 (三全音) 的普通大走音不应被误标为跨八度.
        旧阈值 abs(raw)>600 → 601~1199 全部误判 '跨八度 (属正常翻唱)', 掩盖真实走音。"""
        n = 100
        std_pitch = np.ones(n) * 440.0
        user_pitch = np.ones(n) * (440.0 * 2 ** (601 / 1200))  # ~622Hz, 601 音分
        energy = np.zeros(n)
        warp = np.array([[i, i] for i in range(n)])
        result = self.calc.calculate(std_pitch, user_pitch, energy, energy, warp)
        assert result.octave_error_rate == 0.0, \
            f"601c 不应判为跨八度, 实际 octave_error_rate={result.octave_error_rate}"
        # 但折叠后的音准偏差应反映这个大走音 (非 0)
        assert result.avg_pitch_cents > 500, f"601c 走音折叠后应仍是大偏差"

    def test_f2_octave_error_near_1200_detected(self):
        """v7.19 整理: 接近 1200 音分 (真跨八度) 仍应被判为八度错误"""
        n = 100
        std_pitch = np.ones(n) * 440.0
        user_pitch = np.ones(n) * (440.0 * 2 ** (1199 / 1200))  # ~880Hz, 1199 音分
        energy = np.zeros(n)
        warp = np.array([[i, i] for i in range(n)])
        result = self.calc.calculate(std_pitch, user_pitch, energy, energy, warp)
        assert result.octave_error_rate > 0.9, \
            f"1199c 接近真八度应判跨八度, 实际 {result.octave_error_rate}"


# ================================================================
# v7.18 P1 — F3 音量动态匹配 / O2 气息改进回归
# ================================================================

class TestP1VolumeBreath:
    """P1: 音量测动态形状非绝对电平 (F3) / 气息为能量动态 (O2)"""

    def setup_method(self):
        self.calc = DeviationCalculator(sample_rate=22050, hop_length=512)

    def test_f3_volume_gain_invariant(self):
        """F3: 录音增益差异 (能量整体 +12dB) → 音量偏差 ≈ 0 (z-score 消除电平)"""
        n = 100
        pitch = np.ones(n) * 440.0
        std_en = np.linspace(-30, -10, n)  # 动态包络 (形状)
        user_en_high_gain = std_en + 12.0  # 用户录音增益高 (录音条件差异)
        user_en_low_gain = std_en - 8.0    # 增益低
        warp = np.array([[i, i] for i in range(n)])
        r_hi = self.calc.calculate(pitch, pitch, std_en, user_en_high_gain, warp)
        r_lo = self.calc.calculate(pitch, pitch, std_en, user_en_low_gain, warp)
        # 相同动态形状 → 偏差应小 (旧: 绝对 dB 差 → 巨大)
        assert r_hi.avg_volume_percent < 0.3, f"高增益音量偏差应小, 实际 {r_hi.avg_volume_percent:.2f}"
        assert r_lo.avg_volume_percent < 0.3, f"低增益音量偏差应小, 实际 {r_lo.avg_volume_percent:.2f}"

    def test_f3_volume_shape_difference_penalized(self):
        """F3: 动态形状不同 (包络反转) → 音量偏差大"""
        n = 100
        pitch = np.ones(n) * 440.0
        std_en = np.linspace(-30, -10, n)
        user_en_diff = np.linspace(-10, -30, n)  # 反相包络 (动态形状不同)
        warp = np.array([[i, i] for i in range(n)])
        r = self.calc.calculate(pitch, pitch, std_en, user_en_diff, warp)
        assert r.avg_volume_percent > 0.5, f"动态形状不同应偏差大, 实际 {r.avg_volume_percent:.2f}"

    def test_f3_volume_score_curve(self):
        """F3: 评分 = (1 - 动态偏差) × 100 (DDD ComparisonScoringService)"""
        from backend.domain.comparison.services import ComparisonScoringService
        service = ComparisonScoringService()
        dev = DeviationData(avg_volume_percent=0.2)
        score = service.score(dev, confidence=1.0).volume.score
        assert score == pytest.approx(80.0, rel=0.05)  # (1-0.2)×100


# ================================================================
# v7.18 P2 — 鲁棒性回归 (S1 median 聚合 / F4 置信度重校准)
# ================================================================

class TestP2Robustness:
    """P2: 离群帧不拖偏 median / 置信度反映对齐可靠性"""

    def setup_method(self):
        self.calc = DeviationCalculator(sample_rate=22050, hop_length=512)
        self.aligner = DTWAligner(sample_rate=22050, hop_length=512)

    def test_s1_median_robust_to_outliers(self):
        """S1: 5% 离群帧 (536c) 不拖偏 median (77c vs mean ~101c)"""
        n = 100
        std_pitch = np.ones(n) * 440.0
        user_pitch = np.ones(n) * 460.0  # ~77 cents
        user_pitch[5:10] = 600.0  # 5% 离群帧 ~536 cents
        energy = np.zeros(n)
        warp = np.array([[i, i] for i in range(n)])
        result = self.calc.calculate(std_pitch, user_pitch, energy, energy, warp)
        # median 聚合 → 离群帧不拖偏
        assert result.avg_pitch_cents < 90, f"median 应稳定≈77, 实际 {result.avg_pitch_cents:.0f}"
        # 对照: 均值会被拖到 ~101
        all_cents = np.abs(self.calc._fold_octave(
            1200 * np.log2(user_pitch / std_pitch)
        ))
        assert np.mean(all_cents) > 95, "均值应被离群拖高 (对比 median 稳定)"

    def test_f4_confidence_identical_high(self):
        """F4: 相同音频置信度 ~1 (对齐可靠 → 高置信)"""
        feats = self._features(n=200)
        r_identical = self.aligner.align(feats, feats)
        assert r_identical.confidence > 0.9, f"相同音频置信度应高, 实际 {r_identical.confidence:.2f}"

    def test_f4_confidence_tempo_shift_kept_high(self):
        """F4: tempo 偏移 (内容相同, 速度不同) → 置信度保持高 (对齐可靠, 非内容不同)"""
        feats = self._features(n=200)
        # 时间拉伸 1.1x (唱快): 内容相同 → 回归残差小 → 置信度应仍高
        n_new = int(200 * 1.1)
        idx = np.linspace(0, 199, n_new)
        feats_stretched = MultiFeatureSequence(
            pitch=np.interp(idx, np.arange(200), feats.pitch),
            energy=np.interp(idx, np.arange(200), feats.energy),
            zcr=np.zeros(n_new),
            times=np.arange(n_new) * 512 / 22050,
            sample_rate=22050, hop_length=512,
        )
        r = self.aligner.align(feats, feats_stretched)
        assert r.confidence > 0.7, f"tempo 偏移对齐仍可靠, 置信度应高, 实际 {r.confidence:.2f}"

    def _features(self, n=200, freq=440.0, seed=0):
        rng = np.random.RandomState(seed)
        return MultiFeatureSequence(
            pitch=np.ones(n) * freq,
            energy=rng.uniform(-25, -15, n),
            zcr=np.zeros(n),
            times=np.arange(n) * 512 / 22050,
            sample_rate=22050,
            hop_length=512,
        )


class TestDTWFallbackConfidence:
    """v7.19 整理回归: DTW 对齐失败回退时置信度必须低.

    旧 bug: _global_align 捕获异常后回退线性缩放 warp_path (cost_matrix=None),
    而 _calculate_confidence 只基于线性路径回归残差 (≈0) → 置信度≈1.0,
    对齐失败被伪装成高置信度 (用户看不到对齐不可靠的信号)。
    """

    def _features(self, n=100):
        return MultiFeatureSequence(
            pitch=np.ones(n) * 440.0,
            energy=np.random.uniform(-30, -10, n),
            zcr=np.random.uniform(0.01, 0.05, n),
            times=np.arange(n) * 512 / 22050,
            sample_rate=22050,
            hop_length=512,
        )

    def test_alignment_failure_reports_low_confidence(self, monkeypatch):
        from services.comparison import dtw_aligner
        import services.comparison.dtw_aligner as aligner_mod

        def _boom(*args, **kwargs):
            raise RuntimeError("simulated librosa_dtw failure")

        monkeypatch.setattr(aligner_mod, "librosa_dtw", _boom)
        aligner = DTWAligner(sample_rate=22050, hop_length=512)
        result = aligner.align(self._features(), self._features())
        assert result.confidence < 0.5, \
            f"对齐失败回退置信度应低, 实际 {result.confidence:.3f} (旧实现≈1.0)"

    def test_empty_features_align_does_not_crash(self):
        """回退分支的空数组防护 — 不应 IndexError/ZeroDivisionError"""
        aligner = DTWAligner(sample_rate=22050, hop_length=512)
        empty = MultiFeatureSequence(
            pitch=np.array([]), energy=np.array([]), zcr=np.array([]),
            times=np.array([]), sample_rate=22050, hop_length=512,
        )
        result = aligner.align(empty, empty)
        # 空输入不应崩溃; 置信度低或为默认
        assert result.confidence >= 0.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
