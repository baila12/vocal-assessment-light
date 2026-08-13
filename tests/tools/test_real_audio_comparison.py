"""Real audio validation: melody.wav — DDD native path (v7.16 P2-15)

v7.1.4 移除 legacy ScoreServiceV4 后, "DDD vs Legacy 双路径对比" 已无意义
(enable_ddd_feature_extraction=False 为死 flag, audio_analysis 恒走 DDD)。
本脚本收敛为单路径 DDD 验证工具: 真实音频 → 评分 → 有效性校验。
"""
from __future__ import annotations
import time
import sys
sys.path.insert(0, '.')

from services.feature_flags import FeatureFlags
from api.business.audio_analysis import analyze_and_score, ddd_orchestrator


def print_scores(label, result, elapsed):
    print(f"\n{'='*60}")
    print(f"  {label}  ({elapsed:.1f}s)")
    print(f"{'='*60}")

    s = result.get('scores', result)
    print(f"  total            {result.get('total_score', result.get('total')):6.1f}")
    print(f"  level             {result.get('level', ''):>6s}")
    print(f"  stars             {result.get('stars', ''):>6s}")
    print(f"  color             {result.get('color', ''):>6s}")
    print(f"  " + "-" * 24)
    print(f"  pitch             {float(s.get('pitch',0)):6.1f}  (13%)")
    print(f"  rhythm            {float(s.get('rhythm',0)):6.1f}  (12%)")
    print(f"  breath            {float(s.get('breath',0)):6.1f}  (22%)")
    print(f"  technique         {float(s.get('technique',0)):6.1f}  (25%)")
    print(f"  muscle_strength   {float(s.get('muscle_strength', result.get('muscle_strength_score', 0))):6.1f}  (15%)")
    print(f"  artistry          {float(s.get('artistry', result.get('artistry_score', 0))):6.1f}  (13%)")
    print(f"  " + "-" * 24)
    print(f"  timbre_adjustment {result.get('timbre_adjustment',0):+6.1f}")
    print(f"  heuristic_dims     {result.get('heuristic_dimensions', [])}")


def main():
    test_file = "uploads/melody.wav"
    print(f"\n[Test] {test_file}")
    print(f"[Flag] DDD scoring: {'OK' if ddd_orchestrator else 'MISSING'}")

    flags_ddd = FeatureFlags(enable_ddd_feature_extraction=True)
    t0 = time.time()
    result_ddd = analyze_and_score(test_file, mode='quick', feature_flags=flags_ddd)
    t_ddd = time.time() - t0
    print_scores('DDD Native', result_ddd, t_ddd)

    print(f"\n  PERFORMANCE:")
    print(f"  DDD native:  {t_ddd:.1f}s")

    # Validity checks
    print(f"\n  VALIDATION:")
    issues = []
    if not result_ddd.get('success', True):
        issues.append('success=False')
    if not (0 <= result_ddd['total_score'] <= 100):
        issues.append(f"total={result_ddd['total_score']} OOB")
    if not result_ddd.get('level'):
        issues.append('level missing')
    if not result_ddd.get('heuristic_dimensions'):
        issues.append('heuristic_dimensions missing')
    status = 'FAIL: ' + ', '.join(issues) if issues else 'PASS'
    print(f"  DDD: {status}")

    print()


if __name__ == '__main__':
    main()
