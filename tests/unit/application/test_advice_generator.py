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


class TestAdviceDimensionSubset:
    """v7.19 E5: generate() 支持 dimensions 子集 (对比四维 pitch/rhythm/volume/breath)"""

    def _compare_scores(self, **overrides):
        base = {
            "pitch_score": 85.0,
            "rhythm_score": 70.0,
            "volume_score": 90.0,
            "breath_score": 60.0,
            "total_score": 77.0,
        }
        base.update(overrides)
        base["total"] = base["total_score"]
        return base

    def test_dimensions_subset_only_uses_given_dims(self):
        """dimensions 限定后, 最强/最弱仅在子集内判定 (volume 参与, 六维无关维度忽略)"""
        gen = AdviceGenerator()
        result = gen.generate(
            self._compare_scores(),
            dimensions=("pitch", "rhythm", "volume", "breath"),
        )
        assert result.strongest_dimension == "volume", (
            f"子集内 volume=90 应最强, 实际 {result.strongest_dimension}"
        )
        assert result.weakest_dimension == "breath", (
            f"子集内 breath=60 应最弱, 实际 {result.weakest_dimension}"
        )

    def test_volume_dimension_name_resolved(self):
        """volume 维度名 → '音量' (DIMENSION_NAMES 已有映射)"""
        gen = AdviceGenerator()
        result = gen.generate(
            self._compare_scores(),
            dimensions=("pitch", "rhythm", "volume", "breath"),
        )
        # 最弱 breath=60 < 75 → 应有 '气息建议'
        assert any("气息建议" in a for a in result.advice), (
            f"breath 最弱应含气息建议, 实际 {result.advice}"
        )
        # 最强 volume=90 ≥ 90 → 应有 '音量控制精准' 表扬
        assert any("音量控制精准" in a for a in result.advice), (
            f"volume 最强应含音量表扬, 实际 {result.advice}"
        )

    def test_default_dimensions_unchanged(self):
        """默认 (不传 dimensions) 仍是六维全量 — 向后兼容"""
        gen = AdviceGenerator()
        result = gen.generate(_scores())
        assert result.strongest_dimension == "artistry"  # 六维: artistry=90 最强
        assert result.weakest_dimension == "technique"   # 六维: technique=60 最弱

    def test_total_not_weakest_even_below_all_dims(self):
        """total 不参与维度排序 — 置信度调制后 total 低于所有维度分也不应成为最弱

        对比路径 total = weighted_total() 含 (0.5+0.5×conf) 调制, 恒 ≤ 加权均值;
        四维分数集中时调制后 total 可低于 min。最弱/最强必须在真实维度中选取,
        否则输出 'total建议：' 空建议并吞掉真实弱维度建议。
        """
        gen = AdviceGenerator()
        result = gen.generate(
            {'pitch_score': 60.0, 'rhythm_score': 60.0, 'volume_score': 60.0,
             'breath_score': 60.0, 'total_score': 45.0, 'total': 45.0},
            dimensions=('pitch', 'rhythm', 'volume', 'breath'),
        )
        assert result.weakest_dimension in ('pitch', 'rhythm', 'volume', 'breath'), (
            f"最弱维度应为真实维度, 实际 {result.weakest_dimension}"
        )
        assert result.strongest_dimension in ('pitch', 'rhythm', 'volume', 'breath'), (
            f"最强维度应为真实维度, 实际 {result.strongest_dimension}"
        )
        # 不应输出 'total建议：' 空建议
        assert not any('total建议' in a for a in result.advice), (
            f"不应产生 total 空建议, 实际 {result.advice}"
        )

    def test_overall_comment_uses_total_not_dims(self):
        """总体评价基于 total (调制后), 而非最强维度分"""
        gen = AdviceGenerator()
        # total=45 (<60) → '需要加强练习'; 若误用最强维度 60 → '水平中等'
        result = gen.generate(
            {'pitch_score': 60.0, 'rhythm_score': 60.0, 'volume_score': 60.0,
             'breath_score': 60.0, 'total_score': 45.0, 'total': 45.0},
            dimensions=('pitch', 'rhythm', 'volume', 'breath'),
        )
        assert any('需要加强练习' in a for a in result.advice), (
            f"总体评价应基于调制后 total=45, 实际 {result.advice}"
        )
