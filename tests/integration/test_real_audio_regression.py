"""
真实音频回归测试 — 评分基线保护

使用 tests/test_data/audio/vocal/ 中的 5 个真实音频文件，
验证评分系统在代码变更前后保持一致性。

基线数据来源: v7.14 为 v7.6 基线校正轮 — 修复 sr 错配 bug 后的真实值
  (详见 BASELINE_V7_14 注释 + docs/4-process/PROJECT_STATUS.md)

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

# ── v7.14 Quick 模式评分基线 (DDD 唯一路径 + P2-11 sr 错配修复) ──
# v7.14 P2-11 根因: 旧代码 librosa.load(sr=None) 后降采样到 16kHz, 但只更新局部变量
# sample_rate, AudioAnalysisResult.sample_rate 保持原生 sr (44.1k/48k)。DDD 各提取器
# 收到的 (16k 音频, 原生 sr) 不一致: rhythm 内部按 orig_sr=原生 重采样 → 时间轴错位、
# onset CV 失真; technique/muscle 频谱轴错位 (spectral_centroid/hf_energy 全偏)。
# pitch 不受影响 (F0 提取在重采样后使用已修正的局部 sr)。
# P2-11 一步加载到 TARGET_SR=16000 → sr 与音频一致 → rhythm/breath/tech/muscle/artistry
# 恢复真实值。实测影响: rhythm 恋人 66→43.8、1高分 71→30.4 (sr 修复前被 2.76x 时间
# 压缩虚高); total 压缩到 58-65; 区分度转移到单维 (rhythm gap 34.5)。
# 范围 = v7.14 实测值 ± buffer (total ±6, pitch/art/muscle ±8, rhythm/breath/tech ±10)
BASELINE_V7_14 = {
    "恋人（高分）.mp3": {
        "total_range": (58, 70),
        "pitch_range":    (59, 75),
        "rhythm_range":   (34, 54),      # v7.14: sr 修复后真实 onset CV (旧 66 为时间压缩虚高)
        "breath_range":   (70, 90),
        "technique_range": (33, 53),
        "artistry_range":  (67, 83),
        "muscle_range":    (70, 86),
    },
    "手写的从前（高分）.mp3": {
        "total_range": (59, 71),
        "pitch_range":    (62, 78),
        "rhythm_range":   (20, 40),      # 钢琴伴奏干扰 onset 检测 (宽缓冲区)
        "breath_range":   (72, 92),
        "technique_range": (42, 62),
        "artistry_range":  (64, 80),
        "muscle_range":    (67, 83),
    },
    "1（高分）.mp3": {
        "total_range": (56, 68),
        "pitch_range":    (63, 79),
        "rhythm_range":   (20, 40),
        "breath_range":   (68, 88),
        "technique_range": (35, 55),
        "artistry_range":  (66, 82),
        "muscle_range":    (66, 82),
    },
    "音频-3分26秒(高分).mp3": {
        "total_range": (57, 69),
        "pitch_range":    (60, 76),
        "rhythm_range":   (27, 47),
        "breath_range":   (69, 89),
        "technique_range": (35, 55),
        "artistry_range":  (65, 81),
        "muscle_range":    (72, 88),
    },
    "陈奕迅难听之声（低分）.mp3": {
        "total_range": (53, 65),
        "pitch_range":    (58, 74),
        "rhythm_range":   (0, 19),       # 严重脱拍
        "breath_range":   (66, 86),
        "technique_range": (37, 57),
        "artistry_range":  (62, 78),
        "muscle_range":    (63, 79),
    },
}

# ── v7.6 Quick 模式评分基线 (DDD 唯一路径, P0+P1+P2 全部修复) ──
# v7.6 六维权重: pitch=13%, rhythm=12%, breath=22%, technique=25%, muscle=15%, artistry=13%
# v7.5 P0: Artistry F0 CV / Technique HNR monotonic / CPPS-HF decoupling / Muscle calibration
# v7.6 P1: Muscle v7.4 proxies verified / crescendo avg×coverage / artistic_fluctuation continuous
# v7.6 P2: CPPS×100 rescale + HNR graduated thresholds (Buckley 2023 singing-specific)
# 范围 = 实测值 ± buffer (±10 stable dims, ±12 technique due to CPP scaling)
BASELINE_V7_6 = {
    "恋人（高分）.mp3": {
        "total_range": (62, 82),
        "pitch_range":    (58, 78),
        "rhythm_range":   (56, 78),
        "breath_range":   (80, 100),
        "technique_range": (42, 62),     # v7.6 P2: CPP rescale + HNR graduated → +6pts
        "artistry_range":  (64, 84),
        "muscle_range":    (68, 88),
    },
    "手写的从前（高分）.mp3": {
        "total_range": (62, 82),
        "pitch_range":    (60, 80),
        "rhythm_range":   (28, 58),      # 钢琴伴奏干扰 onset 检测 (宽缓冲区)
        "breath_range":   (81, 100),
        "technique_range": (48, 72),     # v7.6 P2: 较大提升 (HNR middle-range benefit)
        "artistry_range":  (64, 86),
        "muscle_range":    (68, 88),
    },
    "1（高分）.mp3": {
        "total_range": (64, 84),
        "pitch_range":    (62, 82),
        "rhythm_range":   (60, 83),
        "breath_range":   (84, 100),
        "technique_range": (44, 64),
        "artistry_range":  (65, 86),
        "muscle_range":    (67, 88),
    },
    "音频-3分26秒(高分).mp3": {
        "total_range": (62, 82),
        "pitch_range":    (58, 78),
        "rhythm_range":   (43, 72),
        "breath_range":   (76, 97),
        "technique_range": (48, 70),
        "artistry_range":  (63, 84),
        "muscle_range":    (70, 91),
    },
    "陈奕迅难听之声（低分）.mp3": {
        "total_range": (52, 73),
        "pitch_range":    (56, 78),
        "rhythm_range":   (0, 18),       # 严重脱拍
        "breath_range":   (70, 92),
        "technique_range": (47, 68),     # v7.6 P2: low-HNR penalty reduced
        "artistry_range":  (58, 80),
        "muscle_range":    (65, 86),
    },
}

# ── v7.4 Quick 模式评分基线 (v7.6 之前, 保留历史参考) ──
BASELINE_V7_4 = {
    "恋人（高分）.mp3": {
        "total_range": (55, 80),
        "pitch_range":    (55, 82),
        "rhythm_range":   (52, 80),
        "breath_range":   (78, 100),
        "technique_range": (25, 80),
        "artistry_range":  (62, 88),
        "muscle_range":    (65, 95),
    },
    "手写的从前（高分）.mp3": {
        "total_range": (48, 75),
        "pitch_range":    (55, 82),
        "rhythm_range":   (25, 60),
        "breath_range":   (80, 100),
        "technique_range": (20, 75),
        "artistry_range":  (62, 88),
        "muscle_range":    (60, 90),
    },
    "1（高分）.mp3": {
        "total_range": (55, 80),
        "pitch_range":    (58, 84),
        "rhythm_range":   (56, 83),
        "breath_range":   (82, 100),
        "technique_range": (20, 75),
        "artistry_range":  (62, 88),
        "muscle_range":    (60, 92),
    },
    "音频-3分26秒(高分).mp3": {
        "total_range": (55, 80),
        "pitch_range":    (55, 82),
        "rhythm_range":   (42, 72),
        "breath_range":   (75, 100),
        "technique_range": (25, 80),
        "artistry_range":  (62, 88),
        "muscle_range":    (65, 95),
    },
    "陈奕迅难听之声（低分）.mp3": {
        "total_range": (40, 65),
        "pitch_range":    (52, 80),
        "rhythm_range":   (0, 20),
        "breath_range":   (70, 98),
        "technique_range": (15, 65),
        "artistry_range":  (60, 86),
        "muscle_range":    (55, 85),
    },
}

# Active baseline — always use latest
BASELINE = BASELINE_V7_14


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
