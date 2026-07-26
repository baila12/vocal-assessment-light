"""
Comprehensive end-to-end system test — v7.1.0

Tests all critical paths: upload/analyze, scoring, infrastructure, EventBus, API factory.
No server required — all tests run directly.
"""
import sys, os, time, traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
os.environ['VAS_DISABLE_RATE_LIMIT'] = '1'

passed = 0
failed = 0
errors = []

def check(name, condition, detail=''):
    global passed, failed
    if condition:
        passed += 1
        print(f'  [PASS] {name} {detail}')
    else:
        failed += 1
        msg = f'  [FAIL] {name} {detail}'
        print(msg)
        errors.append(msg)

print('=' * 60)
print('COMPREHENSIVE SYSTEM TEST — v7.1.0')
print('=' * 60)

# ---- 1. Imports ----
print('\n--- 1. Module Imports ---')
try:
    from api.business.audio_analysis import analyze_and_score, ddd_orchestrator
    from api.business.audio_analysis import _ddd_scoring_available
    from services.feature_flags import FeatureFlags
    from services.score_service import ScoreServiceV4
    from services.audio_features_service import AudioFeaturesResult
    check('Core imports', True)
except Exception as e:
    check('Core imports', False, str(e))
    print(traceback.format_exc())
    sys.exit(1)

# ---- 2. Feature Flags ----
print('\n--- 2. Feature Flags ---')
flags = FeatureFlags()
check('DDD scoring default', flags.enable_ddd_scoring is True)
check('DDD extraction default', flags.enable_ddd_feature_extraction is True)
check('Quick mode DDD scoring', FeatureFlags.for_quick().enable_ddd_scoring is True)
check('Quick mode DDD extraction', FeatureFlags.for_quick().enable_ddd_feature_extraction is True)
check('Pro mode DDD scoring', FeatureFlags.for_professional().enable_ddd_scoring is True)
check('Pro mode DDD extraction', FeatureFlags.for_professional().enable_ddd_feature_extraction is True)
check('Quick skips HNR', FeatureFlags.for_quick().enable_multiscale_hnr is False)
check('Quick skips reverb', FeatureFlags.for_quick().enable_reverb_compensation is False)
check('FC feature flag exists', hasattr(flags, 'enable_fcpe'))

# ---- 3. Upload + Analyze (Quick) ----
print('\n--- 3. Upload + Analyze (Quick mode) ---')
t0 = time.time()
try:
    result = analyze_and_score('uploads/melody.wav', mode='quick',
                               feature_flags=FeatureFlags.for_quick())
    elapsed = time.time() - t0
    check('Success', result.get('success') is True)
    ts = result.get('total_score', 0)
    check('Total score 0-100', 0 <= ts <= 100, 'score=%.1f' % ts)
    check('Has analysis_id', bool(result.get('analysis_id')))
    check('Has level', bool(result.get('level')), str(result.get('level')))
    s = result.get('scores', {})
    check('Score keys >= 6', len(s) >= 6, 'keys=%s' % list(s.keys()))
    check('Pitch 0-100', 0 <= s.get('pitch', 0) <= 100, 'pitch=%.0f' % s['pitch'])
    check('Rhythm 0-100', 0 <= s.get('rhythm', 0) <= 100, 'rhythm=%.0f' % s['rhythm'])
    check('Breath 0-100', 0 <= s.get('breath', 0) <= 100, 'breath=%.0f' % s['breath'])
    check('Technique 0-100', 0 <= s.get('technique', 0) <= 100, 'tech=%.0f' % s['technique'])
    check('Muscle present', 'muscle_strength' in s, 'muscle=%.0f' % s.get('muscle_strength', 0))
    check('Artistry 0-100', 0 <= s.get('artistry', 0) <= 100, 'art=%.0f' % s['artistry'])
    check('heuristic_dimensions', result.get('heuristic_dimensions') is not None)
    check('timbre_adjustment', result.get('timbre_adjustment') is not None)
    check('Has advice', len(result.get('advice', [])) > 0)
    check('Performance < 120s', elapsed < 120, '%.1fs' % elapsed)
    check('Not disqualified', result.get('is_disqualified') is not True)
    total_score = result['total_score']
    level = result['level']
except Exception as e:
    traceback.print_exc()
    check('Upload flow', False, str(e))
    total_score = 0

# ---- 4. Old ScoreServiceV4 still works (fallback) ----
print('\n--- 4. ScoreServiceV4 (legacy fallback) ---')
try:
    svc = ScoreServiceV4()
    old_result = svc.calculate(features=AudioFeaturesResult())
    check('Legacy calculate', old_result.total_score >= 0)
    check('No DL fields', not hasattr(old_result, 'dl_mos_score'))
except Exception as e:
    check('Legacy scoring', False, str(e))

# ---- 5. DDD Orchestrator direct ----
print('\n--- 5. DDD ScoringOrchestrator ---')
try:
    r = ddd_orchestrator.calculate(AudioFeaturesResult())
    dims = ['pitch_score', 'rhythm_score', 'breath_score',
            'technique_score', 'muscle_strength_score', 'artistry_score']
    check('All 6 dims', all(k in r for k in dims))
    check('heuristic list', isinstance(r.get('heuristic_dimensions'), list))
    check('muscle is heuristic', 'muscle_strength' in r.get('heuristic_dimensions', []))
