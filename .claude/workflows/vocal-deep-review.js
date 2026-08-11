export const meta = {
  name: 'vocal-deep-review',
  description: 'Deep review of the vocal assessment project across 8 dimensions with adversarial verification',
  phases: [
    { title: 'Review', detail: '8 parallel dimension reviewers' },
    { title: 'Verify', detail: 'adversarial verification of every finding' },
  ],
}

const ROOT = 'c:/Users/jack/Desktop/临时文件/声乐/vocal_assessment_light'

const FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          severity: { type: 'string', enum: ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] },
          title: { type: 'string', description: 'One-line title of the issue' },
          file: { type: 'string', description: 'Repo-relative file path (e.g. backend/domain/assessment/pitch_scorer.py)' },
          line_ref: { type: 'string', description: 'Optional line number or line range reference' },
          description: { type: 'string', description: 'What the issue is, 2-4 sentences' },
          evidence: { type: 'string', description: 'The concrete code/documentation evidence found (quote key lines)' },
          impact: { type: 'string', description: 'Concrete user/performance/stability/score impact if realized' },
          recommendation: { type: 'string', description: 'A specific fix suggestion' },
        },
        required: ['severity', 'title', 'file', 'description', 'evidence', 'impact', 'recommendation'],
      },
    },
  },
  required: ['findings'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['CONFIRMED', 'PLAUSIBLE', 'REFUTED'] },
    evidence_check: { type: 'string', description: 'What you actually read in the real code to check this claim' },
    analysis: { type: 'string', description: 'Why you confirmed/refuted it, citing real lines' },
  },
  required: ['verdict', 'evidence_check', 'analysis'],
}

const SHARED_CTX = `
PROJECT ROOT: ${ROOT}
This is an offline vocal assessment web app: FastAPI (backend/) + Vue3/Element Plus SPA (frontend/src/).
Architecture claims DDD layering: backend/domain (pure), backend/application (orchestration), backend/infrastructure (SQLite/audio IO), backend/interfaces (FastAPI routes + WebSocket).
Legacy service layer: services/ (~9800 lines) and api/business/ (~600 lines) — supposedly being 'strangled out' by DDD.
Docs live in docs/1-product/, docs/2-technical/, docs/4-process/ (PROJECT_STATUS.md is the status bible, claims v7.14, 633 backend tests, 297 frontend Vitest).
Known recent feature (v7.14): upload auto-match to song library. Known earlier feature (v7.13): real-time pitch comparison.
Read real files with the Read tool; search with Grep. Quote actual line numbers in evidence. Be skeptical and precise — only report issues with real evidence. For each finding give severity: CRITICAL (blocks correctness/security/data-loss), HIGH (significant bug/quality), MEDIUM (maintainability/edge-case), LOW (style/nitpick). Aim for 3-12 high-signal findings per dimension, prioritize genuine issues over nitpicks. Do NOT report style preferences without a concrete cost.
`

