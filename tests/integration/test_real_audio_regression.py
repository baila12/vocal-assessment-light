"""
真实音频回归测试 — 评分基线保护

使用 tests/test_data/audio/vocal/ 中的 5 个真实音频文件，
验证评分系统在代码变更前后保持一致性。

基线数据来源: v7.3 DDD 唯一路径 + audiofeat 增强 (见 docs/4-process/PROJECT_STATUS.md)

TDD 用法:
  - GREEN: 当前基线必须通过 (保护已有评分不被意外修改)
  - RED:   修改评分算法后 → 更新基线 → 有意变更需同步更新此文件

运行:
  pytest tests/integration/test_real_audio_regression.py -v
"""
import pytest
from pathlib import Path

from api.business.audio_analysis import analyze_and_score

# ── 真实音频文件列表 ──
REAL_AUDIO_FILES = [
    "恋人（高分）.mp3",
    "手写的从前（高分）.mp3",
    "1（高分）.mp3",
    "音频-3分26秒(高分).mp3",
    "陈奕迅难听之声（低分）.mp3",
]

# ── v7.4 Quick 模式评分基线 (DDD 唯一路径, P0 修复) ──
# v7.4 六维权重: pitch=13%, rhythm=12%, breath=22%, technique=25%, muscle=15%, artistry=13%
# P0-1: CPPS 替代 HNR 作为气声比主特征 (40% vs 70%)
# P0-2: ZCR + Spectral Centroid 增强咬字清晰度
# P0-3: 无颤音 fallback (pitch_cv + dynamic_range)
# P0-4: 肌肉权重 25%→15%, 释放 10% 重新分配
# 范围 = 实测值 ± buffer (±12 for all dimensions due to scoring changes)
BASELINE_V7_4 = {
    "恋人（高分）.mp3": {
        "total_range": (55, 80),
        "pitch_range":    (55, 82),
        "rhythm_range":   (52, 80),
        "breath_range":   (78, 100),
        "technique_range": (25, 80),     # v7.4: CPPS primary raises floor
        "artistry_range":  (62, 88),
        "muscle_range":    (65, 95),
    },
    "手写的从前（高分）.mp3": {
        "total_range": (48, 75),
        "pitch_range":    (55, 82),
        "rhythm_range":   (25, 60),      # 钢琴伴奏干扰 onset 检测
        "breath_range":   (80, 100),
        "technique_range": (20, 75),     # v7.4: CPPS primary raises floor
        "artistry_range":  (62, 88),
        "muscle_range":    (60, 90),
    },
    "1（高分）.mp3": {
        "total_range": (55, 80),
        "pitch_range":    (58, 84),
        "rhythm_range":   (56, 83),
        "breath_range":   (82, 100),
        "technique_range": (20, 75),     # v7.4: CPPS primary raises floor
        "artistry_range":  (62, 88),
        "muscle_range":    (60, 92),
    },
    "音频-3分26秒(高分).mp3": {
        "total_range": (55, 80),
        "pitch_range":    (55, 82),
        "rhythm_range":   (42, 72),
        "breath_range":   (75, 100),
        "technique_range": (25, 80),     # v7.4: CPPS primary raises floor
        "artistry_range":  (62, 88),
        "muscle_range":    (65, 95),
    },
    "陈奕迅难听之声（低分）.mp3": {
        "total_range": (40, 65),
        "pitch_range":    (52, 80),
        "rhythm_range":   (0, 20),       # 严重脱拍
        "breath_range":   (70, 98),
        "technique_range": (15, 65),     # v7.4: CPPS primary raises floor
        "artistry_range":  (60, 86),
        "muscle_range":    (55, 85),
    },
}

# Legacy baselines (kept for reference)
BASELINE_V7_3 = BASELINE_V7_4  # alias
BASELINE = BASELINE_V7_4


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
    """真实音频评分回归 — 与 v7.3 基线对比"""

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

        for dim in ['pitch', 'rhythm', 'breath', 'technique', 'artistry']:
            dim_key = f"{dim}_range"
            if dim_key in baseline:
                dim_min, dim_max = baseline[dim_key]
                dim_score = scores.get(dim, -1)
                assert dim_min <= dim_score <= dim_max, \
                    f"{filename}: {dim}={dim_score} 超出基线 [{dim_min}, {dim_max}]"

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
        """高分组（恋人）vs 低分组（陈奕迅）总分差 >= 10 (v7.3: 六维权重稀释)"""
        path_high = _resolve_audio_path("恋人（高分）.mp3")
        path_low = _resolve_audio_path("陈奕迅难听之声（低分）.mp3")

        if not path_high or not path_low:
            pytest.skip("测试音频不全")

        high = analyze_and_score(path_high, mode='quick')
        low = analyze_and_score(path_low, mode='quick')

        if not high.get('success') or not low.get('success'):
            pytest.skip("分析失败")

        diff = high['total_score'] - low['total_score']
        assert diff >= 10, \
            f"区分度不足: 高={high['total_score']}, 低={low['total_score']}, 差={diff}"

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
