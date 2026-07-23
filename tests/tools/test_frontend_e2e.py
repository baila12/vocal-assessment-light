"""
Frontend E2E test — v7.1.0

Uses Playwright to test Vue 3 SPA pages load correctly,
no console errors, buttons respond, and key flows work.
"""
import sys, os, time, json

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Playwright not installed. Install with: pip install playwright && playwright install chromium")
    sys.exit(1)

BACKEND = "http://127.0.0.1:8000"
FRONTEND = "http://127.0.0.1:5173"

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
print('FRONTEND E2E TEST — Vue 3 SPA')
print('=' * 60)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width': 1280, 'height': 800})
    page = context.new_page()

    # Collect console errors
    console_errors = []
    page.on('console', lambda msg: (
        console_errors.append(f'[{msg.type}] {msg.text}')
        if msg.type == 'error' else None
    ))
    page.on('pageerror', lambda err: console_errors.append(f'[PAGE ERROR] {err}'))

    # ---- 1. Home page loads ----
    print('\n--- 1. Home Page ---')
    try:
        page.goto(FRONTEND, wait_until='networkidle', timeout=15000)
        check('Page loads', True)
        check('Title not empty', len(page.title()) > 0, page.title())
        # Check for key elements
        check('Has file upload area', page.locator('.el-upload').count() > 0 or
              page.locator('text=上传').count() > 0 or
              page.locator('text=Upload').count() > 0 or
              page.locator('[class*="upload"]').count() > 0,
              'found upload-related elements')
    except Exception as e:
        check('Home page', False, str(e))

    # ---- 2. Navigation works ----
    print('\n--- 2. Navigation ---')
    try:
        # Check bottom nav or top nav exists
        nav_links = page.locator('a, button, .el-menu-item').all()
        check('Nav items exist', len(nav_links) > 0, '%d nav items' % len(nav_links))
    except Exception as e:
        check('Navigation', False, str(e))

    # ---- 3. History page ----
    print('\n--- 3. History Page ---')
    try:
        # Try clicking history link
        history_link = page.locator('a[href*="history"], button:has-text("历史"), a:has-text("History")').first
        if history_link.is_visible():
            history_link.click()
            page.wait_for_load_state('networkidle', timeout=10000)
            check('History page loaded', True, page.url)
        else:
            # Try direct navigation
            page.goto(f'{FRONTEND}/history', wait_until='networkidle', timeout=10000)
            check('History direct nav', True, page.url)
    except Exception as e:
        check('History page', False, str(e))

    # ---- 4. Compare page ----
    print('\n--- 4. Compare Page ---')
    try:
        page.goto(f'{FRONTEND}/compare', wait_until='networkidle', timeout=10000)
        check('Compare page loads', True, page.url)
        # Check for upload areas
        uploads = page.locator('[class*="upload"], input[type="file"]').count()
        check('Upload elements', uploads > 0, '%d upload elements' % uploads)
    except Exception as e:
        check('Compare page', False, str(e))

    # ---- 5. Sing page ----
    print('\n--- 5. Sing Page ---')
    try:
        page.goto(f'{FRONTEND}/sing', wait_until='networkidle', timeout=10000)
        check('Sing page loads', True, page.url)
        # Check for sing button or action buttons
        buttons = page.locator('button').all()
        button_texts = [b.inner_text().strip() for b in buttons[:15] if b.is_visible()]
        has_sing_button = any('唱' in t or 'Sing' in t for t in button_texts if t)
        check('Sing UI elements', has_sing_button or len(buttons) > 3,
              '%d buttons, texts=%s' % (len(buttons), button_texts[:5]))
    except Exception as e:
        check('Sing page', False, str(e))

    # ---- 6. Report page (direct) ----
    print('\n--- 6. Report Page ---')
    try:
        page.goto(f'{FRONTEND}/report/test123', wait_until='networkidle', timeout=10000)
        check('Report page loads', page.url and '/report/' in page.url, page.url)
    except Exception as e:
        check('Report page', False, str(e))

    # ---- 7. API health check visible ----
    print('\n--- 7. Backend Connectivity ---')
    try:
        resp = page.request.get(f'{BACKEND}/health')
        check('Backend reachable', resp.ok, 'status=%d' % resp.status)
        data = resp.json()
        check('Backend healthy', data.get('status') == 'healthy')
        check('GPU info', data.get('gpu', {}).get('available') is True)
    except Exception as e:
        check('Backend connectivity', False, str(e))

    # ---- 8. Upload flow (API via fetch) ----
    print('\n--- 8. Upload via API ---')
    try:
        import requests
        with open('uploads/melody.wav', 'rb') as f:
            resp = requests.post(
                f'{BACKEND}/api/v1/upload',
                files={'file': ('melody.wav', f, 'audio/wav')},
                data={'mode': 'quick'},
                timeout=120
            )
        check('Upload HTTP 200', resp.status_code == 200, 'HTTP %d' % resp.status_code)
        result = resp.json()
        check('Upload success', result.get('success') is True)
        check('Has total_score', 'total_score' in result)
        check('Has 6 dims', len(result.get('scores', {})) >= 6)
        check('Has muscle_strength', 'muscle_strength' in result.get('scores', {}))
        check('Has heuristic', result.get('heuristic_dimensions') is not None)
    except Exception as e:
        check('Upload flow', False, str(e))

    # ---- 9. Console errors ----
    print('\n--- 9. Console Errors ---')
    if console_errors:
        for err in console_errors[:10]:  # Show first 10
            print(f'  [LOG] {err[:120]}')
    check('No console errors', len(console_errors) == 0,
          '%d errors found' % len(console_errors))

    # ---- 10. Responsive ----
    print('\n--- 10. Responsive Design ---')
    try:
        # Test mobile viewport
        page.set_viewport_size({'width': 375, 'height': 812})
        page.goto(FRONTEND, wait_until='networkidle', timeout=10000)
        check('Mobile viewport loads', True)
        page.set_viewport_size({'width': 1280, 'height': 800})
    except Exception as e:
        check('Responsive', False, str(e))

    browser.close()

# ---- SUMMARY ----
print('\n' + '=' * 60)
print('FRONTEND RESULTS: %d passed, %d failed out of %d' % (passed, failed, passed + failed))
if errors:
    print('\nFAILURES:')
    for e in errors:
        print('  ' + e)
if failed == 0:
    print('\n*** ALL FRONTEND TESTS PASSED ***')
else:
    print('\n*** %d FAILURES DETECTED ***' % failed)
print('=' * 60)
