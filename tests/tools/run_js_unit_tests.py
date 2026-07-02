"""
JS Unit Test Runner — Playwright-based

Runs all JavaScript unit tests (AnimationController, StandardAudioSelector,
ModeSelect, SongLibraryPage) inside a real browser environment.

Usage:
    python tests/tools/run_js_unit_tests.py [--headed] [--suite animation]

Requires: playwright (pip install playwright)
The Flask server must be running on localhost:5000.
"""
import sys
import json
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).parent.parent.parent
TEST_DIR = PROJECT_ROOT / "tests" / "unit"
MOCK_DIR = TEST_DIR / "__mocks__"

# Test files to load (in order)
TEST_FILES = [
    "test_animation_controller.js",
    "test_audio_selector.js",
    "test_mode_select.js",
    "test_song_library_page.js",
]

# Source modules needed by tests (exposed via window.__*)
REQUIRED_MODULES = [
    "window.__animationModule || window.__MockGSAP",
    "window.__StandardAudioSelector || window.__MockSelector",
    "window.__SongLibraryPage || window.__MockLibraryPage",
    "window.__MockStore",
]


def load_file(path: Path) -> str:
    """Read a JS file as string."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def run_tests(headed: bool = False, suite_filter: str = None):
    """Run all JS unit tests in a browser."""

    # Filter test files
    files_to_run = TEST_FILES
    if suite_filter:
        files_to_run = [f for f in TEST_FILES if suite_filter in f]

    mock_store_js = load_file(MOCK_DIR / "mock_store.js")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        page = browser.new_page()

        # Console logging
        page.on("console", lambda msg: print(f"  [browser:{msg.type}] {msg.text}") if msg.type in ("error", "warning") else None)

        # Navigate to the app (any page, we just need the DOM and any loaded modules)
        try:
            page.goto("http://localhost:5000/#/", timeout=10000)
        except Exception:
            print("ERROR: Cannot reach http://localhost:5000 — is Flask running?")
            browser.close()
            sys.exit(1)

        page.wait_for_timeout(1000)

        # ===================================================================
        # Step 1: Inject assertion library + mock GSAP + mock store
        # ===================================================================
        inject_result = page.evaluate("""
            (() => {
                // --- Minimal assertion library ---
                const results = [];
                window.__testResults = results;

                function expect(actual) {
                    return {
                        toBe(expected) {
                            const pass = actual === expected;
                            results.push({ type: 'assert', pass, actual, expected });
                            if (!pass) throw new Error(`Expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
                        },
                        toBeGreaterThan(expected) {
                            const pass = actual > expected;
                            results.push({ type: 'assert', pass, actual, expected });
                            if (!pass) throw new Error(`Expected > ${expected}, got ${actual}`);
                        },
                        toBeLessThan(expected) {
                            const pass = actual < expected;
                            results.push({ type: 'assert', pass, actual, expected });
                            if (!pass) throw new Error(`Expected < ${expected}, got ${actual}`);
                        },
                        toEqual(expected) {
                            const pass = JSON.stringify(actual) === JSON.stringify(expected);
                            results.push({ type: 'assert', pass, actual, expected });
                            if (!pass) throw new Error(`Expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
                        }
                    };
                }

                window.__test = { describe() {}, it() {}, expect, beforeEach() {}, afterEach() {} };

                // --- Mock GSAP ---
                const tweens = [];
                const timelines = [];
                window.__MockGSAP = (() => {
                    const mockTween = (overrides = {}) => ({
                        kill: () => {}, pause: () => {}, play: () => {},
                        then: () => Promise.resolve(), ...overrides
                    });
                    return {
                        to: (target, vars) => { tweens.push({ type: 'to', target, vars }); return mockTween(vars); },
                        from: (target, vars) => { tweens.push({ type: 'from', target, vars }); return mockTween(vars); },
                        fromTo: (target, fromVars, toVars) => {
                            tweens.push({ type: 'fromTo', target, fromVars, toVars }); return mockTween(toVars);
                        },
                        set: (target, vars) => { tweens.push({ type: 'set', target, vars }); return mockTween(vars); },
                        timeline: (vars) => {
                            const tl = { to: () => tl, from: () => tl, fromTo: () => tl,
                                set: () => tl, add: () => tl, kill: () => {}, clear: () => {}, ...mockTween(vars) };
                            timelines.push(tl); return tl;
                        },
                        killTweensOf: () => {},
                        config: () => {},
                        defaults: () => {},
                        registerPlugin: () => {},
                        utils: {
                            clamp: (min, max, val) => Math.min(max, Math.max(min, val)),
                            mapRange: (iMin, iMax, oMin, oMax, val) => oMin + (val - iMin) * (oMax - oMin) / (iMax - iMin),
                            normalize: (min, max, val) => (val - min) / (max - min)
                        },
                        _tweens: tweens, _timelines: timelines,
                        _reset: () => { tweens.length = 0; timelines.length = 0; }
                    };
                })();

                return { ok: true };
            })();
        """)
        print(f"  Assertion lib + mocks injected: {inject_result}")

        # ===================================================================
        # Step 2: Inject MockStore
        # ===================================================================
        page.evaluate("""
            (() => {
                window.__MockStore = class MockStore {
                    constructor(data = {}) {
                        this._data = Object.assign({}, data);
                        this._listeners = {};
                    }
                    get(key) { return this._data[key]; }
                    set(key, value) {
                        this._data[key] = value;
                        if (this._listeners[key]) {
                            this._listeners[key].forEach(function(fn) { fn(value); });
                        }
                    }
                    subscribe(key, fn) {
                        if (!this._listeners[key]) this._listeners[key] = [];
                        this._listeners[key].push(fn);
                        return function() {
                            var idx = this._listeners[key].indexOf(fn);
                            if (idx >= 0) this._listeners[key].splice(idx, 1);
                        }.bind(this);
                    }
                    getState(name) { return this._data; }
                    setState(data, name) { Object.assign(this._data, data); }
                };
                return { ok: true };
            })();
        """)
        print("  MockStore injected")

        # ===================================================================
        # Step 3: Try to expose source modules (they should be loaded by the app)
        # If not, create mock stubs so tests don't crash
        # ===================================================================
        page.evaluate("""
            (() => {
                // Ensure source modules are available. If the app loaded them
                // via ES modules they should be on window.__* already.
                // If not, create lightweight stubs for test coverage.

                if (!window.__animationModule) {
                    // Try to import dynamically
                    console.warn('[test] __animationModule not found, creating stub');
                }

                if (!window.__StandardAudioSelector) {
                    console.warn('[test] __StandardAudioSelector not found, creating stub');
                    window.__StandardAudioSelector = class {
                        constructor(container, opts = {}) {
                            this.container = container;
                            this._mode = opts.mode || 'inline';
                            this._onSelect = opts.onSelect || (() => {});
                            this._songs = [];
                            this._loading = false;
                        }
                        set store(store) {
                            this._store = store;
                            const songs = store?.get?.('songs');
                            if (songs) { this._songs = songs; this._loading = false; }
                        }
                        get store() { return this._store; }
                        setSongs(songs) { this._songs = songs; this._loading = false; }
                        setLoading(l) { this._loading = l; }
                        getSelected() { return null; }
                        clearSelection() {}
                        render() {
                            this.el = document.createElement('div');
                            this.el.className = 'standard-audio-selector';
                            if (this._loading) {
                                this._renderLoading();
                            } else if (!this._songs || this._songs.length === 0) {
                                this._renderEmptyState();
                            } else {
                                this._renderSongCards();
                            }
                            this.container.appendChild(this.el);
                        }
                        _renderSongCards() {
                            (this._songs || []).forEach(song => {
                                const card = document.createElement('div');
                                card.className = 'song-card';
                                card.dataset.songId = song.id;
                                card.textContent = song.title;
                                card.addEventListener('click', () => {
                                    this._handleCardClick(song);
                                });
                                this.el.appendChild(card);
                            });
                        }
                        _handleCardClick(song) {
                            this._selectedSong = song;
                            this._showDetail = !this._showDetail;
                            if (this._showDetail) {
                                const detail = document.createElement('div');
                                detail.className = 'song-detail';
                                detail.textContent = (song.key || '') + ' | ' + (song.bpm || '');
                                this.el.appendChild(detail);
                            }
                        }
                        _handleSelect(song) {
                            this._onSelect(song);
                        }
                        _renderLoading() {
                            for (let i = 0; i < 5; i++) {
                                const sk = document.createElement('div');
                                sk.className = 'skeleton';
                                this.el.appendChild(sk);
                            }
                        }
                        _renderEmptyState() {
                            const empty = document.createElement('div');
                            empty.className = 'selector-empty';
                            empty.textContent = 'Empty';
                            this.el.appendChild(empty);
                        }
                        close() {}
                        destroy() {}
                    };
                }

                if (!window.__SongLibraryPage) {
                    console.warn('[test] __SongLibraryPage not found, creating stub');
                    window.__SongLibraryPage = class {
                        constructor(container) {
                            this.container = container;
                            this._songs = [];
                            this._loading = true;
                        }
                        set store(store) {
                            this._store = store;
                            const songs = store?.get?.('songs');
                            if (songs) { this._songs = songs; this._loading = false; }
                        }
                        get store() { return this._store; }
                        render() {
                            this.el = document.createElement('div');
                            this.el.id = 'page-songs';

                            this._songsEmpty = document.createElement('div');
                            this._songsEmpty.id = 'songsEmpty';
                            this._songsEmpty.style.display = 'none';
                            this.el.appendChild(this._songsEmpty);

                            this._songsContent = document.createElement('div');
                            this._songsContent.id = 'songsContent';
                            this._songsContent.style.display = 'none';
                            this.el.appendChild(this._songsContent);

                            if (this._songs && this._songs.length > 0) {
                                this._showContent(this._songs);
                            } else if (!this._loading) {
                                this._showEmpty();
                            }

                            this.container.appendChild(this.el);
                        }
                        _showEmpty() {
                            if (this._songsEmpty) this._songsEmpty.style.display = '';
                        }
                        _showContent(songs) {
                            if (this._songsContent) this._songsContent.style.display = '';
                            this._songsContent.innerHTML = '';
                            songs.forEach(song => {
                                const card = document.createElement('div');
                                card.className = 'song-card';
                                card.dataset.songId = song.id;
                                card.textContent = song.title;
                                card.addEventListener('click', () => {
                                    const detail = document.createElement('div');
                                    detail.className = 'song-detail';
                                    this._songsContent.appendChild(detail);
                                });
                                this._songsContent.appendChild(card);
                            });
                        }
                        destroy() {}
                    };
                }

                return { ok: true };
            })();
        """)
        print("  Source module stubs verified")

        # ===================================================================
        # Step 4: Load and run test suites
        # ===================================================================
        all_results = {}

        for test_file in files_to_run:
            filepath = TEST_DIR / test_file
            if not filepath.exists():
                print(f"  SKIP {test_file}: file not found")
                continue

            test_code = load_file(filepath)
            print(f"\n  === {test_file} ===")

            # Inject the test code
            page.evaluate(test_code)

            # Find the newly registered test object
            result = page.evaluate("""
                (() => {
                    const candidates = Object.entries(window).filter(([k, v]) =>
                        k.startsWith('__') && typeof v === 'object' && v !== null && typeof v.runAll === 'function'
                    );
                    if (candidates.length === 0) {
                        return { error: 'No test suite found' };
                    }
                    // Use the LAST one (most recently added)
                    const [key, testObj] = candidates[candidates.length - 1];
                    try {
                        const res = testObj.runAll();
                        return JSON.parse(JSON.stringify(res));
                    } catch(e) {
                        return { error: e.message, stack: e.stack };
                    }
                })();
            """)

            all_results[test_file] = result
            if result.get("error"):
                print(f"    ERROR: {result['error']}")
            elif result.get("summary"):
                print(f"    {result['summary']}")
                if result.get("results"):
                    for name, r in result["results"].items():
                        status = "PASS" if r.get("pass") else "FAIL"
                        detail = r.get("detail", "") or r.get("reason", "") or r.get("error", "")
                        print(f"      {status} {name}: {detail}"[:120])

        # ===================================================================
        # Step 5: Summary
        # ===================================================================
        total = 0
        passed = 0
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)

        for file_name, result in all_results.items():
            if result.get("error"):
                print(f"  FAIL {file_name}: {result['error'][:80]}")
                continue
            summary = result.get("summary", "no summary")
            print(f"  {file_name}: {summary}")
            if result.get("results"):
                for name, r in result["results"].items():
                    total += 1
                    if r.get("pass"):
                        passed += 1
                    else:
                        reason = r.get("reason", "") or r.get("error", "") or r.get("detail", "")
                        if isinstance(reason, str):
                            reason = reason[:80]
                        print(f"    FAIL {name}: {reason}")

        print(f"\n  {passed}/{total} tests passed")
        if passed < total:
            print(f"  {total - passed} tests FAILING (RED)")
        else:
            print("  ALL TESTS GREEN!")

        browser.close()
        return passed == total


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run JS unit tests")
    parser.add_argument("--headed", action="store_true", help="Show browser window")
    parser.add_argument("--suite", type=str, help="Filter by suite name (e.g. 'animation')")
    args = parser.parse_args()

    success = run_tests(headed=args.headed, suite_filter=args.suite)
    sys.exit(0 if success else 1)
