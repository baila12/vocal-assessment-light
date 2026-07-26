"""Quick validation: melody.wav alignment after f0 fix"""
import time, sys
sys.path.insert(0, '.')
from services.feature_flags import FeatureFlags
from api.business.audio_analysis import analyze_and_score

test_file = "uploads/melody.wav"
print(f"Test: {test_file}")

flags_ddd = FeatureFlags(enable_ddd_feature_extraction=True)
t0 = time.time()
r_ddd = analyze_and_score(test_file, mode='quick', feature_flags=flags_ddd)
t_ddd = time.time() - t0

flags_old = FeatureFlags(enable_ddd_feature_extraction=False)
t0 = time.time()
r_old = analyze_and_score(test_file, mode='quick', feature_flags=flags_old)
t_old = time.time() - t0

print(f"\n{'dimension':<20s} {'DDD':>7s} {'Legacy':>7s} {'delta':>7s}")
s_ddd = r_ddd.get('scores', r_ddd)
s_old = r_old.get('scores', r_old)
for d in ['pitch', 'rhythm', 'breath', 'technique', 'muscle_strength', 'artistry']:
    vd = float(s_ddd.get(d, 0))
    vo = float(s_old.get(d, 0))
    print(f"{d:<20s} {vd:6.1f}  {vo:6.1f}  {vd-vo:+6.1f}")
print(f"{'total':<20s} {r_ddd.get('total_score',0):6.1f}  {r_old.get('total_score',0):6.1f}  {r_ddd.get('total_score',0)-r_old.get('total_score',0):+6.1f}")
print(f"level: DDD={r_ddd.get('level','?')} Legacy={r_old.get('level','?')}")
print(f"time:  DDD={t_ddd:.1f}s Legacy={t_old:.1f}s")
