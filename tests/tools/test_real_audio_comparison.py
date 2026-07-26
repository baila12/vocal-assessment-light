"""Real audio test: melody.wav — DDD native vs legacy adapter path"""
from __future__ import annotations
import time
import sys
sys.path.insert(0, '.')

from services.feature_flags import FeatureFlags
from api.business.audio_analysis import (
    analyze_and_score, _ddd_feature_extractor_available, ddd_orchestrator
)


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
    print(f"  pitch             {float(s.get('pitch',0)):6.1f}  (10%)")
    print(f"  rhythm            {float(s.get('rhythm',0)):6.1f}  (10%)")
    print(f"  breath            {float(s.get('breath',0)):6.1f}  (20%)")
    print(f"  technique         {float(s.get('technique',0)):6.1f}  (25%)")
    print(f"  muscle_strength   {float(s.get('muscle_strength', result.get('muscle_strength_score', 0))):6.1f}  (25%)")
    print(f"  artistry          {float(s.get('artistry', result.get('artistry_score', 0))):6.1f}  (10%)")
    print(f"  " + "-" * 24)
    print(f"  timbre_adjustment {result.get('timbre_adjustment',0):+6.1f}")
    print(f"  heuristic_dims     {result.get('heuristic_dimensions', [])}")


def main():
    test_file = "uploads/melody.wav"
    print(f"\n[Test] {test_file}")
    print(f"[Flag] DDD scoring: {'OK' if ddd_orchestrator else 'MISSING'}")
    print(f"[Flag] DDD feature extraction: {'OK' if _ddd_feature_extractor_available else 'MISSING'}")

    # ============================================================
    # Test 1: DDD native extraction (new default)
    # ============================================================
    print("\n>>> [Test 1] DDD native extraction path (production default)")
    flags_ddd = FeatureFlags(enable_ddd_feature_extraction=True)
    t0 = time.time()
    result_ddd = analyze_and_score(test_file, mode='quick', feature_flags=flags_ddd)
    t_ddd = time.time() - t0
    print_scores('DDD Native', result_ddd, t_ddd)

    # ============================================================
    # Test 2: Legacy adapter path
    # ============================================================
    print("\n>>> [Test 2] Legacy path (AudioFeaturesService -> FeatureAdapter)")
    flags_old = FeatureFlags(enable_ddd_feature_extraction=False)
    t0 = time.time()
    result_old = analyze_and_score(test_file, mode='quick', feature_flags=flags_old)
    t_old = time.time() - t0
    print_scores('Legacy Adapter', result_old, t_old)

    # ============================================================
    # Diff analysis
    # ============================================================
    print(f"\n{'='*60}")
    print(f"  DIFF: DDD - Legacy")
    print(f"{'='*60}")
    s_ddd = result_ddd.get('scores', result_ddd)
    s_old = result_old.get('scores', result_old)
    dims = [
        ('pitch', 'pitch'),
        ('rhythm', 'rhythm'),
        ('breath', 'breath'),
        ('technique', 'technique'),
        ('muscle_strength', 'muscle_strength'),
        ('artistry', 'artistry'),
    ]
    for key, name in dims:
        v1 = float(s_ddd.get(key, 0))
        v2 = float(s_old.get(key, 0))
        print(f"  {name:<18s} DDD={v1:6.1f}  Legacy={v2:6.1f}  delta={v1-v2:+6.2f}")

    v_total_ddd = result_ddd.get('total_score', 0)
    v_total_old = result_old.get('total_score', 0)
    diff_total = v_total_ddd - v_total_old
    print(f"  {'-'*52}")
    print(f"  {'total':<18s} DDD={v_total_ddd:6.1f}  "
          f"Legacy={v_total_old:6.1f}  delta={diff_total:+6.2f}")
    print(f"  {'level':<18s} DDD={result_ddd.get('level','?'):>6s}  Legacy={result_old.get('level','?'):>6s}")
    print(f"  {'timbre_adj':<18s} DDD={result_ddd.get('timbre_adjustment',0):+6.1f}  Legacy={result_old.get('timbre_adjustment',0):+6.1f}")

    # Performance
    print(f"\n  PERFORMANCE:")
    print(f"  DDD native:  {t_ddd:.1f}s")
    print(f"  Legacy:      {t_old:.1f}s")
    print(f"  delta:       {t_ddd - t_old:+.1f}s")

    # Validity checks
    print(f"\n  VALIDATION:")
    for r, name in [(result_ddd, 'DDD'), (result_old, 'Legacy')]:
        issues = []
        if not r.get('success', True):
            issues.append('success=False')
        if not (0 <= r['total_score'] <= 100):
            issues.append(f"total={r['total_score']} OOB")
        if not r.get('level'):
            issues.append('level missing')
        if not r.get('heuristic_dimensions'):
            issues.append('heuristic_dimensions missing')
        status = 'FAIL: ' + ', '.join(issues) if issues else 'PASS'
        print(f"  {name}: {status}")

    print()


if __name__ == '__main__':
    main()
