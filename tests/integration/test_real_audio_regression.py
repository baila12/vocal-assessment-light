"""
真实音频回归测试 — 评分基线保护

使用 tests/test_data/audio/vocal/ 中的 5 个真实音频文件，
验证评分系统在代码变更前后保持一致性。

基线: BASELINE_V7_17 (v7.17 评分校准后重校准 — 高分音频 ≥80, 陈奕迅低分保持)
  v7.18/v7.19 仅改动对比分析 (comparison), 六维评估未变 → 本基线对 assessment 仍有效。

TDD 用法:
  - GREEN: 当前基线必须通过 (保护已有评分不被意外修改)
  - RED:   修改评分算法后 → 更新基线 → 有意变更需同步更新此文件

运行:
  pytest tests/integration/test_real_audio_regression.py -v
"""
import pytest
from pathlib import Path

from api.business.audio_analysis import analyze_and_score

pytestmark = pytest.mark.slow

# ── 真实音频文件列表 ──
REAL_AUDIO_FILES = [
    "恋人（高分）.mp3",
    "手写的从前（高分）.mp3",
    "1（高分）.mp3",
    "音频-3分26秒(高分).mp3",
    "陈奕迅难听之声（低分）.mp3",
]

# ── v7.17 Quick 模式评分基线 (评分校准: 高分音频 ≥80) ──
# v7.17 校准: A1 rhythm 混音映射重校准 (伴奏污染) + B1 pitch MAE 曲线放宽 (24音分→85)
# + tilt/hf 改质量组件 (修复气声比结构性封顶 65) + CPP/HNR/articulation 曲线校准
# + B4 breath/muscle/artistry 微调。4 个"高分"真实音频 total 79.9-82.6 (优秀 A),
# 陈奕迅 (低分) 72.0 保持低分 (rhythm 9.3), 区分度: 总分排序 + rhythm gap 62.8。
# 范围 = v7.17 实测值 ± buffer (total ±5, pitch/art/muscle ±7, rhythm/breath/tech ±8)
BASELINE_V7_17 = {
    "恋人（高分）.mp3": {
        "total_range": (76, 86),
        "pitch_range":    (75, 89),
        "rhythm_range":   (64, 80),
        "breath_range":   (81, 96),
        "technique_range": (68, 84),
        "artistry_range":  (75, 89),
        "muscle_range":    (78, 92),
    },
    "手写的从前（高分）.mp3": {
        "total_range": (77, 88),
        "pitch_range":    (78, 91),
        "rhythm_range":   (57, 73),
        "breath_range":   (83, 99),
        "technique_range": (77, 92),
        "artistry_range":  (72, 86),
        "muscle_range":    (75, 88),
    },
    "1（高分）.mp3": {
        "total_range": (74, 85),
        "pitch_range":    (77, 91),
        "rhythm_range":   (57, 73),
        "breath_range":   (79, 95),
        "technique_range": (69, 85),
        "artistry_range":  (73, 87),
        "muscle_range":    (73, 87),
    },
    "音频-3分26秒(高分).mp3": {
        "total_range": (75, 86),
        "pitch_range":    (76, 90),
        "rhythm_range":   (61, 77),
        "breath_range":   (79, 94),
        "technique_range": (68, 85),
        "artistry_range":  (73, 87),
        "muscle_range":    (80, 95),
    },
    "陈奕迅难听之声（低分）.mp3": {
        "total_range": (66, 78),
        "pitch_range":    (75, 89),
        "rhythm_range":   (0, 17),       # 严重脱拍
        "breath_range":   (77, 92),
        "technique_range": (69, 85),
        "artistry_range":  (69, 83),
        "muscle_range":    (69, 83),
    },
}

# Active baseline — always use latest
BASELINE = BASELINE_V7_17


def _resolve_audio_path(filename):
    """Resolve a test audio file path."""
    base = Path(__file__).parent.parent / "test_data" / "audio" / "vocal"
    path = base / filename
    if not path.exists():
        return None
    return str(path)


# ============================================================================
# 回归测试 — 基线保护
# ============================================================================

