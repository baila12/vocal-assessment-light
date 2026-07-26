"""Batch real audio test: tests/test_data/audio/vocal/*.mp3"""
from __future__ import annotations
import time, sys, os, glob
sys.path.insert(0, '.')

from services.feature_flags import FeatureFlags
from api.business.audio_analysis import analyze_and_score

TEST_DIR = "tests/test_data/audio/vocal"


def test_one(filepath, label):
    """Run both paths on one file, return (ddd_result, old_result, ddd_time, old_time)"""
    flags_ddd = FeatureFlags(enable_ddd_feature_extraction=True)
    flags_old = FeatureFlags(enable_ddd_feature_extraction=False)

    t0 = time.time()
    r_ddd = analyze_and_score(filepath, mode='quick', feature_flags=flags_ddd)
    t_ddd = time.time() - t0

    t0 = time.time()
    r_old = analyze_and_score(filepath, mode='quick', feature_flags=flags_old)
    t_old = time.time() - t0

    return r_ddd, r_old, t_ddd, t_old


def main():
    files = sorted(glob.glob(os.path.join(TEST_DIR, "*.mp3")))
    if not files:
        files = sorted(glob.glob(os.path.join(TEST_DIR, "*.wav")))
    print(f"Found {len(files)} files in {TEST_DIR}\n")

    results = []
    for f in files:
        name = os.path.basename(f)
        size_mb = os.path.getsize(f) / 1024 / 1024
        print(f">>> {name}  ({size_mb:.1f}MB)")
        r_ddd, r_old, t_ddd, t_old = test_one(f, name)
        results.append((name, r_ddd, r_old, t_ddd, t_old))

        s_ddd = r_ddd.get('scores', r_ddd)
        s_old = r_old.get('scores', r_old)
        dims = ['pitch', 'rhythm', 'breath', 'technique', 'muscle_strength', 'artistry']

        # Per-dimension scores
        print(f"  {'':>24s} {'DDD':>7s} {'Legacy':>7s} {'Delta':>7s}")
        for d in dims:
            vd = float(s_ddd.get(d, 0))
            vo = float(s_old.get(d, 0))
            print(f"  {d:<24s} {vd:6.1f}  {vo:6.1f}  {vd-vo:+6.1f}")

        td = r_ddd.get('total_score', 0)
        to = r_old.get('total_score', 0)
        print(f"  {'total':<24s} {td:6.1f}  {to:6.1f}  {td-to:+6.1f}")
        print(f"  {'level':<24s} {r_ddd.get('level','?'):>6s}  {r_old.get('level','?'):>6s}")
        print(f"  {'time':<24s} {t_ddd:5.1f}s  {t_old:5.1f}s")
        print()

    # Summary
    print(f"{'='*60}")
    print(f"  SUMMARY ({len(results)} files)")
    print(f"{'='*60}")
    print(f"  {'file':<28s} {'DDD total':>8s} {'Legacy':>7s} {'Delta':>7s}  {'DDD level':>8s} {'Leg level':>8s}")
    print(f"  {'-'*76}")
    for name, r_ddd, r_old, _, _ in results:
        td = r_ddd.get('total_score', 0)
        to = r_old.get('total_score', 0)
        ld = r_ddd.get('level', '?')
        lo = r_old.get('level', '?')
        short = name[:26]
        print(f"  {short:<28s} {td:7.1f}  {to:6.1f}  {td-to:+6.1f}   {ld:>8s}  {lo:>8s}")

    # Average delta
    avg_delta = sum(r[1].get('total_score',0) - r[2].get('total_score',0) for r in results) / len(results)
    print(f"  {'-'*76}")
    print(f"  Average delta: {avg_delta:+.1f}")

    # Validation
    all_pass = True
    for name, r_ddd, r_old, _, _ in results:
        for r, path in [(r_ddd, 'DDD'), (r_old, 'Legacy')]:
            if not r.get('success', True) or not (0 <= r.get('total_score', -1) <= 100):
                print(f"  FAIL: {name} {path}")
                all_pass = False
    if all_pass:
        print(f"\n  ALL {len(results)*2} tests PASSED")
    print()


if __name__ == '__main__':
    main()
