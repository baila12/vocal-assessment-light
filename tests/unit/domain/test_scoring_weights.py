"""ScoringWeights TDD — 六维权重值对象 (单一数据来源)"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../../..")

import pytest
from backend.domain.assessment.scoring_weights import (
    ScoringWeights,
    WeightsValidationError,
)
from backend.domain.assessment.value_objects import (
    PitchScore, RhythmScore, BreathScore,
    TechniqueScore, MuscleStrengthScore, ArtistryScore,
)


def make_pitch(score: float = 80.0) -> PitchScore:
    return PitchScore(raw_score=score, mae_cents=10.0, rpa=0.9, rca=0.9,
                      gross_error_rate=0.01, octave_error_rate=0.01,
                      smoothness_cv=1.2, detection_rate=0.95, pitch_breaks=0)

def make_rhythm(score: float = 80.0) -> RhythmScore:
    return RhythmScore(raw_score=score, onset_cv=0.12, median_ioi_deviation=0.05,
                       irregularity_penalty=0.0, is_clean_vocal=False)

def make_breath(score: float = 80.0) -> BreathScore:
    return BreathScore(raw_score=score, long_note_support=75.0, dynamic_control=70.0,
                       breath_design=65.0, breath_technique=60.0, is_clean_vocal=False)

def make_technique(score: float = 80.0) -> TechniqueScore:
    return TechniqueScore(raw_score=score, articulation_clarity=75.0, breath_voice_ratio=78.0)

def make_muscle(score: float = 80.0) -> MuscleStrengthScore:
    return MuscleStrengthScore(raw_score=score, body_muscle_strength=78.0,
                               facial_muscle_strength=82.0, is_heuristic=True)

def make_artistry(score: float = 80.0) -> ArtistryScore:
    return ArtistryScore(raw_score=score, vibrato_quality=75.0, dynamic_control=70.0,
                         phrase_expression=65.0, pitch_variation=60.0)


class TestScoringWeightsDefault:
    """默认权重 = v7.4 定稿 13/12/22/25/15/13"""

    def test_default_weights_match_v7_4(self):
        w = ScoringWeights.default()
        assert w.pitch == pytest.approx(0.13)
        assert w.rhythm == pytest.approx(0.12)
        assert w.breath == pytest.approx(0.22)
        assert w.technique == pytest.approx(0.25)
        assert w.muscle == pytest.approx(0.15)
        assert w.artistry == pytest.approx(0.13)

    def test_default_sum_is_100_percent(self):
        assert ScoringWeights.default().sum() == pytest.approx(1.0)

    def test_default_passes_validation(self):
        ScoringWeights.default().validate()


class TestScoringWeightsValidation:
    def test_valid_weights_pass(self):
        ScoringWeights(pitch=0.1, rhythm=0.1, breath=0.2,
                       technique=0.25, muscle=0.25, artistry=0.1).validate()

    def test_sum_must_be_100_percent(self):
        w = ScoringWeights(pitch=0.3, rhythm=0.3, breath=0.25,
                           technique=0.2, artistry=0.1, muscle=0.0)
        with pytest.raises(WeightsValidationError, match="100"):
            w.validate()

    def test_single_dimension_max_50_percent(self):
        w = ScoringWeights(pitch=0.55, rhythm=0.1, breath=0.1,
                           technique=0.1, muscle=0.1, artistry=0.05)
        with pytest.raises(WeightsValidationError, match="50%|0.5"):
            w.validate()

    def test_negative_weight_rejected(self):
        w = ScoringWeights(pitch=-0.1, rhythm=0.1, breath=0.2,
                           technique=0.25, muscle=0.25, artistry=0.3)
        with pytest.raises(WeightsValidationError, match="负数|negative|0"):
            w.validate()

    def test_validate_returns_self_for_chaining(self):
        assert ScoringWeights.default().validate() is not None


class TestScoringWeightsAggregation:
    """加权聚合 — 六维总分 (不含音色)"""

    def test_weighted_total_all_eighty(self):
        w = ScoringWeights.default()
        total = w.weighted_total(
            make_pitch(80), make_rhythm(80), make_breath(80),
            make_technique(80), make_muscle(80), make_artistry(80),
        )
        assert total == pytest.approx(80.0)

    def test_weighted_total_matches_v7_4_math(self):
        # 各维 100 分 → 总分 = 13+12+22+25+15+13 = 100
        w = ScoringWeights.default()
        total = w.weighted_total(
            make_pitch(100), make_rhythm(100), make_breath(100),
            make_technique(100), make_muscle(100), make_artistry(100),
        )
        assert total == pytest.approx(100.0)

    def test_custom_weights_change_total(self):
        # 只用 pitch(1.0) → 总分 = pitch 分数
        w = ScoringWeights(pitch=1.0, rhythm=0.0, breath=0.0,
                           technique=0.0, muscle=0.0, artistry=0.0)
        total = w.weighted_total(
            make_pitch(90), make_rhythm(80), make_breath(80),
            make_technique(80), make_muscle(80), make_artistry(80),
        )
        assert total == pytest.approx(90.0)


class TestStylePresets:
    """scoring-config.feature: 四种风格预设 — 6 维适配 (原 5 维 ×0.85 + muscle 15%)"""

    def test_all_presets_sum_to_100(self):
        for name, w in ScoringWeights.presets().items():
            assert w.sum() == pytest.approx(1.0), f"{name} sum != 100%"
            w.validate()

    def test_presets_includes_four_styles(self):
        p = ScoringWeights.presets()
        assert set(p.keys()) == {"pop", "bel_canto", "ethnic", "rap"}

    def test_pop_preset_values(self):
        w = ScoringWeights.pop()
        assert w.pitch == pytest.approx(0.21)
        assert w.rhythm == pytest.approx(0.17)
        assert w.breath == pytest.approx(0.13)
        assert w.technique == pytest.approx(0.17)
        assert w.muscle == pytest.approx(0.15)
        assert w.artistry == pytest.approx(0.17)

    def test_bel_canto_preset_values(self):
        w = ScoringWeights.bel_canto()
        assert w.pitch == pytest.approx(0.25)
        assert w.rhythm == pytest.approx(0.13)
        assert w.breath == pytest.approx(0.21)
        assert w.technique == pytest.approx(0.17)
        assert w.muscle == pytest.approx(0.15)
        assert w.artistry == pytest.approx(0.09)

    def test_rap_preset_rhythm_heavy(self):
        w = ScoringWeights.rap()
        assert w.rhythm > w.pitch
        assert w.rhythm == pytest.approx(0.30)
        assert w.pitch == pytest.approx(0.08)

    def test_ethnic_preset_balanced(self):
        w = ScoringWeights.ethnic()
        dims = [w.pitch, w.rhythm, w.breath, w.technique, w.artistry]
        assert max(dims) - min(dims) <= 0.10

    def test_default_preset_is_pop(self):
        assert ScoringWeights.default_preset_name() == "pop"

    def test_from_preset_unknown_raises(self):
        with pytest.raises(WeightsValidationError):
            ScoringWeights.from_preset("jazz")


class TestWeightedTotalFromScores:
    """从原始分数字典计算加权总分 — API apply-weights 纯重算用"""

    def test_default_weights_from_scores(self):
        w = ScoringWeights.default()
        total = w.weighted_total_from_scores({
            "pitch": 80, "rhythm": 80, "breath": 80,
            "technique": 80, "muscle": 80, "artistry": 80,
        })
        assert total == pytest.approx(80.0)

    def test_custom_weights_from_scores(self):
        w = ScoringWeights(pitch=1.0, rhythm=0.0, breath=0.0,
                           technique=0.0, muscle=0.0, artistry=0.0)
        total = w.weighted_total_from_scores({
            "pitch": 90, "rhythm": 50, "breath": 50,
            "technique": 50, "muscle": 50, "artistry": 50,
        })
        assert total == pytest.approx(90.0)

    def test_rap_preset_from_scores(self):
        w = ScoringWeights.rap()
        total = w.weighted_total_from_scores({
            "pitch": 90, "rhythm": 50, "breath": 70,
            "technique": 70, "muscle": 70, "artistry": 70,
        })
        # 0.08*90 + 0.30*50 + 0.09*70 + 0.13*70 + 0.15*70 + 0.25*70
        expected = 0.08*90 + 0.30*50 + 0.09*70 + 0.13*70 + 0.15*70 + 0.25*70
        assert total == pytest.approx(expected)


class TestScoringWeightsSerialization:
    def test_to_dict(self):
        w = ScoringWeights.default()
        d = w.to_dict()
        assert set(d.keys()) == {"pitch", "rhythm", "breath", "technique", "muscle", "artistry"}
        assert d["pitch"] == pytest.approx(0.13)

    def test_from_dict_roundtrip(self):
        d = {"pitch": 0.1, "rhythm": 0.1, "breath": 0.2,
             "technique": 0.25, "muscle": 0.25, "artistry": 0.1}
        w = ScoringWeights.from_dict(d)
        assert w.sum() == pytest.approx(1.0)
        assert w.pitch == pytest.approx(0.1)

    def test_from_dict_validates(self):
        with pytest.raises(WeightsValidationError):
            ScoringWeights.from_dict({"pitch": 0.9, "rhythm": 0.0, "breath": 0.0,
                                      "technique": 0.0, "muscle": 0.0, "artistry": 0.0})
