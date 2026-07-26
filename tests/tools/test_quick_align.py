"""Quick alignment test: clipped_test.wav — DDD native vs legacy"""
import time, sys
sys.path.insert(0, '.')
from services.feature_flags import FeatureFlags
from api.business.audio_analysis import analyze_and_score

test_file = "uploads/clipped_test.wav"
print(f"Test: {test_file}")

# DDD native
flags_ddd = FeatureFlags(enable_ddd_feature_extraction=True)
t0 = time.time()
r_ddd = analyze_and_score(test_file, mode='quick', feature_flags=flags_ddd)
t_ddd = time.time() - t0

# Legacy
flags_old = FeatureFlags(enable_ddd_feature_extraction=False)
t0 = time.time()
r_old = analyze_and_score(test_file, mode='quick', feature_flags=flags_old)
t_old = time.time() - t0

# Compare
print(f"\n{'dimension':<20s} {'DDD':>7s} {'Legacy':>7s} {'delta':>7s}")
print("-" * 44)
s_ddd = r_ddd.get('scores', r_ddd)
s_old = r_old.get('scores', r_old)
for d in ['pitch', 'rhythm', 'breath', 'technique', 'muscle_strength', 'artistry']:
    vd = float(s_ddd.get(d, 0))
    vo = float(s_old.get(d, 0))
    bar = "!" if abs(vd - vo) > 10 else ""
    print(f"{d:<20s} {vd:6.1f}  {vo:6.1f}  {vd-vo:+6.1f}  {bar}")

td = r_ddd.get('total_score', 0)
to = r_old.get('total_score', 0)
print("-" * 44)
print(f"{'total':<20s} {td:6.1f}  {to:6.1f}  {td-to:+6.1f}")
print(f"{'level':<20s} {r_ddd.get('level','?'):>6s}  {r_old.get('level','?'):>6s}")
print(f"{'time':<20s} {t_ddd:5.1f}s  {t_old:5.1f}s  {t_ddd-t_old:+.1f}s")

# Validation
all_ok = True
for r, name in [(r_ddd, 'DDD'), (r_old, 'Legacy')]:
    ok = r.get('success', True) and 0 <= r.get('total_score', -1) <= 100
    if not ok:
        print(f"FAIL: {name} score={r.get('total_score')}")
        all_ok = False

# Max delta check
max_delta = max(abs(float(s_ddd.get(d, 0)) - float(s_old.get(d, 0))) for d in ['pitch', 'rhythm', 'breath', 'technique', 'muscle_strength', 'artistry'])
print(f"\nMax dimension delta: {max_delta:.1f}")
print("PASS: scores aligned!" if max_delta < 15 else "WARNING: large delta")