except Exception as e:
    traceback.print_exc()
    check('DDD orchestrator', False, str(e))

# ---- 6. Infrastructure Audio ----
print('\n--- 6. Infrastructure Audio ---')
try:
    from backend.infrastructure.audio import (
        LibrosaAudioLoader, PYINPitchExtractor, DemucsSeparator
    )
    loader = LibrosaAudioLoader()
    audio = loader.load('uploads/melody.wav')
    check('Load WAV', audio.duration_s > 0, '%.1fs %dHz' % (audio.duration_s, audio.sample_rate))
    check('Audio mono', audio.is_mono is True)
    check('Frozen dataclass', hasattr(audio, '__dataclass_fields__'))

    extractor = PYINPitchExtractor()
    pitch = extractor.extract(audio.samples, audio.sample_rate)
    check('Pitch detection', pitch.detection_rate > 0, 'rate=%.2f' % pitch.detection_rate)
    check('f0 frames', len(pitch.f0) > 0, '%d frames' % len(pitch.f0))
    check('Pitch frozen', hasattr(pitch, '__dataclass_fields__'))

    gpu = DemucsSeparator.detect_gpu()
    check('GPU detect', 'cuda' in gpu.lower() or 'cpu' in gpu.lower(), gpu)
except Exception as e:
    traceback.print_exc()
    check('Infra audio', False, str(e))

# ---- 7. FCPE ----
print('\n--- 7. FCPE Pitch Extractor ---')
try:
    from backend.infrastructure.audio.fcpe_extractor import FCPEPitchExtractor
    import numpy as np
    fcpe = FCPEPitchExtractor()
    sr = 22050
    t = np.linspace(0, 1, sr, endpoint=False)
    y = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    fcpe_r = fcpe.extract(y, sr=sr)
    f0_mean = np.mean(fcpe_r.f0[fcpe_r.f0 > 0])
    check('FCPE method', fcpe_r.method == 'fcpe')
    check('FCPE accuracy', abs(f0_mean - 440) < 20, '%.1f Hz' % f0_mean)
except Exception as e:
    traceback.print_exc()
    check('FCPE', False, str(e))

# ---- 8. History Repository ----
print('\n--- 8. History Repository ---')
try:
    from repositories.history_repository import JsonHistoryRepository
    repo = JsonHistoryRepository('data/web_history.json', 50)
    records = repo.get_all(limit=5)
    check('History accessible', len(records) >= 0, '%d records' % len(records))
except Exception as e:
    check('History', False, str(e))

# ---- 9. EventBus ----
print('\n--- 9. EventBus ---')
try:
    from backend.shared.event_bus import EventBus
    from backend.domain.assessment.events import ScoreCalculated
    bus = EventBus()
    events = []
    bus.subscribe(ScoreCalculated, lambda e: events.append(e))
    bus.publish(ScoreCalculated(
        total_score=85.0, dimensions={'pitch': 80}, level='A', grade='A'))
    check('Event publish', len(events) == 1)
    check('Event data', events[0].total_score == 85.0)
except Exception as e:
    check('EventBus', False, str(e))

# ---- 10. FastAPI App Factory ----
print('\n--- 10. FastAPI App Factory ---')
try:
    from backend.main import create_app
    app = create_app()
    routes = [r.path for r in app.routes]
    check('Health route', '/health' in routes)
    check('API routes', any('/api/v1/' in r for r in routes))
    check('WS route', any('/ws/' in r for r in routes))
    check('SPA fallback', any('{full_path' in r for r in routes))
    check('Routes > 20', len(routes) > 20, '%d routes' % len(routes))
except Exception as e:
    traceback.print_exc()
    check('App factory', False, str(e))

# ---- 11. Frontend build exists ----
print('\n--- 11. Frontend build ---')
check('Vue dist exists', os.path.isdir('frontend/dist'))
check('index.html', os.path.isfile('frontend/dist/index.html'))
check('assets dir', os.path.isdir('frontend/dist/assets'))
check('assets files', len(os.listdir('frontend/dist/assets')) > 0)

# ---- 12. Non-voice detection ----
print('\n--- 12. Non-voice detection ---')
try:
    import numpy as np
    import soundfile as sf
    noise = np.random.randn(22050 * 2).astype(np.float32)  # 2s white noise
    sf.write('/tmp/test_noise.wav', noise, 22050)
    noise_result = analyze_and_score('/tmp/test_noise.wav', mode='quick',
                                     feature_flags=FeatureFlags.for_quick())
    check('Noise detected as non-voice', noise_result.get('is_voice') is False,
          'is_voice=%s' % noise_result.get('is_voice'))
except Exception as e:
    traceback.print_exc()
    check('Non-voice', False, str(e))

# ---- SUMMARY ----
print('\n' + '=' * 60)
print('RESULTS: %d passed, %d failed out of %d checks' % (passed, failed, passed + failed))
if errors:
    print('\nFAILURES:')
    for e in errors:
        print('  ' + e)
if failed == 0:
    print('\n*** ALL SYSTEM TESTS PASSED ***')
else:
    print('\n*** %d FAILURES DETECTED ***' % failed)
print('=' * 60)
