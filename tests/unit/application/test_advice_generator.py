"""
P2-15 Phase 1 — AdviceGenerator (DDD application 层) 行为契约

从 legacy services/advice_service.py 移植 (消除"建议生成 100% legacy"):
- 消费 calculate_ddd 六维分数 dict → 排序找最强/最弱维度
- 总体评价分档 (>=90/>=85/>=80/>=70/>=60/<60)
- 最弱 <75 给改进建议; 最强 >=90 给表扬
- 输出 AdviceResult(advice, strongest_dimension, weakest_dimension)
"""

import pytest

from backend.application.assessment.advice_generator import AdviceGenerator, AdviceResult


def _scores(**overrides):
    """构造六维分数 dict (calculate_ddd 产物字段名, 含 total 兼容键)"""
    base = {
        "pitch_score": 80.0,
        "rhythm_score": 70.0,
        "breath_score": 75.0,
        "technique_score": 60.0,
        "muscle_strength_score": 85.0,
        "artistry_score": 90.0,
        "total_score": 77.0,
    }
    base.update(overrides)
    # calculate_ddd 产物含 total 兼容键 (result["total"] = result["total_score"])
    base["total"] = base["total_score"]
    return base


class TestAdviceGeneratorStructure:
    def test_generate_returns_advice_result(self):
        gen = AdviceGenerator()
        result = gen.generate(_scores())
        assert isinstance(result, AdviceResult)
        assert isinstance(result.advice, list)
        assert result.strongest_dimension in ("pitch", "rhythm", "breath",
                                              "technique", "muscle_strength", "artistry")
        assert result.weakest_dimension in ("pitch", "rhythm", "breath",
                                            "technique", "muscle_strength", "artistry")

    def test_generate_accepts_dict_and_returns_advice_list(self):
        gen = AdviceGenerator()
        result = gen.generate(_scores())
        assert len(result.advice) >= 1  # 至少含总体评价


class TestAdviceStrongestWeakest:
    def test_strongest_and_weakest_detected(self):
        gen = AdviceGenerator()
        # artistry=90 最强, technique=60 最弱
        result = gen.generate(_scores())
        assert result.strongest_dimension == "artistry"
        assert result.weakest_dimension == "technique"

    def test_strongest_ties_resolve_consistently(self):
        gen = AdviceGenerator()
        # pitch 与 artistry 同为 90 → 排序靠前者胜 (sorted reverse, dict 顺序稳定)
        result = gen.generate(_scores(pitch_score=90.0))
        assert result.strongest_dimension == "pitch"


class TestAdviceTiers:
    @pytest.mark.parametrize("total,keyword", [
        (95, "优秀表现"),
        (88, "整体良好"),
        (82, "整体表现良好"),
        (75, "水平中等"),
        (65, "基础尚可"),
        (50, "需要加强练习"),
    ])
    def test_overall_comment_tiers(self, total, keyword):
        gen = AdviceGenerator()
        result = gen.generate(_scores(total_score=total))
        assert any(keyword in a for a in result.advice), (
            f"total={total} 应含 '{keyword}' 评价, 实际 {result.advice}"
        )

    def test_weakest_below_75_adds_improvement_tip(self):
        gen = AdviceGenerator()
        result = gen.generate(_scores())  # technique=60 < 75
        assert any("技术建议" in a for a in result.advice), (
            f"最弱维度 <75 应含改进建议, 实际 {result.advice}"
        )

    def test_weakest_at_or_above_75_no_tip(self):
        gen = AdviceGenerator()
        # 所有维度 >=75 (技术 78 仍是最弱但 >=75) → 不应有改进建议
        result = gen.generate(_scores(technique_score=78.0, rhythm_score=80.0,
                                      breath_score=80.0, pitch_score=85.0))
        assert not any("建议：" in a for a in result.advice), (
            f"最弱 >=75 不应有改进建议, 实际 {result.advice}"
        )

    def test_strongest_at_or_above_90_adds_praise(self):
        gen = AdviceGenerator()
        result = gen.generate(_scores())  # artistry=90 >= 90
        assert any("艺术表现力出色" in a for a in result.advice), (
            f"最强 >=90 应含表扬, 实际 {result.advice}"
        )

    def test_strongest_below_90_no_praise(self):
        gen = AdviceGenerator()
        result = gen.generate(_scores(artistry_score=89.0))
        assert not any("出色" in a and "艺术" in a for a in result.advice), (
            f"最强 <90 不应有表扬, 实际 {result.advice}"
        )

    def test_advice_contains_strongest_dimension_name(self):
        gen = AdviceGenerator()
        result = gen.generate(_scores())
        # 总体评价应提及最强维度 (artistry → 艺术表现)
        assert any("艺术表现" in a for a in result.advice)