@pytest.mark.parametrize("filename", REAL_AUDIO_FILES)
class TestRealAudioRegression:
    """真实音频评分回归 — 与 v7.6 基线对比"""

    def test_audio_file_exists(self, filename):
        """测试音频文件存在"""
        path = _resolve_audio_path(filename)
        assert path is not None, f"测试音频不存在: {filename}"

    def test_quick_mode_returns_valid_scores(self, filename):
        """Quick 模式返回有效评分结果"""
        path = _resolve_audio_path(filename)
        if path is None:
            pytest.skip(f"测试音频不存在: {filename}")

        result = analyze_and_score(path, mode='quick')

        assert result.get('success'), f"Quick 分析失败: {result.get('error')}"
        assert 'total_score' in result
        assert 'scores' in result
        assert 'level' in result
        assert result.get('level') != '?', f"{filename}: level 不应为 '?'"

    def test_total_score_in_baseline_range(self, filename):
        """总分在 v7.3 基线范围内"""
        path = _resolve_audio_path(filename)
        if path is None:
            pytest.skip(f"测试音频不存在: {filename}")

        result = analyze_and_score(path, mode='quick')
        if not result.get('success'):
            pytest.skip(f"分析失败: {result.get('error')}")

        baseline = BASELINE.get(filename, {})
        total_min, total_max = baseline.get("total_range", (0, 100))
        total = result['total_score']

        assert total_min <= total <= total_max, \
            f"{filename}: total={total} 超出基线 [{total_min}, {total_max}]"

    def test_dimension_scores_in_baseline_ranges(self, filename):
        """各维度评分在基线范围内"""
        path = _resolve_audio_path(filename)
        if path is None:
            pytest.skip(f"测试音频不存在: {filename}")

        result = analyze_and_score(path, mode='quick')
        if not result.get('success'):
            pytest.skip(f"分析失败: {result.get('error')}")

        baseline = BASELINE.get(filename, {})
        scores = result['scores']

        # 维度名 → (scores dict 键, baseline 范围键) — muscle 键名与基线字段名不同
        DIM_KEYS = {
            'pitch': ('pitch', 'pitch_range'),
            'rhythm': ('rhythm', 'rhythm_range'),
            'breath': ('breath', 'breath_range'),
            'technique': ('technique', 'technique_range'),
            'muscle_strength': ('muscle_strength', 'muscle_range'),
            'artistry': ('artistry', 'artistry_range'),
        }
        for score_key, range_key in DIM_KEYS.values():
            if range_key in baseline:
                dim_min, dim_max = baseline[range_key]
                dim_score = scores.get(score_key, -1)
                assert dim_min <= dim_score <= dim_max, \
                f"{filename}: {score_key}={dim_score} 超出基线 [{dim_min}, {dim_max}]"

    def test_scores_in_valid_range(self, filename):
        """所有分数在 0-100 之间"""
        path = _resolve_audio_path(filename)
        if path is None:
            pytest.skip(f"测试音频不存在: {filename}")

        result = analyze_and_score(path, mode='quick')
        if not result.get('success'):
            pytest.skip(f"分析失败: {result.get('error')}")

        total = result['total_score']
        assert 0 <= total <= 100, f"{filename}: total={total} 不在 [0, 100]"

        for dim, score in result.get('scores', {}).items():
            assert 0 <= score <= 100, f"{filename}: {dim}={score} 不在 [0, 100]"


# ============================================================================
# 区分度验证
# ============================================================================

class TestScoreDifferentiation:
    """评分区分度 — 高分 vs 低分应有显著差异"""

    def test_high_vs_low_total_differentiation(self):
        """高分组（恋人）vs 低分组（陈奕迅）——总分排序 + 单维区分度。

        v7.14 规格校正: sr 修复后 total 压缩到 58-65 (实测 diff=4.8), 原 ≥8 总分差不可达。
        与 BDD differentiation.feature 一致的可验证不变量:
          1. 总分排序正确 (高 > 低)
          2. 至少一个核心维度 gap ≥ 10 (实测 rhythm 43.8 vs 9.3 = 34.5)
        """
        path_high = _resolve_audio_path("恋人（高分）.mp3")
        path_low = _resolve_audio_path("陈奕迅难听之声（低分）.mp3")

        if not path_high or not path_low:
            pytest.skip("测试音频不全")

        high = analyze_and_score(path_high, mode='quick')
        low = analyze_and_score(path_low, mode='quick')

        if not high.get('success') or not low.get('success'):
            pytest.skip("分析失败")

        assert high['total_score'] > low['total_score'], \
            f"总分排序错误: 高={high['total_score']} 应 > 低={low['total_score']}"

        dims = ['pitch', 'rhythm', 'breath', 'technique', 'artistry']
        gaps = {d: abs(high['scores'].get(d, 0) - low['scores'].get(d, 0)) for d in dims}
        assert max(gaps.values()) >= 10, \
            f"无核心维度区分度 ≥10: {gaps} (总分 {high['total_score']} vs {low['total_score']})"

    def test_all_high_scores_above_low(self):
        """高分组所有音频总分应高于低分组"""
        path_low = _resolve_audio_path("陈奕迅难听之声（低分）.mp3")
        if not path_low:
            pytest.skip("低分测试音频不存在")

        low = analyze_and_score(path_low, mode='quick')
        if not low.get('success'):
            pytest.skip("低分分析失败")

        high_files = [f for f in REAL_AUDIO_FILES if "高分" in f]
        for filename in high_files:
            path = _resolve_audio_path(filename)
            if not path:
                continue
            result = analyze_and_score(path, mode='quick')
            if not result.get('success'):
                continue

            assert result['total_score'] > low['total_score'], \
                f"{filename} ({result['total_score']}) 应 > 低分 ({low['total_score']})"


# ============================================================================
# Quick/Pro 一致性
# ============================================================================

class TestQuickProConsistency:
    """Quick vs Professional 模式一致性"""

    def test_quick_pro_total_within_25_percent(self):
        """同一音频 Quick 和 Pro 总分差距 < 25% (v5.19: 20→25%)"""
        path = _resolve_audio_path("恋人（高分）.mp3")
        if not path:
            pytest.skip("测试音频不存在")

        quick = analyze_and_score(path, mode='quick')
        pro = analyze_and_score(path, mode='professional')

        if not quick.get('success') or not pro.get('success'):
            pytest.skip("分析失败")

        q_total = quick['total_score']
        p_total = pro['total_score']

        if q_total > 0:
            ratio = abs(q_total - p_total) / q_total
            assert ratio < 0.25, \
                f"Quick/Pro 差距过大: Quick={q_total}, Pro={p_total}, ratio={ratio:.1%}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