const DIMENSIONS = [
  {
    key: 'docs-alignment',
    prompt: `${SHARED_CTX}
YOU ARE THE DOCUMENTATION-ALIGNMENT AUDITOR. Your job: cross-check every concrete claim in the docs against the actual code, and every code behavior against the docs. Read these docs first: docs/2-technical/API_CONTRACT.md, docs/2-technical/SCORING.md, docs/4-process/PROJECT_STATUS.md, README.md, docs/1-product/GOALS.md. Then read the actual route files: backend/interfaces/api/routes/*.py, backend/interfaces/api/schemas/*.py, backend/interfaces/ws/*.py, backend/domain/assessment/scoring_weights.py.

CHECK LIST:
1. Every API endpoint claimed in docs: does the route exist with the exact method+path? E.g. /api/v1/upload, /analyze, /compare, /separate, /extract-pitch, /report, /flags, /scoring/presets, /scoring/apply-weights, /history, /songs, /songs/{id}/pitch, /songs/{id}/compare, /songs/match, /audio, /ws/v1/score. Report any missing/misrouted.
2. Response shapes: docs claim specific JSON fields (e.g. compare returns standard_pitch/user_pitch/low_alignment_segments; upload with auto_match injects matched_song/matched_candidates/fallback_reason; songs/match returns matched/candidates/fallback_reason/detected_key/partial/elapsed_ms). Verify each against the schema/route code.
3. Version consistency: main.py declares title='VAS v7.13', version='7.13.0' but the project is v7.14 (README, PROJECT_STATUS, last commit). Confirm whether this is stale. Also check frontend/package.json version.
4. Scoring weights: docs say 13/12/22/25/15/13. Verify ScoringWeights.default() and every place weights are hardcoded.
5. Test counts: PROJECT_STATUS claims 633 backend + 297 frontend Vitest. Check if these are plausible from the test files (do not run tests; just count test functions in tests/unit/domain, tests/unit/infrastructure, tests/integration, tests/extended and frontend/tests). Report large discrepancies.
6. Feature claims in README (v7.14 auto-match, v7.13 five phases) — spot-check that the named files/endpoints exist (backend/domain/song_match/, POST /songs/match, CompareView auto-match area, frontend/src/stores/songMatch.store.ts).
7. Flag system: docs describe GET /api/v1/flags and DimensionFlags. Verify.
8. Any doc claim that is factually contradicted by code, and any code that has no doc coverage.

Return your findings in the schema.`,
  },
  {
    key: 'architecture-coupling',
    prompt: `${SHARED_CTX}
YOU ARE THE ARCHITECTURE & COUPLING AUDITOR. Focus: DDD layering compliance, coupling, duplication, dead code, and the 'strangler' migration completeness.

CHECK LIST:
1. DDD layering violations: search backend/domain/ for imports of backend.infrastructure, backend.interfaces, services, or api.business. Domain must be pure (protocols only). Report any domain module that imports infra/interfaces or does filesystem/HTTP work directly.
2. Circular imports: look for obvious import cycles between backend modules (application<->interfaces, domain<->application). Check the route modules import deps correctly.
3. Legacy strangle completeness: services/ has ~9800 lines (audio_service.py 830, phrase_service.py 630, style_aware_scorer.py 517, dl_services/*). Determine which are ACTUALLY imported by the production path (backend/interfaces/api/routes/assessment.py, ws/score_handler.py) vs dead. README claims 'v7.12 dl_services dead code cleanup' and 'Flask /old removed v7.6' — verify the current production import graph. Report legacy modules still hot in the request path that duplicate DDD logic (two sources of truth for scoring/analysis).
4. File size violations: README/rules cap ~800 lines. Files over 800 lines: frontend/src/views/CompareView.vue (1189), SingView.vue (881), services/audio_service.py (830). Check backend for >800-line files and frontend >800-line files. Note them with coupling risk.
5. Duplicate logic: check whether scoring weights / scoring formulas exist in BOTH backend/domain and services/ (e.g. _score_lightweight in ws/score_handler.py vs ScoringWeights — was it really unified in v7.13?). Search for hardcoded weight tuples like (10,10,20,25,25,10) or (13,12,22,25,15,13) anywhere in the codebase.
6. Dead code: unused modules, unused imports (spot check a few big files), __pycache__-only references, legacy features/types.py DeprecationWarning status.
7. Coupling between layers: do routes call services/ directly? Does application import interfaces? Does anything bypass the application layer and call domain from routes?
8. Is there a clean data flow: route to application use-case to domain service to infrastructure repo? Or do routes call domain/repo directly (leaky layering)?

Return findings in the schema with concrete import/file evidence.`,
  },
  {
    key: 'runtime-stability',
    prompt: `${SHARED_CTX}
YOU ARE THE RUNTIME-STABILITY & SILENT-FAILURE AUDITOR. Focus: will this crash or fail silently in production. The user specifically fears silent crashes.

CHECK LIST:
1. Silent exception swallowing: Grep for bare 'except:', 'except Exception:', 'except Exception as e: pass', 'except BaseException', bare 'pass' in except bodies, and ignored exceptions across backend/, services/, api/business/. Identify blocks that swallow errors and return fake/garbage results (e.g. feature extractor returning zeros/None on failure instead of propagating). Especially backend/domain/audio/*, backend/application/assessment/ddd_feature_orchestrator.py, scoring_orchestrator.py, and api/business/audio_analysis.py.
2. WebSocket failure modes: read backend/interfaces/ws/score_handler.py and streaming_session.py. What happens if: the client disconnects mid-stream? The analysis throws? The WS message is malformed? Is there try/except around the send loop? Is the session cleaned up? Note that main.py's global exception handler only covers HTTP, not WS — confirm.
3. Error propagation in async handlers: do FastAPI routes that call heavy sync code (librosa, demucs, parselmouth) run it in a thread pool (run_in_executor/anyio.to_thread/starlette run_in_threadpool) or block the event loop? Check assessment.py upload route, compare, songs_pitch GET /songs/{id}/pitch (claimed thread pool).
4. Thread-safety: SQLite access from multiple threads (sqlite_song_match_profile_repo claims a thread lock; sqlite_song_repo?), the KMP_DUPLICATE_LIB_OK=TRUE global env hack, librosa/parselmouth thread safety. Race conditions on shared in-memory state (InMemoryPitchCacheRepository).
5. Input validation: is user input validated at boundaries (file extension, size, path traversal, top_n bounds, negative/zero values)? Look at route handlers and config.
6. Resource cleanup on failure: uploaded temp files deleted on error? Are there leaked files in uploads/ (check if uploads/ is cleaned)?
7. Config resolution: read backend/infrastructure/config.py — are settings read at import time vs runtime? Any env var that would crash at startup if missing? Any mismatch between requirements.txt and imports (e.g. torchfcpe, torchcrepe imported but not installed)?
8. Startup: could main.py fail to import in a fresh env? Any import inside lifespan that throws?
9. Retry/timeout: DL model load timeouts, long-running operations with no timeout, requests without timeouts.

Return findings in the schema with concrete evidence.`,
  },
  {
    key: 'memory-leaks',
    prompt: `${SHARED_CTX}
YOU ARE THE MEMORY-LEAK / RESOURCE-LIFECYCLE AUDITOR. Focus: unbounded growth over a long-lived server or long session.

CHECK LIST:
1. Caches that never evict: InMemoryPitchCacheRepository (backend/domain/songs_pitch or infrastructure) — is it a dict that grows forever per song ID? lru_cache singletons in backend/interfaces/api/deps.py (get_song_match_profile_repo, get_auto_match_use_case) — what do they hold? Any dict keyed by upload id / song id that grows without bound?
2. WebSocket session lifecycle: backend/interfaces/ws/* — on disconnect, are session objects, buffers, and references removed from any global registry? Grep for global lists/dicts of sessions. Do completed recordings release the audio buffers (numpy arrays)?
3. Frontend timers/listeners: in the big views (SingView.vue, CompareView.vue, ReportView.vue, HomeView.vue) and components (PitchComparisonCanvas.vue, WaveformCanvas.vue) — are setInterval/setTimeout/requestAnimationFrame cleaned up in onUnmounted? Are event listeners (window keydown, resize) added/removed? Does the GSAP pulse animation get killed? Check for setInterval without clearInterval.
4. Frontend store growth: Pinia stores (songs.store, songMatch.store, history.store, assessment.store) — do they keep unbounded arrays (e.g. pitch data per comparison, history pages)? Any cache maps that never clear?
5. Large object retention: matplotlib figures closed? numpy arrays in module globals? app.state holding big objects? Waveform/spectrogram image blobs retained?
6. File handles: is soundfile/librosa io opened with context managers? Any open() without close in services/audio_service.py or api/business/audio_analysis.py?
7. Audio buffers in upload pipeline: after an analysis completes, is the decoded audio array released or kept in a registry?
8. Electron side: frontend/electron/* — any obvious leaks (not critical).

Return findings in schema. Distinguish CONFIRMED leaks (clear evidence of unbounded growth) from PLAUSIBLE risks.`,
  },
  {
    key: 'performance',
    prompt: `${SHARED_CTX}
YOU ARE THE PERFORMANCE AUDITOR. Focus: whether performance meets the documented budgets and whether the app stays responsive.

CONTEXT FROM DOCS: README claims Quick ~30-40s, Pro ~3-5min (docs/1-product/GOALS.md says Quick ~20s, Pro ~155s CPU/~55s GPU). docs/2-technical/PERFORMANCE_ANALYSIS_AND_OPTIMIZATION.md has the performance plan. WebSocket pushes pitch every 2s. Files up to 50MB.

CHECK LIST:
1. Blocking the event loop: FastAPI async routes that call librosa/parselmouth/numpy/demucs synchronously will freeze ALL requests. Check backend/interfaces/api/routes/assessment.py (upload/analyze/compare/separate/extract-pitch), songs_pitch.py, song_match.py, and ws/score_handler.py. Are heavy calls wrapped in run_in_executor/threadpool? The /songs/{id}/pitch route claims 'thread pool' — verify. The /upload route is the critical one.
2. Whole-file decode: 50MB files decoded into memory? librosa.load with sr=22050 mono — fine; but is the full array processed at once (not streamed)? Any sr=None full-res decode?
3. N+1 / missing pagination: backend/infrastructure/persistence/sqlite_song_repo.py list queries, history queries — any per-item queries in a loop? songs list_all_with_filepath used by match profile precompute.
4. Feature extraction redundancy: does the upload pipeline extract features more than once (e.g. DDD orchestrator + legacy audio_service both run)? Is that a big time cost?
5. Frontend render performance: PitchComparisonCanvas.vue draws per-frame — is it using requestAnimationFrame, throttling, DPR handling? pitchFps.ts claims FPS-based degradation — does it actually reduce work? CompareView 1189 lines — any per-second full re-renders of large arrays? pitchLive.ts O(n) dot rendering — is n bounded?
6. WS batching: 2s pitch pushes — is the payload size sane? Any unbounded queue if client is slow?
7. SQLite: WAL mode? indexes? songs_match_profiles table indexing?
8. Matplotlib/visualization: are plots generated per request? Memory/time cost.

Report only evidence-backed findings; include the code path and lines. Return in schema.`,
  },
  {
    key: 'scoring-objectivity',
    prompt: `${SHARED_CTX}
YOU ARE THE SCORING OBJECTIVITY & FAIRNESS AUDITOR. Focus: is the six-dimension score objectively computed, deterministic, and fair — and does the code match the documented algorithm.

READ FIRST: docs/2-technical/SCORING.md, docs/2-technical/SCORING_ALGORITHM_IMPROVEMENT_PLAN.md, then backend/domain/assessment/*.py (all scorers + scoring_weights.py + value_objects.py), backend/domain/audio/*.py extractors, backend/application/assessment/scoring_orchestrator.py, ddd_feature_orchestrator.py, and tests/integration/test_real_audio_regression.py.

CHECK LIST:
1. Single source of truth for weights: ScoringWeights.default() = (13,12,22,25,15,13)? Search the ENTIRE repo for hardcoded weight tuples or literal numbers like 10,10,20,25,25,10 (the old buggy weights) and 0.13,0.12,0.22,0.25,0.15,0.13. Check ws/score_handler.py _score_lightweight still uses ScoringWeights (was supposedly fixed v7.13).
2. Determinism: same audio file to the same scores? Any randomness (numpy random, sampling, nondeterministic ordering) in extraction/scoring? Any dependence on dict ordering or hash seeds?
3. Magic numbers & thresholds: enumerate unexplained constants in scorers (e.g. MAE breakpoints, HNR thresholds, CPPS rescale, breath thresholds). Are they documented/literature-backed or arbitrary? Does SCORING.md match the actual constants?
4. Heuristic labeling: docs mark Muscle as HEURISTIC and timbre as proxy. Verify these are honestly labeled in code comments and the score is not presented as objective fact. Is there any dimension that is essentially fabricated proxy yet presented as accurate?
5. Baseline/calibration: read tests/integration/test_real_audio_regression.py BASELINE_V7_6. The docs admit 4 breath dimension FAILs (0.1-0.8 pts out of range). What does that mean — is breath scoring calibrated? Assess whether the scoring pipeline is trustworthy given known drift.
6. Range clamping & non-linear behavior: score ranges (Quick 60-90 smooth vs Pro 0-100), clamp[0,100], timbre adjust +3~-5. Are clamps masking real data? Does a near-silent or noise-only file score reasonably (not a random 70-80)?
7. Edge inputs: empty audio, 1s audio, 50MB file, stereo vs mono, low sample rate — handled gracefully or crash/zero?
8. weighted_total correctness: ScoringWeights.weighted_total() math correct? Presets (pop/classical/folk/rap) applied correctly with muscle 15%?

Return findings in schema. This is the user's key concern (scoring objectivity) so be rigorous and cite actual thresholds/lines.`,
  },
  {
    key: 'frontend-quality',
    prompt: `${SHARED_CTX}
YOU ARE THE FRONTEND QUALITY & RUNTIME AUDITOR. Focus: Vue 3 SPA correctness, lifecycle, state management, and whether it runs without silent failures.

FILES: frontend/src/views/*.vue (CompareView 1189, SingView 881, SongsView 770, HomeView 576, ReportView 503, HistoryView 346), frontend/src/components/*.vue + components/scoring/*, frontend/src/stores/*.ts, frontend/src/composables/*.ts, frontend/src/utils/pitch*.ts, frontend/src/api/client.ts.

CHECK LIST:
1. Lifecycle cleanup: onUnmounted cleanup of intervals/timers/WS/event listeners in SingView (recording, WS, pulse animation), CompareView (playback, keyboard shortcuts), PitchComparisonCanvas (rAF loop, A-B loop), ReportView (GSAP). Grep for setInterval/setTimeout/addEventListener/requestAnimationFrame and check each has a matching clear/remove.
2. WebSocket robustness: frontend/src/composables/useWebSocket.ts — reconnection logic, backoff, onerror handling, close during route navigation. Does a dropped WS kill the page silently? Does SingView handle WS error/close?
3. Error feedback: do fetch failures show user-visible errors (ElMessage) or silently no-op? Check stores' catch blocks. songMatch.store, songs.store, assessment.store, history.store.
4. State bugs: assessment.store, songMatch.store state shape; CompareView auto-match flow (upload to candidates to select to compare) — any stale state when song changes? PitchComparisonCanvas live-mode dot rendering (pitchLive.ts) — alpha fade correctness, clock alignment (100ms wall clock).
5. Type safety claims: docs claim vue-tsc 0 errors. Spot-check for 'any' casts, unsafe (window as any).__store usage, missing null guards on API responses.
6. Canvas correctness: PitchComparisonCanvas DPR handling, resize handling, coordinate transforms (CSS px vs device px), clearing the canvas on unmount.
7. Accessibility/UX: buttons with click handlers, aria, reduced-motion handling (claims double protection).
8. Mobile/responsive: claims responsive — check the big views have basic responsive handling.

Return findings in schema with component/file + line evidence.`,
  },
  {
    key: 'test-quality',
    prompt: `${SHARED_CTX}
YOU ARE THE TEST-QUALITY & COVERAGE-GAP AUDITOR. Focus: do the 633 backend + 297 frontend tests actually prove the system works, or are they hollow? Are critical paths covered?

READ: tests/unit/domain/**, tests/unit/infrastructure/**, tests/integration/** (api_routes, songs_api, scoring_api, songs_pitch_api, compare_pitch_api, song_match_api, test_real_audio_regression), tests/extended/**, tests/bdd/** (features + step defs), frontend/tests/** (stores, pitch utils).

CHECK LIST:
1. Assertion strength: sample tests across suites — do they assert specific output values (real behavioral verification) or just assert 'no exception' / 'status 200' (smoke)? Count proportion roughly. Read several test files and quote examples of weak assertions.
2. Critical-path coverage: is the full scoring pipeline (upload to feature extraction to scoring to response) tested end-to-end with REAL audio, or with heavily mocked feature extractors? Check tests/integration/test_api_routes.py — do they mock librosa/audio analysis or run real extraction? If real, are the audio fixtures tiny/fake?
3. The 4 failing breath baseline tests: read the baseline regression test + the assertions. Is the scoring pipeline objectively validated by these, or are the baselines so loose as to be meaningless? Does the suite have tests that would catch a scoring regression (not just range checks)?
4. BDD XFAIL trend: PROJECT_STATUS lists many XFAIL scenarios (pitch-realtime 25 XFAIL, sing-song-select 6 XFAIL, animations 9 XFAIL, auto-match 3 XFAIL, database 6 XFAIL, upload 3 SKIP). Read a couple of these features + step defs. Are XFAILs masking unimplemented features that docs claim are done? Is there a risk that '100% GREEN' really means 'mostly skipped'?
5. Frontend tests: read frontend/tests/unit/stores/songMatch.test.ts and a pitch util test. Are they testing behavior with real logic, or testing mocked fetch implementation details? Vitest counts (297) — do they map to meaningful assertions?
6. Coverage of error paths: are failure modes (invalid file, timeout, WS disconnect, malformed response) tested? Grep tests for pytest.raises / error cases.
7. Dead/brittle tests: tests that test implementation details (would break on refactor without behavior change), tests with timeouts that could flake, tests that share global state / pollute data dirs (songs.db leak was fixed per git log — verify).
8. Test isolation: do integration tests touch real files (uploads/, data/)? Side effects on the real app data?

Return findings in schema. Distinguish 'test is hollow' from 'test is fine'.`,
  },
]

