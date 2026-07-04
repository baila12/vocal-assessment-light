"""
ScoreCalibrator 单元测试 v1.0

测试评分校准器的各项功能
"""

import pytest

from services.dl_services.enhanced_dl_assessor import ScoreCalibrator


class TestScoreCalibrator:
    """ScoreCalibrator 测试类"""

    def setup_method(self):
        """每个测试方法前执行"""
        self.calibrator = ScoreCalibrator()

    def test_init(self):
        """测试初始化"""
        assert self.calibrator is not None
        assert self.calibrator.CONSISTENCY_THRESHOLD == 5.0
        assert len(self.calibrator._historical_diffs) == 0

    def test_calibrate_score_quick_mode(self):
        """测试快速模式评分校准"""
        # 测试边界分数
        score_30 = self.calibrator.calibrate_score(30, 'pitch', 'quick')
        assert 55 <= score_30 <= 92, f"快速模式分数超出范围: {score_30}"

        score_60 = self.calibrator.calibrate_score(60, 'pitch', 'quick')
        assert 55 <= score_60 <= 92, f"快速模式分数超出范围: {score_60}"

        score_90 = self.calibrator.calibrate_score(90, 'pitch', 'quick')
        assert 55 <= score_90 <= 92, f"快速模式分数超出范围: {score_90}"

    def test_calibrate_score_professional_mode(self):
        """测试专业模式评分校准"""
        # 专业模式分数应在0-100范围
        score_30 = self.calibrator.calibrate_score(30, 'pitch', 'professional')
        assert 0 <= score_30 <= 100, f"专业模式分数超出范围: {score_30}"

        score_60 = self.calibrator.calibrate_score(60, 'pitch', 'professional')
        assert 0 <= score_60 <= 100, f"专业模式分数超出范围: {score_60}"

        score_90 = self.calibrator.calibrate_score(90, 'pitch', 'professional')
        assert 0 <= score_90 <= 100, f"专业模式分数超出范围: {score_90}"

    def test_calibrate_total(self):
        """测试总分校准"""
        scores = {
            'pitch': 80,
            'rhythm': 75,
            'breath': 85,
            'technique': 70,
            'artistry': 90
        }
        weights = {
            'pitch': 0.28,
            'rhythm': 0.20,
            'breath': 0.20,
            'technique': 0.18,
            'artistry': 0.14
        }

        quick_total = self.calibrator.calibrate_total(scores, weights, 'quick')
        assert 55 <= quick_total <= 92, f"快速模式总分超出范围: {quick_total}"

        prof_total = self.calibrator.calibrate_total(scores, weights, 'professional')
        assert 0 <= prof_total <= 100, f"专业模式总分超出范围: {prof_total}"

    def test_consistency_adjustment_large_diff(self):
        """测试一致性调整（大差异）"""
        quick = 85
        prof = 70
        diff = quick - prof  # 15分差异

        quick_adj, prof_adj = self.calibrator.get_consistency_adjustment(quick, prof)

        # 调整后差异应该减小
        new_diff = abs(quick_adj - prof_adj)
        assert new_diff < diff, "调整后差异应该减小"
        assert quick_adj < quick, "快速模式分数应该降低"
        assert prof_adj > prof, "专业模式分数应该提高"

    def test_consistency_adjustment_small_diff(self):
        """测试一致性调整（小差异）"""
        quick = 80
        prof = 78

        quick_adj, prof_adj = self.calibrator.get_consistency_adjustment(quick, prof)

        # 小差异不需要调整
        assert quick_adj == quick, "小差异不需要调整快速模式分数"
        assert prof_adj == prof, "小差异不需要调整专业模式分数"

    def test_validate_consistency(self):
        """测试一致性验证"""
        # 一致的评分
        quick_scores = {
            'pitch': 80,
            'rhythm': 75,
            'breath': 85,
            'technique': 70,
            'artistry': 90
        }
        prof_scores = {
            'pitch': 82,
            'rhythm': 77,
            'breath': 83,
            'technique': 72,
            'artistry': 88
        }

        is_consistent, diffs, max_diff = self.calibrator.validate_consistency(
            quick_scores, prof_scores
        )

        assert is_consistent, "评分应该一致"
        assert max_diff < 5.0, f"最大差异应该小于5分: {max_diff}"
        assert all(d < 5.0 for d in diffs.values()), "所有维度差异应该小于5分"

    def test_validate_consistency_inconsistent(self):
        """测试一致性验证（不一致情况）"""
        quick_scores = {
            'pitch': 90,
            'rhythm': 85,
            'breath': 95,
            'technique': 80,
            'artistry': 95
        }
        prof_scores = {
            'pitch': 70,
            'rhythm': 75,
            'breath': 80,
            'technique': 70,
            'artistry': 85
        }

        is_consistent, diffs, max_diff = self.calibrator.validate_consistency(
            quick_scores, prof_scores
        )

        assert not is_consistent, "评分不应该一致"
        assert max_diff >= 5.0, f"最大差异应该大于等于5分: {max_diff}"
        assert len(self.calibrator._historical_diffs) == 1, "应该记录历史差异"

    def test_get_adaptive_params(self):
        """测试获取自适应参数"""
        # 初始状态，返回基础参数
        params = self.calibrator.get_adaptive_params('quick')
        assert 'min_score' in params
        assert 'max_score' in params

        # 添加一些历史差异记录
        for _ in range(15):
            self.calibrator._historical_diffs.append(8.0)  # 超过阈值

        # 自适应调整后，参数可能改变
        adaptive_params = self.calibrator.get_adaptive_params('quick')
        assert 'min_score' in adaptive_params
        assert 'max_score' in adaptive_params

    def test_update_adaptive_params(self):
        """测试更新自适应参数"""
        # 大差异情况
        self.calibrator.update_adaptive_params('pitch', 85, 70)

        assert 'pitch' in self.calibrator._adaptive_params['quick']
        assert len(self.calibrator._adaptive_params['quick']['pitch']) == 1

        # 小差异情况
        self.calibrator.update_adaptive_params('rhythm', 75, 73)

        # 小差异不记录
        assert 'rhythm' not in self.calibrator._adaptive_params['quick']


class TestScoreCalibratorEdgeCases:
    """ScoreCalibrator 边界条件测试"""

    def setup_method(self):
        self.calibrator = ScoreCalibrator()

    def test_extreme_scores(self):
        """测试极端分数"""
        # 分数0
        score_0 = self.calibrator.calibrate_score(0, 'pitch', 'professional')
        assert score_0 >= 0

        # 分数100
        score_100 = self.calibrator.calibrate_score(100, 'pitch', 'professional')
        assert score_100 <= 100

    def test_negative_scores(self):
        """测试负分数"""
        score = self.calibrator.calibrate_score(-10, 'pitch', 'quick')
        assert score >= 55, "快速模式负分数应该被限制在最小值"

    def test_over_100_scores(self):
        """测试超过100的分数"""
        score = self.calibrator.calibrate_score(150, 'pitch', 'professional')
        assert score <= 100, "分数应该被限制在最大值"

    def test_empty_scores_dict(self):
        """测试空分数字典"""
        total = self.calibrator.calibrate_total({}, {}, 'quick')
        assert 55 <= total <= 92

    def test_missing_dimensions(self):
        """测试缺少某些维度的评分"""
        quick_scores = {'pitch': 80}
        prof_scores = {'pitch': 82}

        is_consistent, diffs, max_diff = self.calibrator.validate_consistency(
            quick_scores, prof_scores
        )

        # 只比较有的维度
        assert 'pitch' in diffs


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
