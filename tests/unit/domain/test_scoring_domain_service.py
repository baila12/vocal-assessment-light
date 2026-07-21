"""ScoringDomainService TDD — 10 tests, EventBus integration"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../../..")

import pytest
from backend.domain.assessment.services import ScoringDomainService
from backend.domain.assessment.value_objects import (
    PitchScore, RhythmScore, BreathScore,
    TechniqueScore, MuscleStrengthScore, ArtistryScore, TimbreAdjustment,
)
from backend.domain.assessment.events import ScoreCalculated
from backend.shared.event_bus import EventBus


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


class TestScoringDomainService:
    def setup_method(self):
        self.service = ScoringDomainService()

    # 1. All 80 → total = 80.0
    def test_all_eighty_returns_eighty(self):
        result = self.service.calculate_total(
            make_pitch(80), make_rhythm(80), make_breath(80),
            make_technique(80), make_muscle(80), make_artistry(80),
        )
        assert result == 80.0

    # 2. Weight sum = 100% verification
    def test_weight_sum_is_100_percent(self):
        p = PitchScore(raw_score=100, mae_cents=0, rpa=1.0, rca=1.0,
                       gross_error_rate=0, octave_error_rate=0,
                       smoothness_cv=1.0, detection_rate=1.0, pitch_breaks=0)
        r = RhythmScore(raw_score=100, onset_cv=0, median_ioi_deviation=0,
                        irregularity_penalty=0, is_clean_vocal=False)
        b = BreathScore(raw_score=100, long_note_support=100, dynamic_control=100,
                        breath_design=100, breath_technique=100, is_clean_vocal=False)
        t = TechniqueScore(raw_score=100, articulation_clarity=100, breath_voice_ratio=100)
        m = MuscleStrengthScore(raw_score=100, body_muscle_strength=100,
                                facial_muscle_strength=100, is_heuristic=True)
        a = ArtistryScore(raw_score=100, vibrato_quality=100, dynamic_control=100,
                          phrase_expression=100, pitch_variation=100)
        result = self.service.calculate_total(p, r, b, t, m, a)
        assert result == 100.0  # 10+10+20+25+25+10 = 100

    # 3. Timbre bonus cap +3
    def test_timbre_bonus_capped_plus_3(self):
        timbre = TimbreAdjustment(adjustment=4.0, brightness_score=90.0,
                                  warmth_score=90.0, nasality_score=0.0, confidence=0.9)
        result = self.service.calculate_total(
            make_pitch(85), make_rhythm(85), make_breath(85),
            make_technique(85), make_muscle(85), make_artistry(85),
            timbre=timbre,
        )
        # base=85, adj clipped to +3 → 88
        assert result == 88.0

    # 4. Timbre penalty floor -5
    def test_timbre_penalty_floor_minus_5(self):
        timbre = TimbreAdjustment(adjustment=-7.0, brightness_score=10.0,
                                  warmth_score=10.0, nasality_score=80.0, confidence=0.9)
        result = self.service.calculate_total(
            make_pitch(85), make_rhythm(85), make_breath(85),
            make_technique(85), make_muscle(85), make_artistry(85),
            timbre=timbre,
        )
        # base=85, adj clipped to -5 → 80
        assert result == 80.0

    # 5. Low confidence → timbre zeroed
    def test_timbre_low_confidence_zero(self):
        timbre = TimbreAdjustment(adjustment=3.0, brightness_score=90.0,
                                  warmth_score=90.0, nasality_score=0.0, confidence=0.3)
        result = self.service.calculate_total(
            make_pitch(75), make_rhythm(75), make_breath(75),
            make_technique(75), make_muscle(75), make_artistry(75),
            timbre=timbre,
        )
        assert result == 75.0  # no adjustment

    # 6. EventBus: score_calculated event emitted
    def test_scoring_service_emits_score_calculated_event(self):
        events = []
        bus = EventBus()
        bus.subscribe(ScoreCalculated, lambda e: events.append(e))

        service = ScoringDomainService(event_bus=bus)
        result = service.calculate_total(
            make_pitch(80), make_rhythm(80), make_breath(80),
            make_technique(80), make_muscle(80), make_artistry(80),
        )

        assert len(events) == 1
        assert events[0].total_score == result
        assert events[0].dimensions["pitch"] == 80
        assert events[0].dimensions["muscle_strength"] == 80

    # 7. Level determination (from total_score)
    def test_level_mapping(self):
        assert ScoringDomainService.determine_level(90) == ("专业级", "S", "#22c55e")
        assert ScoringDomainService.determine_level(80) == ("优秀", "A", "#3b82f6")
        assert ScoringDomainService.determine_level(65) == ("良好", "B", "#10b981")
        assert ScoringDomainService.determine_level(50) == ("中等", "C", "#f59e0b")
        assert ScoringDomainService.determine_level(30) == ("及格", "D", "#f97316")
        assert ScoringDomainService.determine_level(10) == ("待改进", "E", "#ef4444")

    # 8. Total clamp [0, 100] (without timbre)
    def test_total_clamped(self):
        result_high = self.service.calculate_total(
            make_pitch(100), make_rhythm(100), make_breath(100),
            make_technique(100), make_muscle(100), make_artistry(100),
        )
        assert result_high <= 100
        assert result_high == 100.0

        result_low = self.service.calculate_total(
            make_pitch(0), make_rhythm(0), make_breath(0),
            make_technique(0), make_muscle(0), make_artistry(0),
        )
        assert result_low >= 0
        assert result_low == 0.0

    # 9. Event details match
    def test_event_details_match(self):
        events = []
        bus = EventBus()
        bus.subscribe(ScoreCalculated, lambda e: events.append(e))
        service = ScoringDomainService(event_bus=bus)

        service.calculate_total(
            make_pitch(55), make_rhythm(50), make_breath(55),
            make_technique(50), make_muscle(45), make_artistry(40),
        )

        assert len(events) == 1
        e = events[0]
        assert e.dimensions["pitch"] == 55
        assert e.dimensions["rhythm"] == 50
        assert e.dimensions["breath"] == 55
        assert e.dimensions["technique"] == 50
        assert e.dimensions["muscle_strength"] == 45
        assert e.dimensions["artistry"] == 40
        assert e.timbre_adjustment == 0.0
        assert e.grade == "C"

    # 10. Without event_bus, no crash
    def test_no_event_bus_no_crash(self):
        service = ScoringDomainService(event_bus=None)
        result = service.calculate_total(
            make_pitch(80), make_rhythm(80), make_breath(80),
            make_technique(80), make_muscle(80), make_artistry(80),
        )
        assert result == 80.0