function verifyPrompt(dim, f) {
  return `${SHARED_CTX}
You are an ADVERSARIAL VERIFIER. A ${dim.key} reviewer reported the following finding. Your job is to INDEPENDENTLY check whether it is real. Default to skepticism: try hard to refute it. Read the actual file(s) at the reported path (relative to ${ROOT}), follow the code path, and decide.

FINDING:
- Severity: ${f.severity}
- Title: ${f.title}
- File: ${f.file}
- Line ref: ${f.line_ref || 'n/a'}
- Description: ${f.description}
- Evidence claimed: ${f.evidence}
- Impact claimed: ${f.impact}

Verify by reading the real code. Report:
- verdict: CONFIRMED (the issue is real as described), PLAUSIBLE (the issue may be real but depends on context/conditions not fully verified), or REFUTED (the claim is wrong — code does not behave as described).
- evidence_check: exactly what you read.
- analysis: cite real line numbers and explain.
If the finding is CONFIRMED, also note the exact line numbers where the problem lives.`
}

phase('Review')
const results = await pipeline(
  DIMENSIONS,
  (d) => agent(d.prompt, { label: 'review:' + d.key, phase: 'Review', schema: FINDINGS_SCHEMA }),
  (review, d) => {
    const findings = review && Array.isArray(review.findings) ? review.findings : []
    return parallel(findings.map((f) => () =>
      agent(verifyPrompt(d, f), { label: 'verify:' + d.key + ':' + f.file, phase: 'Verify', schema: VERDICT_SCHEMA })
        .then((v) => ({ ...f, dimension: d.key, verdict: v || { verdict: 'PLAUSIBLE', evidence_check: 'verifier returned null', analysis: 'verifier failed to run' } }))
    ))
  }
)

return results
